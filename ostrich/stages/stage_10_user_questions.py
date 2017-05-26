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


def get_steps(r):
    """Things we need the user to tell us."""

    nextsteps = []
    nextsteps.append(
        steps.QuestionStep(
            'git-mirror-github',
            'Are you running a local github.com mirror?',
            ('Mirroring github.com speeds up setup on slow and '
             'unreliable networks, but means that you have to '
             'maintain a mirror somewhere on your corporate network. '
             'If you are unsure, just enter "git://github.com" here. '
             'Otherwise, we need an answer in the form of '
             '<protocol>://<server>, for example '
             'git://gitmirror.example.com'),
            'Mirror URL',
            **r.kwargs
            )
        )
    nextsteps.append(
        steps.QuestionStep(
            'git-mirror-openstack',
            'Are you running a local git.openstack.org mirror?',
            ('Mirroring git.openstack.org speeds up setup on slow '
             'and unreliable networks, but means that you have to '
             'maintain a mirror somewhere on your corporate network. '
             'If you are unsure, just enter '
             '"git://git.openstack.org" here. Otherwise, we need an '
             'answer in the form of <protocol>://<server>, for '
             'example git://gitmirror.example.com'),
            'Mirror URL',
            **r.kwargs
            )
        )
    nextsteps.append(
        steps.QuestionStep(
            'osa-branch',
            'What OSA branch (or commit SHA) would you like to use?',
            'Use stable/newton unless you know what you are doing.',
            'OSA branch',
            **r.kwargs
            )
        )
    nextsteps.append(
        steps.QuestionStep(
            'http-proxy',
            'Are you running a local http proxy?',
            ('OSA will download large objects such as LXC base '
             'images. If you have a slow network, or are on a '
             'corporate network which requires a proxy, configure it '
             'here with a URL like http://cache.example.com:3128 . '
             'If you do not use a proxy, please enter "none" here. '
             'Please note this proxy is only used for mitaka installs, '
             'as OSA added an in-built proxy in newton.'),
            'HTTP Proxy',
            **r.kwargs
            )
        )
    nextsteps.append(
        steps.QuestionStep(
            'hypervisor',
            'What hypervisor do you want to run?',
            'Possible answers are "ironic" or "kvm".',
            'Hypervisor',
            **r.kwargs
            )
        )
    nextsteps.append(
        steps.QuestionStep(
            'local-cache',
            'Local caching',
            ('Do you locally cache rpc-repo.rackspace.com? If so, we expect '
             'the cache to be in a directory named rpc-repo.rackspace.com '
             'on your cache web server. Please enter the hostname for that '
             'server here. If you do not cache, just enter "none" here.'),
            'Local Cache',
            **r.kwargs
            )
        )
    nextsteps.append(
        steps.QuestionStep(
            'enable-ceph',
            'Ceph support',
            ('Would you like to deploy ceph as well? If so, answer "yes" '
             'here'),
            'Ceph support',
            **r.kwargs
            )
        )
    nextsteps.append(
        steps.QuestionStep(
            'ansible-debug',
            'Enable ansible debugging mode?',
            ('Do you want to enable ansible debugging mode? This produces a '
             'of extra, hard to read output. However, it is useful in '
             'debugging some issues. To enable debug mode, answer "yes".'),
            'Ansible debugging',
            **r.kwargs
            )
        )

    return nextsteps
