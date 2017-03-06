import curses
import datetime
import fcntl
import json
import os
import psutil
import re
import select
import subprocess
import sys
import textwrap
import time

import emitters


class Step(object):
    def __init__(self, name, depends=None, max_attempts=5):
        self.name = name
        self.depends = depends
        self.attempts = 0
        self.max_attempts = max_attempts


class SimpleCommandStep(Step):
    def __init__(self, name, command, depends=None, cwd=None, env=None,
                 max_attempts=5):
        super(SimpleCommandStep, self).__init__(name, depends=depends,
                                                max_attempts=max_attempts)
        self.command = command
        self.cwd = cwd

        self.env = os.environ
        self.env.update(env)

    def __str__(self):
        return 'step %s, depends on %s' % (self.name, self.depends)

    def run(self, emit, screen):
        emit.emit('Running %s' % self)
        emit.emit('# %s\n' % self.command)
        self.attempts += 1

        if self.attempts > self.max_attempts:
            emit.emit('... repeatedly failed step, giving up')
            sys.exit(1)

        obj = subprocess.Popen(self.command,
                               stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE,
                               shell=True,
                               cwd=self.cwd,
                               env=self.env)
        proc = psutil.Process(obj.pid)
        procs = {}

        flags = fcntl.fcntl(obj.stdout, fcntl.F_GETFL)
        fcntl.fcntl(obj.stdout, fcntl.F_SETFL, flags | os.O_NONBLOCK)

        flags = fcntl.fcntl(obj.stderr, fcntl.F_GETFL)
        fcntl.fcntl(obj.stderr, fcntl.F_SETFL, flags | os.O_NONBLOCK)

        obj.stdin.close()
        while obj.poll() is None:
            readable, _, _ = select.select([obj.stderr, obj.stdout], [], [], 0)
            for f in readable:
                emit.emit(os.read(f.fileno(), 10000))

            seen = []
            for child in proc.children(recursive=True):
                try:
                    seen.append(child.pid)
                    if child.pid not in procs:
                        procs[child.pid] = ' '.join(child.cmdline())
                        emit.emit('*** process started *** %d -> %s'
                                  % (child.pid, procs[child.pid]))
                except psutil.NoSuchProcess:
                    pass

            ended = []
            for pid in procs:
                if pid not in seen:
                    emit.emit('*** process ended *** %d -> %s'
                              % (pid, procs.get(child.pid, '???')))
                    ended.append(pid)

            for pid in ended:
                del procs[pid]

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


class RegexpEditorStep(Step):
    def __init__(self, name, path, search, replace, cwd=None, env=None):
        super(RegexpEditorStep, self).__init__(name)
        self.path = path
        if cwd and not path.startswith('/'):
            self.path = os.path.join(cwd, path)

        self.search = search
        self.replace = replace

    def run(self, emit, screen):
        output = []
        changes = 0

        emit.emit('--- %s' % self.path)
        emit.emit('+++ %s' % self.path)

        with open(self.path, 'r') as f:
            for line in f.readlines():
                line = line.rstrip()
                newline = re.sub(self.search, self.replace, line)
                output.append(newline)

                if newline != line:
                    emit.emit('- %s' % line)
                    emit.emit('+ %s' % newline)
                    changes += 1
                else:
                    emit.emit('  %s' % line)

        with open(self.path, 'w') as f:
            f.write('\n'.join(output))

        return 'Changed %d lines' % changes


class BulkRegexpEditorStep(Step):
    def __init__(self, name, path, file_filter, replacements, cwd=None,
                 env=None):
        super(BulkRegexpEditorStep, self).__init__(name)
        self.path = path
        if cwd and not path.startswith('/'):
            self.path = os.path.join(cwd, path)

        self.file_filter = re.compile(file_filter)
        self.replacements = replacements

    def run(self, emit, screen):
        silent_emitter = emitters.NoopEmitter('noop', None)
        changes = 0

        for root, _, files in os.walk(self.path):
            for filename in files:
                m = self.file_filter.match(filename)
                if not m:
                    continue

                path = os.path.join(root, filename)
                for (search, replace) in self.replacements:
                    s = RegexpEditorStep('bulk-edit', path, search, replace)
                    result = s.run(silent_emitter, None)
                    emit.emit('%s -> %s' % (path, result))
                    if result != 'Changed 0 lines':
                        changes += 1

        return changes
