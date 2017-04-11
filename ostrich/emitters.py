#!/usr/bin/env python
#
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
import gzip
import os
import sys
import textwrap


class NoopEmitter(object):
    def __init__(self, progname, output):
        self.progname = progname
        self.output = output
        self.logfile = None

    def clear(self):
        pass

    def logger(self, logfile):
        pass

    def emit(self, s):
        pass

    def getstr(self, s):
        return None


class LoggingEmitter(NoopEmitter):
    def logger(self, logfile):
        if self.logfile:
            self.logfile.close()
        self.logfile = gzip.open(
            os.path.expanduser('~/.%s/%s.gz'
                               % (self.progname, logfile)), 'w')


class Emitter(LoggingEmitter):
    def clear(self):
        self.output.clear()

    def emit(self, s):
        height, width = self.output.getmaxyx()

        for line in s.split('\n'):
            line = ''.join([i if ord(i) < 128 else ' ' for i in line])

            if self.logfile:
                self.logfile.write('%s %s\n' % (datetime.datetime.now(), line))
                self.logfile.flush()

            for l in textwrap.wrap(line, width - 3):
                if len(l) > 0:
                    self.output.scroll()
                    self.output.addstr(height - 2, 1, ' ' * (width - 1))

                    try:
                        self.output.addstr(height - 2, 2, l)
                    except Exception as e:
                        print('Exception: %s' % e)
                        print('>>%s<<' % line)
                        sys.exit(1)

        self.output.border()
        self.output.refresh()

    def getstr(self, s):
        height, width = self.output.getmaxyx()

        self.emit(s)
        curses.echo()
        answer = self.output.getstr(height - 2, len(s) + 2)
        curses.noecho()
        return answer


class SimpleEmitter(LoggingEmitter):
    def clear(self):
        sys.stdout.write('-----------------------------------------------\n')

    def emit(self, s):
        for line in s.split('\n'):
            line = ''.join([i if ord(i) < 128 else ' ' for i in line])

            if self.logfile:
                self.logfile.write('%s %s\n' % (datetime.datetime.now(), line))
                self.logfile.flush()

            sys.stdout.write('%s\n' % line)
            sys.stdout.flush()

    def getstr(self, s):
        answer = raw_input(s)
        return answer
