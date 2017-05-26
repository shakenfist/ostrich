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
import os

from ostrich import steps
from ostrich import utils


def get_steps(r):
    """Debug output."""

    nextsteps = []

    nextsteps.append(
        steps.SimpleCommandStep(
               'openstack-details',
               './helpers/openstack-details %s' % r.complete['osa-branch'],
               **r.kwargs)
        )

    if utils.is_ironic(r):
        nextsteps.append(
            steps.SimpleCommandStep(
                   'openstack-details-ironic',
                   ('./helpers/openstack-details-ironic %s'
                    % r.complete['osa-branch']),
                   **r.kwargs)
            )

        net, hosts = utils.expand_ironic_netblock(r)
        nextsteps.append(
            steps.SimpleCommandStep(
                'setup-neutron-ironic',
                ('./helpers/setup-neutron-ironic %s %s %s %s'
                 % (r.complete['ironic-ip-block'],
                    hosts[0], hosts[11], hosts[-11])
                 ),
                **r.kwargs)
            )

    return nextsteps
