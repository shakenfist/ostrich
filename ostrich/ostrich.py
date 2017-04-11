#!/usr/bin/env python
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# An OpenStack ansible install runner
#

import argparse
import curses
import importlib
import ipaddress
import json
import os
import sys
import urlparse

import runner
import stage_loader
import steps
import utils


ARGS = None


def expand_ironic_netblock(r):
    net = ipaddress.ip_network(r.complete['ironic-ip-block'])
    hosts = []
    for h in net.hosts():
        hosts.append(str(h))

    return net, hosts


def stage5_configure_osa_before_bootstrap(r, **kwargs):
    """Do all the configuration we do before bootstrapping."""

    nextsteps = []

    if r.complete['http-proxy'] and r.complete['http-proxy'] != 'none':
        kwargs['env'].update({'http_proxy': r.complete['http-proxy'],
                              'https_proxy': r.complete['http-proxy']})

        # This entry will only last until it is clobbered by ansible
        local_servers = 'localhost,127.0.0.1'
        if r.complete['local-cache'] != 'none':
            local_servers += ',%s' % r.complete['local-cache']

        nextsteps.append(
            steps.FileAppendStep(
                'proxy-environment',
                '/etc/environment',
                (('\n\nexport http_proxy="%(proxy)s"\n'
                  'export HTTP_PROXY="%(proxy)s"\n'
                  'export https_proxy="%(proxy)s"\n'
                  'export HTTPS_PROXY="%(proxy)s"\n'
                  'export ftp_proxy="%(proxy)s"\n'
                  'export FTP_PROXY="%(proxy)s"\n'
                  'export no_proxy=%(local)s\n'
                  'export NO_PROXY=%(local)sn')
                 % {'proxy': r.complete['http-proxy'],
                    'local': local_servers}),
                **kwargs)
            )

    replacements = [
        ('(http|https|git)://github.com',
         r.complete['git-mirror-github']),
        ('(http|https|git)://git.openstack.org',
         r.complete['git-mirror-openstack']),
        ('apt-get', 'DEBIAN_FRONTEND=noninteractive apt-get')
        ]

    if r.complete['local-cache'] != 'none':
        replacements.append(
            ('https://rpc-repo.rackspace.com',
             'http://%s/rpc-repo.rackspace.com' % r.complete['local-cache'])
            )

    nextsteps.append(
        steps.BulkRegexpEditorStep(
            'bulk-edit-osa',
            '/opt/openstack-ansible',
            '.*\.(ini|yml|sh)$',
            replacements,
            **kwargs)
        )

    nextsteps.append(
        steps.BulkRegexpEditorStep(
            'unapply-git-mirrors-for-cgit',
            '/opt/openstack-ansible',
            '.*\.(ini|yml|sh)$',
            [
                ('%s/cgit' % r.complete['git-mirror-openstack'],
                 'https://git.openstack.org/cgit')
            ],
            **kwargs)
        )

    #########################################################################
    # Release specific steps: Newton
    if r.complete['osa-branch'] == 'stable/newton':
        if utils.is_ironic(r):
            nextsteps.append(
                steps.SimpleCommandStep(
                    'fixup-add-ironic-newton',
                    ('sed -i -e "/- name: heat.yml.aio/ a \        '
                     '- name: ironic.yml.aio"  tests/bootstrap-aio.yml'),
                    **kwargs)
                )

        nextsteps.append(
            steps.RegexpEditorStep(
                'ansible-no-loopback-swap',
                ('/opt/openstack-ansible/tests/roles/bootstrap-host/'
                 'tasks/prepare_loopback_swap.yml'),
                'command: grep /openstack/swap.img /proc/swaps',
                'command: /bin/true',
                **kwargs)
            )

    #########################################################################
    # Release specific steps: Mitaka
    elif r.complete['osa-branch'] == 'stable/mitaka':
        p = urlparse.urlparse(r.complete['git-mirror-github'])
        mirror_host_github = p.netloc.split(':')[0]
        p = urlparse.urlparse(r.complete['git-mirror-openstack'])
        mirror_host_openstack = p.netloc.split(':')[0]

        nextsteps.append(
            steps.SimpleCommandStep(
                'git-mirror-host-keys',
                ('ssh-keyscan -H %s >> /etc/ssh/ssh_known_hosts'
                 % mirror_host_openstack),
                **kwargs)
            )

        if mirror_host_github != mirror_host_openstack:
            nextsteps.append(
                steps.SimpleCommandStep(
                    'git-mirror-host-keys-github',
                    ('ssh-keyscan -H %s >> /etc/ssh/ssh_known_hosts'
                     % mirror_host_github),
                    **kwargs)
                )

        if utils.is_ironic(r):
            nextsteps.append(
                steps.SimpleCommandStep(
                    'fixup-add-ironic-mitaka',
                    """sed -i -e '/swift_conf_overrides | default/ a \\    - name: ironic.yml.aio\\n      override: "{{ ironic_conf_overrides | default({}) }}"'  tests/roles/bootstrap-host/tasks/prepare_aio_config.yml""",
                    **kwargs)
                )

            nextsteps.append(
                steps.FileAppendStep(
                    'group-vars-ironic_service_user_name',
                    'playbooks/inventory/group_vars/all.yml',
                    '\n\nironic_service_user_name: ironic',
                    **kwargs)
                )

    #########################################################################
    nextsteps.append(
        steps.RegexpEditorStep(
            'lxc-cachable-downloads',
            '/usr/share/lxc/templates/lxc-download',
            'wget_wrapper -T 30 -q https?://',
            'wget_wrapper -T 30 -q --no-hsts http://',
            **kwargs)
        )

    nextsteps.append(
        steps.SimpleCommandStep(
            'archive-upper-constraints',
            ('curl https://git.openstack.org/cgit/openstack/requirements/'
             'plain/upper-constraints.txt?id='
             '$(awk \'/requirements_git_install_branch:/ {print $2}\' '
             '/opt/openstack-ansible/playbooks/defaults/repo_packages/'
             'openstack_services.yml) -o ~/.ostrich/upper-contraints.txt'),
            **kwargs)
        )

    return nextsteps


