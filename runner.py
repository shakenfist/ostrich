#!/usr/bin/python

# An openstack ansible install runner


import os
import subprocess
import sys


class Step(object):
    def __init__(self, name, depends=None):
        self.name = name
        self.depends = depends
        self.attempts = 0


class SimpleCommandStep(Step):
    def __init__(self, name, command, depends=None):
        super(SimpleCommandStep, self).__init__(name, depends)
        self.command = command

    def __str__(self):
        return 'step %s, depends on %s' %(self.name, self.depends)

    def run(self):
        print 'running %s' % self
        self.attempts += 1

        if self.attempts > 5:
            print '... repeatedly failed step, giving up'
            sys.exit(1)

        obj = subprocess.Popen(self.command,
                               stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE,
                               shell=True)
        (stdout, stderr) = obj.communicate()

        returncode = obj.returncode
        print '... exit code %d' % returncode
        return returncode == 0


class QuestionStep(Step):
    def __init__(self, name, title, helpful, prompt, depends=None):
        super(QuestionStep, self).__init__(name, depends)
        self.title = title
        self.help = helpful
        self.prompt = prompt
        
    def run(self):
        print self.title
        print '=' * len(self.title)
        print
        print self.help
        print
        return input('%s >> ' % self.prompt)


class EnforceScreenStep(Step):
    def __init__(self):
        super(EnforceScreenStep, self).__init__('enforce-screen')

    def run(self):
        if os.environ['TERM'] != 'screen':
            print 'Only run ostrich in a screen session please'
            sys.exit(1)


class Runner(object):
    def __init__(self):
        self.steps = {}
        self.complete = {}

    def load_step(self, step):
        self.steps[step.name] = step

    def load_dependancy_chain(self, steps, depends=None):
        depend = depends
        for step in steps:
            step.depends = depend
            depend = step.name
            self.load_step(step)

    def resolve_steps(self):
        run = [True]
        complete = []

        while len(run) > 0:
            print
            run = []
            complete = []

            for step_name in self.steps:
                step = self.steps[step_name]
                depends = step.depends

                if not depends or self.complete.get(step.depends, False):
                    run.append(step_name)
                    outcome = step.run()
                    if outcome:
                        self.complete[step_name] = outcome
                        complete.append(step_name)

            for step_name in complete:
                del self.steps[step_name]


if __name__ == '__main__':
    r = Runner()

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
                      'Mirror URL')])

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
