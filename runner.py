#!/usr/bin/python

# An openstack ansible install runner

import curses
import curses.textpad
import datetime
import fcntl
import json
import os
import re
import select
import subprocess
import sys
import textwrap
import time


class Step(object):
    def __init__(self, name, depends=None):
        self.name = name
        self.depends = depends
        self.attempts = 0


class SimpleCommandStep(Step):
    def __init__(self, name, command, depends=None, cwd=None, env=None):
        super(SimpleCommandStep, self).__init__(name, depends)
        self.command = command
        self.cwd = cwd

        self.env = os.environ
        self.env.update(env)

    def __str__(self):
        return 'step %s, depends on %s' %(self.name, self.depends)

    def run(self, emit, screen):
        emit.emit('Running %s' % self)
        emit.emit('# %s\n' % self.command)
        self.attempts += 1

        if self.attempts > 5:
            emit.emit('... repeatedly failed step, giving up')
            sys.exit(1)

        obj = subprocess.Popen(self.command,
                               stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE,
                               shell=True,
                               cwd=self.cwd,
                               env=self.env)

        flags = fcntl.fcntl(obj.stdout, fcntl.F_GETFL)
        fcntl.fcntl(obj.stdout, fcntl.F_SETFL, flags | os.O_NONBLOCK)

        flags = fcntl.fcntl(obj.stderr, fcntl.F_GETFL)
        fcntl.fcntl(obj.stderr, fcntl.F_SETFL, flags | os.O_NONBLOCK)

        obj.stdin.close()
        while obj.poll() is None:
            readable, _, _ = select.select([obj.stderr, obj.stdout], [], [], 0)
            for f in readable:
                emit.emit(os.read(f.fileno(), 10000))

        emit.emit('... process complete')
        returncode = obj.returncode
        emit.emit('... exit code %d' % returncode)
        return returncode == 0


class QuestionStep(Step):
    def __init__(self, name, title, helpful, prompt, depends=None):
        super(QuestionStep, self).__init__(name, depends)
        self.title = title
        self.help = helpful
        self.prompt = prompt
        
    def run(self, emit, screen):
        emit.emit('%s' % self.title)
        emit.emit('%s\n' % ('=' * len(self.title)))
        emit.emit('%s\n' % self.help)
        return emit.getstr('>> ')


class EnforceScreenStep(Step):
    def __init__(self):
        super(EnforceScreenStep, self).__init__('enforce-screen')

    def run(self, emit, screen):
        if not os.environ['TERM'].startswith('screen'):
            emit.emit('Only run ostrich in a screen session please')
            sys.exit(1)
        return True


class Emitter(object):
    def __init__(self, output):
        self.output = output
        self.lines = 1
        self.logfile = None

    def clear(self):
	self.lines = 1
	self.output.clear()

    def logger(self, logfile):
        if self.logfile:
            self.logfile.close()
        self.logfile = open(os.path.expanduser('~/.ostrich/%s' % logfile), 'w')

    def emit(self, s):
        _, width = self.output.getmaxyx()
        width -= 6

        for line in s.split('\n'):
            line = ''.join([i if ord(i) < 128 else ' ' for i in line])

            if self.logfile:
                self.logfile.write('%s %s\n' %(datetime.datetime.now(), line))
                self.logfile.flush()

            if len(line) < 1:
                self.lines += 1

            for l in textwrap.wrap(line, width):
                if len(l) > 0:
                    try:
                        self.output.addstr(self.lines, 2, l)
                    except Exception as e:
                        print 'Exception: %s' % e
                        print '>>%s<<' % line
                        sys.exit(1)
                self.lines += 1

        self.output.border()
        self.output.refresh()

    def getstr(self, s):
        self.emit(s)
        curses.echo()
        answer = self.output.getstr(self.lines - 1, len(s) + 2)
        curses.noecho()
        return answer


