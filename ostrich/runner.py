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


import curses
import datetime
import json
import os
import sys

import emitters


class Runner(object):
    def __init__(self, screen):
        self.screen = screen

        self.steps = {}

        self.complete = {}
        self.counter = 0
        self.kwargs = {}
        self.tested = {}

        if os.path.exists(self._get_state_path()):
            with open(self._get_state_path(), 'r') as f:
                state = json.loads(f.read())
                self.complete = state.get('complete', {})
                self.counter = state.get('counter', 0)
                self.kwargs = state.get('kwargs', {})
                self.tested = state.get('tested', {})

    def _get_state_path(self):
        if not os.path.exists(os.path.expanduser('~/.ostrich')):
            os.mkdir(os.path.expanduser('~/.ostrich'))

        return os.path.expanduser('~/.ostrich/state.json')

    def load_step(self, step):
        if step.name in self.complete:
            print('You cannot load a new step with the same name as an '
                  'already complete step! The re-used name is %s.'
                  % step.name)
        if step.name in self.steps:
            print('You cannot load a new step with the same name as an '
                  'already pending step! The re-used name is %s.'
                  % step.name)
        self.steps[step.name] = step

    def load_dependancy_chain(self, steps, depends=None):
        depend = depends
        for step in steps:
            step.depends = depend
            depend = step.name
            self.load_step(step)

    def resolve_steps(self, use_curses=True):
        if use_curses:
            # Setup curses windows for the steps view
            height, width = self.screen.getmaxyx()
            progress = curses.newwin(3, width, 0, 0)
            progress.border()
            progress.refresh()

            output = curses.newwin(height - 4, width, 3, 0)
            output.scrollok(True)
            output.border()
            output.refresh()
            emitter = emitters.Emitter('ostrich', output)
        else:
            output = None
            emitter = emitters.SimpleEmitter('ostrich', output)

        for step_name in self.complete:
            if step_name in self.steps:
                del self.steps[step_name]

        run = [True]
        complete = []

        while len(run) > 0:
            run = []
            complete = []

            for step_name in self.steps:
                step = self.steps[step_name]

                runnable = False
                if not step.depends:
                    runnable = True

                if self.complete.get(step.depends, False):
                    runnable = True

                if runnable:
                    if use_curses:
                        progress.clear()
                        progress.addstr(1, 3, '%s %d steps to run, running %s'
                                        % (datetime.datetime.now(),
                                           len(self.steps),
                                           step_name))
                        progress.border()
                        progress.refresh()

                    run.append(step_name)
                    emitter.clear()
                    emitter.logger('%06d-%s' % (self.counter, step_name))
                    outcome = step.run(emitter, self.screen)
                    self.counter += 1

                    if outcome:
                        self.complete[step_name] = outcome
                        complete.append(step_name)

                    if self._get_state_path():
                        with open(self._get_state_path(), 'w') as f:
                            f.write(json.dumps({
                                        'complete': self.complete,
                                        'counter': self.counter,
                                        'kwargs': self.kwargs,
                                        'tested': self.tested,
                                        },
                                               indent=4, sort_keys=True))

            for step_name in complete:
                del self.steps[step_name]

        if len(self.steps) > 0:
            s = []
            for step in self.steps:
                s.append(str(step))

            print('Warning! Resolving steps did not process all outstanding '
                  'steps! This indicates a step that was expected to have '
                  'run has not. Outstanding steps are: %s' % '; '.join(s))
            sys.exit(1)