def stage6_bootstrap(r, **kwargs):
    """Bootstrap ansible and AIO."""

    nextsteps = []

    nextsteps.append(
        steps.SimpleCommandStep(
            'bootstrap-ansible',
            './scripts/bootstrap-ansible.sh',
            **kwargs)
        )
    nextsteps.append(
        steps.SimpleCommandStep(
            'bootstrap-aio',
            './scripts/bootstrap-aio.sh',
            **kwargs)
        )

    return nextsteps


def stage7_user_variables(r, **kwargs):
    """Configure user variables with all our special things."""

    nextsteps = []

    if r.complete['http-proxy'] and r.complete['http-proxy'] != 'none':
        # This is the more permanent way of doing this
        local_servers = 'localhost,127.0.0.1'
        if r.complete['local-cache'] != 'none':
            local_servers += ',%s' % r.complete['local-cache']

        nextsteps.append(
            steps.FileAppendStep(
                'proxy-environment-via-ansible',
                '/etc/openstack_deploy/user_variables.yml',
                (('\n\n'
                  'no_proxy_env: "%(local)s,{{ '
                  'internal_lb_vip_address }},{{ external_lb_vip_address }},'
                  '{%% for host in groups[\'all_containers\'] %%}'
                  '{{ hostvars[host][\'container_address\'] }}'
                  '{%% if not loop.last %%},{%% endif %%}{%% endfor %%}"\n'
                  'global_environment_variables:\n'
                  '  HTTPS_PROXY: "%(proxy)s"\n'
                  '  https_proxy: "%(proxy)s"\n'
                  '  HTTP_PROXY: "%(proxy)s"\n'
                  '  http_proxy: "%(proxy)s"\n'
                  '  NO_PROXY: "{{ no_proxy_env }}"\n'
                  '  no_proxy: "{{ no_proxy_env }}"')
                 % {'proxy': r.complete['http-proxy'],
                    'local': 'local_servers'}),
                **kwargs)
            )

    nextsteps.append(
        steps.FileAppendStep(
            'osa-debug-mode',
            '/etc/openstack_deploy/user_variables.yml',
            '\n\ndebug: true\nverbose: true',
            **kwargs)
        )

    nextsteps.append(
        steps.FileCreateStep(
            'lxc-hosts-apt-keep-configs',
            '/etc/ansible/roles/lxc_hosts/templates/apt-keep-configs.j2',
            """Dpkg::Options {
   "--force-confdef";
   "--force-confold";
}""",
            **kwargs)
        )

    nextsteps.append(
        steps.SimpleCommandStep(
            'lxc-hosts-apt-keep-configs-enable',
            """sed -i -e '/- name: Update container resolvers/ i \\- name: Always keep modified config files\\n  template:\\n    src: apt-keep-configs.j2\\n    dest: "{{ lxc_container_cache_path }}/{{ item.chroot_path }}/etc/apt/apt.conf.d/00apt-keep-configs"\\n  with_items: lxc_container_caches\\n  tags:\\n    - lxc-cache\\n    - lxc-cache-update\\n\\n'  /etc/ansible/roles/lxc_hosts/tasks/lxc_cache_preparation.yml""",
            **kwargs)
        )

    # Release specific steps: Mitaka
    if r.complete['osa-branch'] == 'stable/mitaka' and utils.is_ironic(r):
        nextsteps.append(
            steps.FileAppendStep(
                'enable-ironic',
                '/etc/openstack_deploy/user_variables.yml',
                '\n\nnova_virt_type: ironic\n',
                **kwargs)
            )

    return nextsteps


