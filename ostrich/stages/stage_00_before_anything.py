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

import psutil
import time

from ostrich import steps


class AptDailyStep(steps.Step):
    """Wait for apt-daily to not be running."""

    def _run(self, emit, screen):
        found_apt_daily = True
        while found_apt_daily:
            emit.emit('Waiting for daily apt run to end')

            found_apt_daily = False
            for process in psutil.process_iter():
                cmdline = ' '.join(process.cmdline())
                if cmdline.find('apt.systemd.daily') != -1:
                    found_apt_daily = True

            if found_apt_daily:
                time.sleep(10)

        return True


def get_steps(r):
    """Things to do before attempting anything."""

    nextsteps = []
    nextsteps.append(AptDailyStep('apt-daily', **r.kwargs))
    return nextsteps
