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

from ostrich import steps
from ostrich import utils


def get_steps(r):
    """Configure user variables with all our special things."""

    nextsteps = []

    if r.complete['http-proxy'] and r.complete['http-proxy'] != 'none':
        # This is the more permanent way of doing this
        local_servers = 'localhost,127.0.0.1'
        if r.complete['local-cache'] != 'none':
            local_servers += ',%s' % r.complete['local-cache']

        if r.complete['osa-branch'] == 'stable/mitaka':
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
    elif r.complete['osa-branch'] == 'stable/newton':
        nextsteps.append(steps.PatchStep(
            'lxc-hosts-ucf-non-interactive-newton', **kwargs))
    else:
        nextsteps.append(steps.PatchStep(
            'lxc-hosts-ucf-non-interactive-ocata', **kwargs))

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

    net, hosts = utils.expand_ironic_netblock(r)

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
