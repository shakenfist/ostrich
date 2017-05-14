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
            **r.kwargs)
        )

    nextsteps.append(
        steps.YamlDeleteElementStep(
            'delete-provider-network',
            '/etc/openstack_deploy/openstack_user_config.yml',
            ['global_overrides', 'provider_networks'],
            2,
            **r.kwargs)
        )

    net, hosts = utils.expand_ironic_netblock(r)

    nextsteps.append(
        steps.YamlUpdateElementStep(
            'configure-external-lb-ip',
            '/etc/openstack_deploy/openstack_user_config.yml',
            ['global_overrides'],
            'external_lb_vip_address',
            str(hosts[4]),
            **r.kwargs)
        )

    nextsteps.append(
        steps.YamlUpdateDictionaryStep(
            'add-network-cidr',
            '/etc/openstack_deploy/openstack_user_config.yml',
            ['cidr_networks'],
            {'ironic': str(net)},
            **r.kwargs)
        )

    nextsteps.append(
        steps.YamlAddElementStep(
            'reserve-netblock-start',
            '/etc/openstack_deploy/openstack_user_config.yml',
            ['used_ips'],
            '%s,%s' % (hosts[0], hosts[10]),
            **r.kwargs)
        )
    nextsteps.append(
        steps.YamlAddElementStep(
            'reserve-netblock-end',
            '/etc/openstack_deploy/openstack_user_config.yml',
            ['used_ips'],
            '%s,%s' % (hosts[-10], hosts[-1]),
            **r.kwargs)
        )
    nextsteps.append(
        steps.SimpleCommandStep(
            'add-ironic-bridge',
            'brctl addbr br-ironic',
            **r.kwargs)
        )
    nextsteps.append(
        steps.SimpleCommandStep(
            'add-ironic-bridge-nic',
            'brctl addif br-ironic eth1',
            **r.kwargs)
        )
    nextsteps.append(
        steps.SimpleCommandStep(
            'add-ironic-bridge-ip',
            'ifconfig br-ironic inet %s up' % hosts[4],
            **r.kwargs)
        )
    nextsteps.append(
        steps.SimpleCommandStep(
            'add-ironic-interface-ip',
            'ifconfig eth1 inet %s up' % hosts[3],
            **r.kwargs)
        )
    nextsteps.append(steps.PatchStep('ironic-vip-address', **r.kwargs))

    return nextsteps