class Runner(object):
    def __init__(self, screen):
        self.screen = screen

        self.steps = {}

        self.state_path = os.path.expanduser('~/.ostrich/state.json')
        if not os.path.exists(os.path.expanduser('~/.ostrich')):
            os.mkdir(os.path.expanduser('~/.ostrich'))

        self.complete = {}
        self.counter = 0
        if os.path.exists(self.state_path):
            with open(self.state_path, 'r') as f:
                state = json.loads(f.read())
                self.complete = state.get('complete', {})
                self.counter = state.get('counter', 0)

    def load_step(self, step):
        self.steps[step.name] = step

    def load_dependancy_chain(self, steps, depends=None):
        depend = depends
        for step in steps:
            step.depends = depend
            depend = step.name
            self.load_step(step)

    def resolve_steps(self):
        # Setup curses windows for the steps view
        height, width = self.screen.getmaxyx()
        progress = curses.newwin(3, width, 0, 0)
        progress.border()
        progress.refresh()

        output = curses.newwin(height - 4, width, 3, 0)
        output.scrollok(True)
        output.border()
        output.refresh()
        emitter = Emitter(output)

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

                if not step.depends or self.complete.get(step.depends, False):
                    progress.clear()
                    progress.addstr(1, 3, '%s %d steps to run, running %s' %(datetime.datetime.now(), len(self.steps), step_name))
                    progress.border()
                    progress.refresh()

                    run.append(step_name)
                    emitter.clear()
                    emitter.logger('%06d-%s' %(self.counter, step_name))
                    outcome = step.run(emitter, self.screen)
                    self.counter += 1

                    if outcome:
                        self.complete[step_name] = outcome
                        complete.append(step_name)

                    with open(self.state_path, 'w') as f:
                        f.write(json.dumps({'complete': self.complete,
                                            'counter': self.counter},
                                           indent=4, sort_keys=True))

            for step_name in complete:
                del self.steps[step_name]


def main(screen):
    screen.nodelay(False)
    r = Runner(screen)

    # We really like screen around here
    r.load_step(EnforceScreenStep())

    # git proxies
    r.load_dependancy_chain(
        [QuestionStep('git-mirror-github',
                      'Are you running a local github.com mirror?',
                      'Mirroring github.com speeds up setup on slow and unreliable networks, but means that you have to maintain a mirror somewhere on your corporate network. If you are unsure, just enter a blank line here. Otherwise, we need an answer in the form of <protocol>://<server>, for example git://gitmirror.example.com',
                      'Mirror URL'),
         QuestionStep('git-mirror-openstack',
                      'Are you running a local git.openstack.org mirror?',
                      'Mirroring git.openstack.org speeds up setup on slow and unreliable networks, but means that you have to maintain a mirror somewhere on your corporate network. If you are unsure, just enter a blank line here. Otherwise, we need an answer in the form of <protocol>://<server>, for example git://gitmirror.example.com',
                      'Mirror URL'),
         QuestionStep('osa-branch',
                      'What OSA branch (or commit SHA) would you like to use?',
                      'Use stable/newton unless you know what you are doing.',
                      'OSA branch')
         ])

    # APT commands
    r.load_dependancy_chain(
        [SimpleCommandStep('apt-update', 'apt-get update'),
         SimpleCommandStep('apt-upgrade', 'apt-get upgrade -y'),
         SimpleCommandStep('apt-dist-upgrade', 'apt-get dist-upgrade -y'),
         SimpleCommandStep('apt-useful',
                           'apt-get install -y screen ack-grep git expect')
         ])

    # Do the thing
    r.resolve_steps()

    # Steps requiring data from earlier
    r.load_dependancy_chain(
        [SimpleCommandStep('git-clone-osa', 'git clone %s/openstack/openstack-ansible /opt/openstack-ansible' % r.complete['git-mirror-openstack']),
         ])

    # Steps where we now have the OSA checkout
    kwargs = {'cwd': '/opt/openstack-ansible',
              'env': {'ANSIBLE_ROLE_FETCH_MODE': 'git-clone'}}
    r.load_dependancy_chain(
         [SimpleCommandStep('git-checkout-osa', 'git checkout %s' % r.complete['osa-branch'], **kwargs),
          SimpleCommandStep('fixup-add-ironic', 'sed -i -e "/- name: heat.yml.aio/ a \        - name: ironic.yml.aio"  tests/bootstrap-aio.yml', **kwargs),
          SimpleCommandStep('fixup-virt-ironic', 'echo "nova_virt_type: ironic" >> etc/openstack_deploy/user_variables.yml', **kwargs),
          ])

    # Do the more things
    r.resolve_steps()


if __name__ == '__main__':
    curses.wrapper(main)
