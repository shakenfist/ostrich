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

import urlparse

from ostrich import steps
from ostrich import utils


def get_steps(r):
    """Do all the configuration we do before bootstrapping."""

    nextsteps = []

    p = urlparse.urlparse(r.complete['git-mirror-github'])
    mirror_host_github = p.netloc.split(':')[0]
    p = urlparse.urlparse(r.complete['git-mirror-openstack'])
    mirror_host_openstack = p.netloc.split(':')[0]

    nextsteps.append(
        steps.SimpleCommandStep(
            'git-mirror-host-keys',
            ('ssh-keyscan -H %s >> /etc/ssh/ssh_known_hosts'
             % mirror_host_openstack),
            **r.kwargs)
        )

    if mirror_host_github != mirror_host_openstack:
        nextsteps.append(
            steps.SimpleCommandStep(
                'git-mirror-host-keys-github',
                ('ssh-keyscan -H %s >> /etc/ssh/ssh_known_hosts'
                 % mirror_host_github),
                **r.kwargs)
            )

    if utils.is_ironic(r):
        if r.complete['osa-branch'] == 'stable/mitaka':
            nextsteps.append(steps.PatchStep('ironic-aio-mitaka', **r.kwargs))
        else:
            nextsteps.append(
                steps.SimpleCommandStep(
                    'fixup-add-ironic-newton',
                    ('sed -i -e "/- name: heat.yml.aio/ a \        '
                     '- name: ironic.yml.aio"  tests/bootstrap-aio.yml'),
                    **r.kwargs)
                )

        nextsteps.append(
            steps.FileAppendStep(
                'group-vars-ironic_service_user_name',
                'playbooks/inventory/group_vars/all.yml',
                '\n\nironic_service_user_name: ironic',
                **r.kwargs)
            )

    if r.complete['osa-branch'] != 'stable/mitaka':
        nextsteps.append(
            steps.RegexpEditorStep(
                'ansible-no-loopback-swap',
                ('/opt/openstack-ansible/tests/roles/bootstrap-host/'
                 'tasks/prepare_loopback_swap.yml'),
                'command: grep /openstack/swap.img /proc/swaps',
                'command: /bin/true',
                **r.kwargs)
            )

    nextsteps.append(
        steps.RegexpEditorStep(
            'lxc-cachable-downloads',
            '/usr/share/lxc/templates/lxc-download',
            'wget_wrapper -T 30 -q https?://',
            'wget_wrapper -T 30 -q --no-hsts http://',
            **r.kwargs)
        )

    nextsteps.append(
        steps.SimpleCommandStep(
            'archive-upper-constraints',
            ('curl https://git.openstack.org/cgit/openstack/requirements/'
             'plain/upper-constraints.txt?id='
             '$(awk \'/requirements_git_install_branch:/ {print $2}\' '
             '/opt/openstack-ansible/playbooks/defaults/repo_packages/'
             'openstack_services.yml) -o ~/.ostrich/upper-contraints.txt'),
            **r.kwargs)
        )

    return nextsteps
