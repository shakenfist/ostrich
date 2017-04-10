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
import time

from oslotest import base

from ostrich import emitters
from ostrich import runner
from ostrich.stages import stage_00_before_anything
from ostrich import steps


class FakeProcess(object):
    def __init__(self, cmdline):
        self._cmdline = cmdline

    def cmdline(self):
        return self._cmdline


PROCESS_ITER_RESULTS = None


def fake_process_iter():
    results = PROCESS_ITER_RESULTS.pop(0)
    for item in results:
        yield FakeProcess(item)


class Stage00TestCase(base.BaseTestCase):
    def test_stage_returns_steps(self):
        r = runner.Runner(None)
        work = stage_00_before_anything.get_steps(r)
        self.assertTrue(len(work) == 1)
        self.assertTrue(type(work[0]) is
                        stage_00_before_anything.AptDailyStep)

    @mock.patch('psutil.process_iter', fake_process_iter)
    @mock.patch.object(time, 'sleep', return_value=None)
    def test_apt_daily_step(self, mock_time):
        global PROCESS_ITER_RESULTS
        PROCESS_ITER_RESULTS = [
            [
                ['/usr/bin/foo', 'apt.systemd.daily'],
                ['/bin/ls'],
                ['/bin/true']
                ],
            [
                ['/bin/ls'],
                ['/usr/bin/foo', 'apt.systemd.daily'],
                ['/bin/true']
                ],
            [
                ['/bin/ls'],
                ['/bin/true']
                ]
            ]

        emit = emitters.NoopEmitter('tests', None)
        s = stage_00_before_anything.AptDailyStep('apt-daily')
        self.assertTrue(s._run(emit, None))
        self.assertEqual(2, mock_time.call_count)
