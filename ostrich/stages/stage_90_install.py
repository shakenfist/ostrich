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

import copy

from ostrich import steps
from ostrich import utils


def get_steps(r):
    """The actual steps."""

    r.kwargs['max_attempts'] = 3
    r.kwargs['cwd'] = '/opt/openstack-ansible/playbooks'

    error_kwargs = copy.deepcopy(r.kwargs)
    error_kwargs['max_attempts'] = 1
    error_kwargs['cwd'] = None

    nextsteps = []
    playnames = [
        ('openstack-hosts-setup', None),
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
                './helpers/openstack-details %s' % r.complete['osa-branch'],
                **r.kwargs)
        ])
    r.resolve_steps(use_curses=(not ARGS.no_curses))

    if utils.is_ironic(r):
        net, hosts = utils.expand_ironic_netblock(r)
        r.kwargs['max_attempts'] = 1
        r.load_step(steps.SimpleCommandStep(
                'setup-neutron-ironic',
                ('./helpers/setup-neutron-ironic %s %s %s %s'
                 % (r.complete['ironic-ip-block'],
                    hosts[0], hosts[11], hosts[-11])
                 ),
                **r.kwargs))
        r.resolve_steps(use_curses=(not ARGS.no_curses))

    return nextstesp
