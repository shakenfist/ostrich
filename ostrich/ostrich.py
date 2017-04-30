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
import copy
import curses
import importlib
import ipaddress
import os
import sys

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
                    'local': local_servers}),
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

    if r.complete['osa-branch'] == 'stable/mitaka':
        nextsteps.append(steps.PatchStep(
            'lxc-hosts-ucf-non-interactive', **kwargs))
    else:
        nextsteps.append(steps.PatchStep(
            'lxc-hosts-ucf-non-interactive-newton', **kwargs))

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
    nextsteps.append(steps.PatchStep('ironic-vip-address', **r.kwargs))

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
        nextsteps.append(steps.PatchStep('ironic-tftp-address', **kwargs))

        if r.complete['osa-branch'] == 'stable/mitaka':
            nextsteps.append(steps.PatchStep('ironic-pxe-options', **kwargs))
        else:
            nextsteps.append(steps.PatchStep('ironic-pxe-options-newton',
                                             **kwargs))

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

    r.load_dependancy_chain(stage7_user_variables(r, **r.kwargs))
    r.resolve_steps(use_curses=(not ARGS.no_curses))

    if utils.is_ironic(r):
        r.load_dependancy_chain(stage8_ironic_networking(r, **r.kwargs))
        r.resolve_steps(use_curses=(not ARGS.no_curses))

    r.load_dependancy_chain(stage9_final_configuration(r, **r.kwargs))
    r.resolve_steps(use_curses=(not ARGS.no_curses))

    # The last of the things
    r.kwargs['max_attempts'] = 3
    r.kwargs['cwd'] = '/opt/openstack-ansible/playbooks'

    error_kwargs = copy.deepcopy(r.kwargs)
    error_kwargs['max_attempts'] = 1
    error_kwargs['cwd'] = None

    nextsteps = []

    # Copy /etc/environment into our runtime so that we can exclude the
    # various containers from proxies.
    nextsteps.append(
        steps.SimpleCommandStep(
            'environment-before',
            'cat /etc/environment',
            **r.kwargs)
        )
    
    nextsteps.append(
        steps.AnsibleTimingSimpleCommandStep(
            'openstack-hosts-setup',
            'openstack-ansible -vvv openstack-hosts-setup.yml',
            os.path.expanduser('~/.ostrich/timings-openstack-hosts-setup.json'),
            **r.kwargs)
        )

    nextsteps.append(
        steps.SimpleCommandStep(
            'environment-after',
            'cat /etc/environment',
            **r.kwargs)
        )
    r.load_dependancy_chain(nextsteps)
    r.resolve_steps(use_curses=(not ARGS.no_curses))

    nextsteps = []
    variables = {}
    variable_re = re.compile('(.*)=(.*)')
    with open('/etc/environment', 'r') as f:
        for line in f.readlines():
            m = variable_re.match(line)
            if m:
                variables[m.group(1)] = m.group(2)

    nextsteps.append(
        steps.KwargStep(
            'ansible-environment',
            r,
            {
                'env': variables
            },
            *r.kwargs
            )
        )
    r.load_dependancy_chain(nextsteps)
    r.resolve_steps(use_curses=(not ARGS.no_curses))

    # Run everything else
    nextsteps = []
    playnames = [
        ('security-hardening', None),
        ('lxc-hosts-setup', None),
        ('lxc-containers-create',
         steps.SimpleCommandStep(
                'lxc-containers-create-on-error',
                './helpers/lxc-ifup',
                **error_kwargs
                )
         ),
        ('setup-infrastructure', None),
        ('os-keystone-install', None),
        ('os-glance-install', None),
        ('os-cinder-install', None),
        ('os-nova-install', None),
        ('os-neutron-install', None),
        ('os-heat-install', None),
        ('os-horizon-install', None),
        ('os-ceilometer-install', None),
        ('os-aodh-install', None),
        ('os-swift-install', None)
    ]

    if utils.is_ironic(r):
        playnames.append(('os-ironic-install', None))

    for play, on_failure in playnames:
        r.kwargs['on_failure'] = on_failure
        nextsteps.append(
            steps.AnsibleTimingSimpleCommandStep(
                play,
                'openstack-ansible -vvv %s.yml' % play,
                os.path.expanduser('~/.ostrich/timings-%s.json' % play),
                **r.kwargs)
        )
    r.load_dependancy_chain(nextsteps)
    r.resolve_steps(use_curses=(not ARGS.no_curses))

    r.kwargs['cwd'] = None
    r.kwargs['on_failure'] = None

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
    r.resolve_steps(use_curses=(not ARGS.no_curses))

    if utils.is_ironic(r):
        net, hosts = expand_ironic_netblock(r)
        r.kwargs['max_attempts'] = 1
        r.load_step(steps.SimpleCommandStep(
                'setup-neutron-ironic',
                ('./helpers/setup-neutron-ironic %s %s %s %s'
                 % (r.complete['ironic-ip-block'],
                    hosts[0], hosts[11], hosts[-11])
                 ),
                **r.kwargs))
        r.resolve_steps(use_curses=(not ARGS.no_curses))

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