def stage8_ironic_networking(r, **kwargs):
    """Configure all the special things for ironic networking."""

    nextsteps = []

    nextsteps.append(
        steps.YamlAddElementStep(
            'add-provider-network',
            '/etc/openstack_deploy/openstack_user_config.yml',
            ['global_overrides', 'provider_networks'],
            {'network':
                 {'group_binds': ['neutron_linuxbridge_agent',
                                  'ironic_conductor_container',
                                  'ironic_api_container'],
                  'container_bridge': 'br-ironic',
                  'container_type': 'veth',
                  'container_interface': 'eth12',
                  'type': 'flat',
                  'net_name': 'ironic',
                  'ip_from_q': 'ironic'
                  }
            },
            **kwargs)
        )

    nextsteps.append(
        steps.YamlDeleteElementStep(
            'delete-provider-network',
            '/etc/openstack_deploy/openstack_user_config.yml',
            ['global_overrides', 'provider_networks'],
            2,
            **kwargs)
        )

    net, hosts = expand_ironic_netblock(r)

    nextsteps.append(
        steps.YamlUpdateElementStep(
            'configure-external-lb-ip',
            '/etc/openstack_deploy/openstack_user_config.yml',
            ['global_overrides'],
            'external_lb_vip_address',
            str(hosts[4]),
            **kwargs)
        )

    nextsteps.append(
        steps.YamlUpdateDictionaryStep(
            'add-network-cidr',
            '/etc/openstack_deploy/openstack_user_config.yml',
            ['cidr_networks'],
            {'ironic': str(net)},
            **kwargs)
        )

    nextsteps.append(
        steps.YamlAddElementStep(
            'reserve-netblock-start',
            '/etc/openstack_deploy/openstack_user_config.yml',
            ['used_ips'],
            '%s,%s' % (hosts[0], hosts[10]),
            **kwargs)
        )
    nextsteps.append(
        steps.YamlAddElementStep(
            'reserve-netblock-end',
            '/etc/openstack_deploy/openstack_user_config.yml',
            ['used_ips'],
            '%s,%s' % (hosts[-10], hosts[-1]),
            **kwargs)
        )
    nextsteps.append(
        steps.SimpleCommandStep(
            'add-ironic-bridge',
            'brctl addbr br-ironic',
            **kwargs)
        )
    nextsteps.append(
        steps.SimpleCommandStep(
            'add-ironic-bridge-nic',
            'brctl addif br-ironic eth1',
            **kwargs)
        )
    nextsteps.append(
        steps.SimpleCommandStep(
            'add-ironic-bridge-ip',
            'ifconfig br-ironic inet %s up' % hosts[4],
            **kwargs)
        )
    nextsteps.append(
        steps.SimpleCommandStep(
            'add-ironic-interface-ip',
            'ifconfig eth1 inet %s up' % hosts[3],
            **kwargs)
        )

    return nextsteps


