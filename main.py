from subprocess import Popen, PIPE
import threading
import Queue
import argparse
from itertools import product
import re
import time
from functools import partial

class Tailor(threading.Thread):
  def __init__(self, queue, lock, server, file, match = None, ignore = None):
    self.lock = lock
    threading.Thread.__init__(self)
    self.server = server
    self.file = file
    self.queue = queue
    self.daemon = True
    self.running = True
    self.match = match
    self.ignore = ignore
    self.start()


  def put_in_queue(self, data):
    if self.ignore and re.search(self.ignore, data):
      return
    if not self.match or re.search(self.match, data):
      self.queue.put((self.server, self.file, data))

  def connect(self):
    #I was getting some weird results where one thread would block out another
    #acquiring releasing the lock seems to work
    self.lock.acquire()
    try:
      command = ['ssh', '-t', self.server] if self.server not in ('localhost', 'local', '') else []
      self.tail_process = Popen(
        command + ['tail', '-f', self.file],
        stdout = PIPE,
        stdin = PIPE,
        stderr = PIPE
      )
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
    if not self.running:
      return self

    self.running = False

    print "Closing: %s:%s" % (self.server, self.file)
    try:
      self.tail_process.terminate()
    finally:
      self._Thread__stop()
      return self

def run(args):
  queue = Queue.Queue()
  lock = threading.Lock()
  T = partial(Tailor, queue, lock)
  server_file_combos = product(args.servers, args.files)
  trailers = [T(server, file, args.match, args.ignore) for server, file in server_file_combos]
  colors = { f: (91 + i) % 100 for i,f in enumerate(args.files) } if len(args.files)>1 else None
  if colors:
    for f in args.files:
      print_with_color(f, colors[f])
  tail(queue, colors, trailers)

def print_with_color(data, color):
  print "\033[%dm%s\033[0m" % (color, data)

def tail(queue, colors, trailers):
  try:
    while True:
      if queue.empty():
        time.sleep(.5)
        continue
      server, file, data = queue.get()
      if colors:
        print_with_color(data + "\r", colors[file])
      else:
        print data + "\r"

  except KeyboardInterrupt:
    for t in trailers:
      t.stop()

def parse_args():
  parser = argparse.ArgumentParser(description = 'Tail a file[s] across locally and/or across multiple servers')

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
    help = 'A comma seperated list of servers to connect to.  local for files on your computer'
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
