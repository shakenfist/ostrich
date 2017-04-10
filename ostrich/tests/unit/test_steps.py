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

import mock

from oslotest import base

from ostrich import emitters
from ostrich import steps
from ostrich.tests.unit import utils as test_utils


class KwargsStepTestCase(base.BaseTestCase):
    @mock.patch('ostrich.emitters.SimpleEmitter', emitters.NoopEmitter)
    def test_kwargs_step(self):
        steps.KWARGS = {}
        r = test_utils.QuestionsAnsweredRunner(None)

        s = steps.KwargsStep(
            'kwargs-osa-tests',
            {
                'cwd': '/opt/openstack-ansible',
                'env': {
                    'ANSIBLE_ROLE_FETCH_MODE': 'git-clone',
                    # 'ANSIBLE_DEBUG': '1',
                    'ANSIBLE_KEEP_REMOTE_FILES': '1'
                }
            },
            **steps.KWARGS
            )
        r.load_step(s)
        r.resolve_steps(use_curses=False)

        self.assertEqual('/opt/openstack-ansible', steps.KWARGS['cwd'])
        self.assertEqual('1', steps.KWARGS['env']['ANSIBLE_KEEP_REMOTE_FILES'])
