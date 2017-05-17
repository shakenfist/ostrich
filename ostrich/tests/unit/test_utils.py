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

from ostrich import utils
from ostrich.tests.unit import utils as test_utils


class UtilsTestCase(base.BaseTestCase):
    def test_is_ironic(self):
        r = test_utils.QuestionsAnsweredRunner(None)

        r.complete['hypervisor'] = 'kvm'
        self.assertFalse(utils.is_ironic(r))

        r.complete['hypervisor'] = 'ironic'
        self.assertTrue(utils.is_ironic(r))

    def test_recursive_dictionary_update_simple(self):
        a = {}
        b = {'a': 1, 'b': 2}
        c = utils.recursive_dictionary_update(a, b)
        self.assertEquals(b, c)

        a = {'a': 3}
        c = utils.recursive_dictionary_update(a, b)
        self.assertEquals(b, c)

        a = {'c': 3}
        c = utils.recursive_dictionary_update(a, b)
        self.assertEquals({'a': 1, 'b': 2, 'c': 3}, c)

    def test_recursive_dictionary_update_deeper(self):
        a = {'c': 3}
        b = {'a': 1, 'b': {'a': 1, 'b': 2}}
        c = utils.recursive_dictionary_update(a, b)
        self.assertEquals({'a': 1, 'b': {'a': 1, 'b': 2}, 'c': 3}, c)

        a = {'b': {'c': 3}, 'c': 3}
        b = {'a': 1, 'b': {'a': 1, 'b': 2}}
        c = utils.recursive_dictionary_update(a, b)
        self.assertEquals({'a': 1, 'b': {'a': 1, 'b': 2, 'c': 3}, 'c': 3}, c)

    def test_recursive_dictionary_update_unset(self):
        a = {'a': 1, 'b': {'a': 1, 'b': 2, 'c': 3}, 'c': 3}
        b = {'b': {'a': None}}
        c = utils.recursive_dictionary_update(a, b)
        self.assertEquals({'a': 1, 'b': {'b': 2, 'c': 3}, 'c': 3}, c)

    def test_recursive_dictionary_update_unset_missing(self):
        a = {'a': 1, 'b': {'a': 1, 'b': 2, 'c': 3}, 'c': 3}
        b = {'b': {'z': None}}
        c = utils.recursive_dictionary_update(a, b)
        self.assertEquals({'a': 1, 'b': {'a': 1, 'b': 2, 'c': 3}, 'c': 3}, c)
