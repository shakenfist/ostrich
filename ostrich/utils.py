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
#
# An OpenStack ansible install runner
#


import ipaddress


def is_ironic(r):
    return r.complete['hypervisor'] == 'ironic'


def recursive_dictionary_update(d, updates):
    for key in updates:
        if key in d and type(d[key]) is dict:
            recursive_dictionary_update(d[key], updates[key])
        else:
            if updates[key] is None:
                del d[key]
            else:
                d[key] = updates[key]
    return d


def expand_ironic_netblock(r):
    net = ipaddress.ip_network(r.complete['ironic-ip-block'])
    hosts = []
    for h in net.hosts():
        hosts.append(str(h))

    return net, hosts
