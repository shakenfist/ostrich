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
    """Things we need the user to tell us about ironic."""

    nextsteps = []
    if utils.is_ironic(r):
        nextsteps.append(
            steps.QuestionStep(
                'ironic-ip-block',
                'IP block for Ironic nodes',
                ('We need to know what IP range to use for the neutron '
                 'network that Ironic nodes appear on. This block is managed '
                 'by neutronso should be separate from your primary netblock. '
                 'Please specify this as a CIDR range, for example '
                 '192.168.52.0/24.'),
                'Ironic IP Block',
                **steps.KWARGS
                )
            )
    return nextsteps
