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


def _ansible_debug(r):
    if r.complete['ansible-debug'] == 'yes':
        return '1'
    return '0'


def get_steps(r):
    """Clone OSA."""

    nextsteps = []
    nextsteps.append(
        steps.SimpleCommandStep(
            'git-clone-osa',
            ('git clone %s/openstack/openstack-ansible '
             '/opt/openstack-ansible'
             % r.complete['git-mirror-openstack']),
            **r.kwargs
            )
        )
    nextsteps.append(
        steps.KwargsStep(
            'kwargs-osa',
            r,
            {
                'cwd': '/opt/openstack-ansible',
                'env': {
                    'ANSIBLE_ROLE_FETCH_MODE': 'git-clone',
                    'ANSIBLE_DEBUG': _ansible_debug(r),
                    'ANSIBLE_KEEP_REMOTE_FILES': '1'
                }
            },
            **r.kwargs
            )
        )

    if utils.is_ironic(r):
        nextsteps.append(
            steps.KwargsStep(
                'kwargs-ironic',
                r,
                {
                    'env': {
                        'BOOTSTRAP_OPTS': 'nova_virt_type=ironic'
                    }
                },
                **r.kwargs
                )
            )

    return nextsteps
