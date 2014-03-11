from subprocess import Popen, PIPE
import threading
import Queue
import argparse
from itertools import product
import re
import time
from functools import partial

def print_with_color(data, color):
    print "\033[%dm%s\033[0m" % (color, data)

def split_strip_and_filter(input, delimeter = ','):
    output = map(lambda x: x.strip(), input.split(delimeter))
    return filter(bool, output)

class Tailor(threading.Thread):
    daemon = True
    running = True
    def __init__(self, queue, lock, server, file, match = None, ignore = None):
        self.lock = lock
        threading.Thread.__init__(self)
        self.server = server
        self.file = file
        self.queue = queue
        self.match = match
        self.ignore = ignore
        self.start()

    def _is_local(self):
        return self.server not in ('localhost', 'local', '')

    def _tail_command(self):
        command = ['ssh', '-t', self.server] if  self._is_local() else []
        return command + ['tail', '-f', self.file]

    def _start_tail_process(self):
        self.tail_process = Popen(
            self._tail_command(),
            stdout = PIPE,
            stdin = PIPE,
            stderr = PIPE
        )

    def put_in_queue(self, data):
        if self.ignore and re.search(self.ignore, data):
            return
        if not self.match or re.search(self.match, data):
            self.queue.put((self.server, self.file, data))

    def connect(self):
        self.lock.acquire()
        try:
            self._start_tail_process()
        except:
            self.stop()
        finally:
            self.lock.release()

    def run(self):
        self.connect()
        line = self.tail_process.stdout.readline()
        while line:
            line = self.tail_process.stdout.readline().strip()
            self.put_in_queue(line)
        self.stop()

    def stop(self):
        if self.running:
            print "Closing: %s:%s" % (self.server, self.file)
            self.stop_tailing_process()
        return self

    def stop_tailing_process(self):
        self.running = False
        try:
            self.tail_process.terminate()
        finally:
            self._Thread__stop()

class TailManager(object):
    match = None
    ignore = None
    def __init__(self, args):
        self.queue = Queue.Queue()
        self.lock = threading.Lock()
        self._init_args(args)
        self._set_colors()

    def run(self):
        try:
            self._tail()
        except KeyboardInterrupt:
            for t in self.trailers:
                t.stop()

    def _init_args(self, args):
        self.servers = split_strip_and_filter(args.servers)
        self.files = split_strip_and_filter(args.files)
        self._set_rules(args)

    def _set_rules(self, args):
        if args.ignore is not None:
            self.ignore = re.compile(args.ignore, re.I)
        if args.match is not None:
            self.match = re.compile(args.match, re.I)

    def _print_open(self, server, file):
        message = "Opening {file} on {server}".format(
            file = file,
            server = server
        )
        self._print(message, server, file)

    def _init_tailor(self, server, file):
        self._print_open(server, file)
        return Tailor(
            self.queue,
            self.lock,
            server,
            file,
            self.match,
            self.ignore
        )

    def _tail(self):
        self._start_trailers()
        while True:
            if self.queue.empty():
                time.sleep(.5)
            else:
                self._print_line()

    def _print_line(self):
        server, file, data = self.queue.get()
        self._print(data + "\r", server, file)

    def _start_trailers(self):
        server_file_combos = product(self.servers, self.files)
        self.trailers = [self._init_tailor(s, f) for s,f in  server_file_combos]

    def _print(self, message, server, file):
        identifier = server if self.color_by == 'server' else file
        print_with_color(message, self.colors[identifier])

    def _set_colors(self):
        if (len(self.servers) > 1):
            self.color_by = 'server'
            alternates = self.servers
        else:
            self.color_by = 'file'
            alternates = self.files
        self.colors = { f: (91 + i) % 100 for i, f in enumerate(alternates) }


def get_args():
    parser = argparse.ArgumentParser(
        description = 'Tail a file[s] locally or across across multiple servers'
    )

    parser.add_argument('-i', '--ignore',
        default = None,
        help = 'a regex string to ignore (similar to: tail -f <file> | grep -v <ignore>)'
    )

    parser.add_argument('-m', '--match',
        default = None,
        help = 'a regex string to match(similar to: tail -f <file> | grep <match>)'
    )

    parser.add_argument('files',
        type = str,
        help = 'The path to the file you want to tail'
    )

    parser.add_argument('servers',
        type = str,
        default = 'local',
        nargs = '?',
        help = 'A comma seperated list of servers to connect to.    local for files on your computer'
    )

    return parser.parse_args()

if __name__ == "__main__":
    TailManager(get_args()).run()
