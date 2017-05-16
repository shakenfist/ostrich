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
    """Final installation steps."""

    nextsteps = []

    #####################################################################
    # Release specific steps: Mitaka
    if r.complete['osa-branch'] == 'stable/mitaka' and utils.is_ironic(r):
        nextsteps.append(
            steps.SimpleCommandStep(
                'add-ironic-to-nova-venv',
                './helpers/add-ironic-to-nova-venv',
                **r.kwargs)
            )

    # Debug output that might be helpful, not scripts are running from
    # ostrich directory
    nextsteps.append(
        steps.SimpleCommandStep('lxc-details',
                                './helpers/lxc-details',
                                **r.kwargs)
        )
    nextsteps.append(
        steps.SimpleCommandStep('pip-ruin-everything',
                                ('pip install python-openstackclient '
                                 'python-ironicclient'),
                                **r.kwargs)
        )
    nextsteps.append(
        steps.SimpleCommandStep('os-cmd-bootstrap',
                                './helpers/os-cmd-bootstrap',
                                **r.kwargs)
        )

    # Remove our HTTP proxy settings because the interfere with talking to
    # OpenStack
    nextsteps.append(
        steps.KwargsStep(
            'kwargs-disable-http-proxy',
            r,
            {
                'max_attempts': 1,
                'env': {
                    'http_proxy': '',
                    'https_proxy': '',
                    'HTTP_PROXY': '',
                    'HTTPS_PROXY': ''
                }
            },
            **r.kwargs
            )
        )

    return nextsteps
