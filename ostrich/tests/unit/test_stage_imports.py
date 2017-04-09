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


import importlib
import os

from oslotest import base
from ostrich import runner
from ostrich import stage_loader


class StageImportsTestCase(base.BaseTestCase):
    def test_stage0_loads(self):
        sl = stage_loader.discover_stages()
        self.assertEqual('stage_00_before_anything.py', sl[0])

    def test_stage_importability(self):
        r = runner.Runner(None)

        for stage_pyname in stage_loader.discover_stages():
            name = stage_pyname.replace('.py', '')
            module = importlib.import_module(
                'ostrich.stages.%s' % name)
            module.get_steps(r)
