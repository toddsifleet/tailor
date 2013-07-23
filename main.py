from subprocess import Popen, PIPE
import threading
import Queue
import argparse
from itertools import product

class Tailor(threading.Thread):
  def __init__(self, queue, server, file):
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
    command = ['ssh', '-t', self.server] if not self.server in ('localhost', 'local') else []
    self.tail_process = Popen(
      command + ['tail', '-f', self.file],
      stdout = PIPE,
      stdin = PIPE,
      stderr = PIPE
    )

  def run(self):
    self.connect()
    line = self.tail_process.stdout.readline()
    while self.running:
      line = self.tail_process.stdout.readline()
      self.put_in_queue(line.strip())
    self.running = False

  def stop(self):
    print "Closing: %s:%s" % (self.server, self.file)
    try:
      self.tail_process.terminate()
    finally:
      self._Thread__stop()
      return self

def run(files, servers):
  queue = Queue.Queue()
  trailers = [Tailor(queue, server, file) for server, file in product(servers, files)]
  colors = { f: (91 + i) % 100 for i,f in enumerate(files) } if len(files)>1 else None
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
  parser = argparse.ArgumentParser(description = 'Tail a file across multiple servers')
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
  print files, servers
  return files, servers

if __name__ == "__main__":
  run(*parse_args())