def stage9_final_configuration(r, **kwargs):
    """Final tweaks to configuration before we run the playbooks."""

    nextsteps = []

    # We also need to re-write git repos in a large number of roles
    replacements = [
        ('(http|https|git)://github.com',
         r.complete['git-mirror-github']),
        ('(http|https|git)://git.openstack.org',
         r.complete['git-mirror-openstack']),
        ('https://mirror.rackspace.com',
         'http://mirror.rackspace.com'),
        (' +checksum:.*', ''),
        ('apt-get', 'DEBIAN_FRONTEND=noninteractive apt-get')
        ]

    if r.complete['local-cache'] != 'none':
        replacements.append(
            ('https://rpc-repo.rackspace.com',
             'http://%s/rpc-repo.rackspace.com' % r.complete['local-cache'])
            )
        replacements.append(
            ('https://bootstrap.pypa.io/get-pip.py',
             'http://%s/pip/get-pip.py' % r.complete['local-cache'])
            )

    nextsteps.append(
        steps.BulkRegexpEditorStep(
            'bulk-edit-roles',
            '/etc/ansible',
            '.*\.(ini|yml)$',
            replacements,
            **kwargs))

    # Release specific steps: Mitaka
    if r.complete['osa-branch'] == 'stable/mitaka' and utils.is_ironic(r):
        nextsteps.append(
            steps.CopyFileStep(
                'enable-ironic-environment-mitaka',
                'etc/openstack_deploy/env.d/ironic.yml',
                '/etc/openstack_deploy/env.d/ironic.yml',
                **kwargs)
            )

    if utils.is_ironic(r):
        nextsteps.append(
            steps.SimpleCommandStep(
                'ironic-tftp-address',
                ('sed -i -e \'s/ironic_tftp_server_address: "{{ ansible_ssh_host }}"/ironic_tftp_server_address: {{ hostvars[inventory_hostname][\'container_networks\'][\'ironic_address\'][\'address\'] }}/\' /etc/ansible/roles/os_ironic/defaults/main.yml')
                **kwargs)
            )

        nextsteps.append(
            steps.SimpleCommandStep(
                'ironic-pxe-options',
                ('sed -i -e \'s/tftp_server = {{ ironic_tftp_server_address }}/tftp_server = {{ ironic_tftp_server_address }}\\npxe_append_params = coreos.autologin ipa-debug=1/\' /etc/ansible/roles/os_ironic/templates/ironic.conf.j2'),
                **kwargs)
            )

    return nextsteps


