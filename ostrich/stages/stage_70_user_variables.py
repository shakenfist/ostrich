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
    """Configure user variables with all our special things."""

    nextsteps = []

    if r.complete['http-proxy'] and r.complete['http-proxy'] != 'none':
        # This is the more permanent way of doing this
        local_servers = 'localhost,127.0.0.1'
        if r.complete['local-cache'] != 'none':
            local_servers += ',%s' % r.complete['local-cache']

        if r.complete['osa-branch'] == 'stable/mitaka':
            nextsteps.append(
                steps.FileAppendStep(
                    'proxy-environment-via-ansible',
                    '/etc/openstack_deploy/user_variables.yml',
                    (('\n\n'
                      'no_proxy_env: "%(local)s,{{ '
                      'internal_lb_vip_address }},{{ external_lb_vip_address }},'
                      '{%% for host in groups[\'all_containers\'] %%}'
                      '{{ hostvars[host][\'container_address\'] }}'
                      '{%% if not loop.last %%},{%% endif %%}{%% endfor %%}"\n'
                      'global_environment_variables:\n'
                      '  HTTPS_PROXY: "%(proxy)s"\n'
                      '  https_proxy: "%(proxy)s"\n'
                      '  HTTP_PROXY: "%(proxy)s"\n'
                      '  http_proxy: "%(proxy)s"\n'
                      '  NO_PROXY: "{{ no_proxy_env }}"\n'
                      '  no_proxy: "{{ no_proxy_env }}"')
                     % {'proxy': r.complete['http-proxy'],
                        'local': local_servers}),
                    **r.kwargs)
                )

    nextsteps.append(
        steps.FileAppendStep(
            'osa-debug-mode',
            '/etc/openstack_deploy/user_variables.yml',
            '\n\ndebug: true\nverbose: true',
            **r.kwargs)
        )

    nextsteps.append(
        steps.FileCreateStep(
            'lxc-hosts-apt-keep-configs',
            '/etc/ansible/roles/lxc_hosts/templates/apt-keep-configs.j2',
            """Dpkg::Options {
   "--force-confdef";
   "--force-confold";
}""",
            **r.kwargs)
        )

    nextsteps.append(
        steps.SimpleCommandStep(
            'lxc-hosts-apt-keep-configs-enable',
            """sed -i -e '/- name: Update container resolvers/ i \\- name: Always keep modified config files\\n  template:\\n    src: apt-keep-configs.j2\\n    dest: "{{ lxc_container_cache_path }}/{{ item.chroot_path }}/etc/apt/apt.conf.d/00apt-keep-configs"\\n  with_items: lxc_container_caches\\n  tags:\\n    - lxc-cache\\n    - lxc-cache-update\\n\\n'  /etc/ansible/roles/lxc_hosts/tasks/lxc_cache_preparation.yml""",
            **r.kwargs)
        )

    if r.complete['osa-branch'] == 'stable/mitaka':
        nextsteps.append(steps.PatchStep(
            'lxc-hosts-ucf-non-interactive', **r.kwargs))
        nextsteps.append(steps.PatchStep('cinder-constraints-mitaka', **r.kwargs))
    elif r.complete['osa-branch'] == 'stable/newton':
        nextsteps.append(steps.PatchStep(
            'lxc-hosts-ucf-non-interactive-newton', **r.kwargs))
    else:
        nextsteps.append(steps.PatchStep(
            'lxc-hosts-ucf-non-interactive-ocata', **r.kwargs))

    # Release specific steps: Mitaka
    if r.complete['osa-branch'] == 'stable/mitaka' and utils.is_ironic(r):
        nextsteps.append(
            steps.FileAppendStep(
                'enable-ironic',
                '/etc/openstack_deploy/user_variables.yml',
                '\n\nnova_virt_type: ironic\n',
                **r.kwargs)
            )

    return nextsteps
