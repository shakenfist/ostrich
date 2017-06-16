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
    """Turn process tracing on, maybe."""

    nextsteps = []
    nextsteps.append(
        steps.KwargsStep(
            'kwargs-trace-processes',
            r,
            {
                'trace_processes': r.complete['trace-processes']
            },
            **r.kwargs
            )
        )
    return nextsteps