def deploy(screen):
    global ARGS

    if not ARGS.no_curses:
        screen.nodelay(False)

    r = runner.Runner(screen)

    # Generic stage lookup tool. This allows deployers to add stages without
    # re-coding the underlying engine, and for new stages to be added without
    # a lot of plumbing.
    for stage_pyname in stage_loader.discover_stages():
        name = stage_pyname.replace('.py', '')
        module = importlib.import_module('ostrich.stages.%s' % name)
        r.load_dependancy_chain(module.get_steps(r))
        r.resolve_steps(use_curses=(not ARGS.no_curses))

    r.load_dependancy_chain(stage5_configure_osa_before_bootstrap(
            r, **r.kwargs))
    r.resolve_steps(use_curses=(not ARGS.no_curses))

    r.load_dependancy_chain(stage6_bootstrap(r, **r.kwargs))
    r.resolve_steps(use_curses=(not ARGS.no_curses))

    r.load_dependancy_chain(stage7_user_variables(r, **r.kwargs))
    r.resolve_steps(use_curses=(not ARGS.no_curses))

    if utils.is_ironic(r):
        r.load_dependancy_chain(stage8_ironic_networking(r, **r.kwargs))
        r.resolve_steps(use_curses=(not ARGS.no_curses))

    r.load_dependancy_chain(stage9_final_configuration(r, **r.kwargs))
    r.resolve_steps(use_curses=(not ARGS.no_curses))

    # The last of the things, run only once
    r.kwargs['max_attempts'] = 1
    r.load_step(
        steps.AnsibleTimingSimpleCommandStep(
            'run-playbooks',
            './scripts/run-playbooks.sh',
            os.path.expanduser('~/.ostrich/run-playbook-timings.json'),
            **r.kwargs))
    r.resolve_steps(use_curses=(not ARGS.no_curses))

    r.kwargs['cwd'] = None

    #####################################################################
    # Release specific steps: Mitaka
    if r.complete['osa-branch'] == 'stable/mitaka' and utils.is_ironic(r):
        r.load_step(
            steps.SimpleCommandStep(
                'add-ironic-to-nova-venv',
                './helpers/add-ironic-to-nova-venv',
                **r.kwargs)
            )

        r.resolve_steps(use_curses=(not ARGS.no_curses))

    # Debug output that might be helpful, not scripts are running from
    # ostrich directory
    r.load_dependancy_chain(
        [steps.SimpleCommandStep('lxc-details',
                                 './helpers/lxc-details',
                                 **r.kwargs),
         steps.SimpleCommandStep('pip-ruin-everything',
                                 ('pip install python-openstackclient '
                                  'python-ironicclient'),
                                 **r.kwargs),
         steps.SimpleCommandStep('os-cmd-bootstrap',
                                 './helpers/os-cmd-bootstrap',
                                 **r.kwargs)
         ])
    r.resolve_steps(use_curses=(not ARGS.no_curses))

    r.kwargs['max_attempts'] = 3
    r.kwargs['failing_step_delay'] = 150

    # Remove our HTTP proxy settings because the interfere with talking to
    # OpenStack
    r.kwargs['env']['http_proxy'] = ''
    r.kwargs['env']['https_proxy'] = ''
    r.kwargs['env']['HTTP_PROXY'] = ''
    r.kwargs['env']['HTTPS_PROXY'] = ''

    r.load_dependancy_chain(
        [steps.SimpleCommandStep(
                'openstack-details',
                './helpers/openstack-details',
                **r.kwargs)
        ])
    r.resolve_steps()

    if is_ironic(r):
        net, hosts = expand_ironic_netblock(r)
        kwargs['max_attempts'] = 1
        r.load_step(steps.SimpleCommandStep(
                'setup-neutron-ironic',
                ('./helpers/setup-neutron-ironic %s %s %s %s'
                 % (r.complete['ironic-ip-block'],
                    hosts[0], hosts[11], hosts[-11])
                 ),
                **kwargs))
        r.resolve_steps()

    # Must be the last step
    r.kwargs['max_attempts'] = 1
    r.load_step(steps.SimpleCommandStep('COMPLETION-TOMBSTONE',
                                        '/bin/true',
                                        **r.kwargs))
    r.resolve_steps(use_curses=(not ARGS.no_curses))


def main():
    global ARGS

    parser = argparse.ArgumentParser()
    parser.add_argument('--no-screen', dest='no_screen',
                        default=False, action='store_true',
                        help='Do not force me to use screen or tmux')
    parser.add_argument('--no-curses', dest='no_curses',
                        default=False, action='store_true',
                        help='Do not use curses for the UI')
    ARGS, extras = parser.parse_known_args()

    # We really like persistent sessions
    if not ARGS.no_screen:
        if ('TMUX' not in os.environ) and ('STY' not in os.environ):
            sys.exit('Only run ostrich in a screen or tmux session please')

    if ARGS.no_curses:
        deploy(None)
    else:
        curses.wrapper(deploy)
