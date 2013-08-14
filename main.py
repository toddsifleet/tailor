from subprocess import Popen, PIPE
import threading
import Queue
import argparse
from itertools import product

class Tailor(threading.Thread):
  def __init__(self, queue, server, file, lock):
    self.lock = lock
    threading.Thread.__init__(self)
    self.server = server
    self.file = file
    self.queue = queue
    self.daemon = True
    self.running = True
    self.start()


  def put_in_queue(self, data):
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

def run(files, servers):
  queue = Queue.Queue()
  lock = threading.Lock()
  trailers = [Tailor(queue, server, file, lock) for server, file in product(servers, files)]
  colors = { f: (91 + i) % 100 for i,f in enumerate(files) } if len(files)>1 else None
  if colors:
    for f in files:
      print_with_color(f, colors[f])
  tail(queue, colors, trailers)

def print_with_color(data, color):
  print "\033[%dm%s\033[0m" % (color, data)

def tail(queue, colors, trailers):
  try:
    while True:
      server, file, data = queue.get()
      if colors:
        print_with_color(data + "\r", colors[file])
      else:
        print data + "\r"

  except KeyboardInterrupt:
    for t in trailers:
      t.stop().join()

def parse_args():
  parser = argparse.ArgumentParser(description = 'Tail a file[s] across locally and/or across multiple servers')
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

  servers = map(lambda x: x.strip(), args.servers.split(','))
  files = map(lambda x: x.strip(), args.files.split(','))
  return filter(bool, files), filter(bool, servers)

if __name__ == "__main__":
  run(*parse_args())
