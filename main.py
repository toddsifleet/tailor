from subprocess import Popen, PIPE
import threading
import Queue
import argparse
from itertools import product
import re
import time
from functools import partial

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

def get_colors(files, servers):
    alternates = files if len(files) > 1 else servers
    colors = { f: (91 + i) % 100 for i, f in enumerate(alternates) }

    if len(files) > 1:
        return lambda f, _: colors[f]
    elif len(servers) > 1:
        return lambda _, s: colors[s]
    else:
        return None

def initialize(args):
    queue = Queue.Queue()
    lock = threading.Lock()
    T = partial(Tailor, queue, lock)
    server_file_combos = product(args.servers, args.files)
    trailers = [T(server, file, args.match, args.ignore) for server, file in server_file_combos]
    colors = get_colors(args.files, args.servers)
    if colors:
        for s, f in server_file_combos:
            print_with_color(f, colors(f, s))
    return queue, colors, trailers

def print_with_color(data, color):
    print "\033[%dm%s\033[0m" % (color, data)

def tail(queue, colors, trailers):
    while True:
        if queue.empty():
            time.sleep(.5)
            continue
        server, file, data = queue.get()
        if colors:
            print_with_color(data + "\r", colors(file, server))
        else:
            print data + "\r"

def run(args):
    queue, color, trailers = initialize(args)
    try:
      tail(queue, color, trailers)
    except KeyboardInterrupt:
        for t in trailers:
            t.stop()

def parse_args():
    parser = argparse.ArgumentParser(description = 'Tail a file[s] locally or across across multiple servers')

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

    args = parser.parse_args()

    args.servers = filter(bool, map(lambda x: x.strip(), args.servers.split(',')))
    args.files = filter(bool, map(lambda x: x.strip(), args.files.split(',')))
    if args.ignore is not None:
        args.ignore = re.compile(args.ignore, re.I)
    if args.match is not None:
        args.match = re.compile(args.match, re.I)
    return args

if __name__ == "__main__":
    run(parse_args())
