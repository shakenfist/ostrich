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
import os
import tempfile
import yaml

from oslotest import base

from ostrich import emitters
from ostrich import steps
from ostrich.tests.unit import utils as test_utils


class YamlStepTestCase(base.BaseTestCase):
    @mock.patch('ostrich.emitters.SimpleEmitter', emitters.NoopEmitter)
    def test_yaml_append_step(self):
        tempdir = tempfile.mkdtemp()

        r = test_utils.QuestionsAnsweredRunner(None)
        r.kwargs = {'cwd': tempdir}

        with open(os.path.join(tempdir, 'foo.yml'), 'w') as f:
            f.write("""- name: Bootstrap the All-In-One (AIO)
  hosts: localhost
  gather_facts: True
  user: root
  roles:
    - role: "sshd"
    - role: "pip_install"
    - role: "bootstrap-host"
  vars:
    confd_overrides:
      aio:
        - name: cinder.yml.aio
        - name: designate.yml.aio
        - name: glance.yml.aio
        - name: heat.yml.aio
        - name: horizon.yml.aio
        - name: keystone.yml.aio
        - name: neutron.yml.aio
        - name: nova.yml.aio
        - name: swift.yml.aio
        - name: ironic.yml.aio
      ceph:
        - name: ceph.yml.aio
        - name: cinder.yml.aio
        - name: glance.yml.aio
        - name: heat.yml.aio
        - name: horizon.yml.aio
        - name: keystone.yml.aio
        - name: neutron.yml.aio
        - name: nova.yml.aio""")

        s = steps.YamlAddElementStep(
            'enable-ironic-aio',
            'foo.yml',
            [0, 'vars', 'confd_overrides', 'aio'],
            'name: ironic.yml.aio',
            **r.kwargs
        )
        r.load_step(s)
        r.resolve_steps(use_curses=False)

        with open(os.path.join(tempdir, 'foo.yml')) as f:
            y = yaml.load(f.read())

            self.assertTrue('name: ironic.yml.aio' in
                            y[0]['vars']['confd_overrides']['aio'])
