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


from oslotest import base

from ostrich import runner
from ostrich.stages import stage_00_before_anything
from ostrich import steps


class Stage00TestCase(base.BaseTestCase):
    def test_stage_returns_steps(self):
        r = runner.Runner(None)
        work = stage_00_before_anything.get_steps(r)
        self.assertTrue(len(work) == 1)
        self.assertTrue(type(work[0]) is steps.SimpleCommandStep)

    def test_stage_waits_for_apt(self):
        # TODO(mikal): rewrite this stage to be more pythonic and therefore
        # testable. Our heritage as a shell script is a bit too clear here.
        pass
