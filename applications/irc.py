from stats import Stats
import StringIO, re
from socket import inet_ntoa, inet_aton
from pprint import pprint
#from pudb import set_trace; set_trace()

def init(mode):
  return Irc(mode)

class Ircstats(Stats):
  
  def addchannel(self, conn, channel):
    self.cats['Server'][conn.remote] += [ channel ]

class Irc():
  stats = Ircstats()

  def __init__(self, mode):
    # one of TRANSPARENT, FULL, HALF
    self.mode = mode

  def protocols(self):
    return ['irc']

  def classify(self, conn):
    nick = False
    user = False
    lines = conn.outgoing.splitlines()
    for l in lines:
      if l.startswith('NICK'):
        nick = True
        continue
      if l.startswith('USER'):
        user = True
    if nick and user:
    return nick and user

  def get_stats(self):
    print self.stats
    #for server, details in self.servers.items():
    #  print "%15.15s:%-4d    via PROXY: %r" % (inet_ntoa(server[0]), server[1], details)

  def irc_methods(self, conn):
    parsed = 0
    lines= conn.outgoing.splitlines()
    if conn.outgoing.endswith('\n'):
      msgs = len(lines)
    else:
      # last message was not (yet) fully received
      msgs = len(lines) - 1

    for l in lines:
      parsed += len(l)+1
      try:
        command, arg = l.split(" ", 1)
        if command.upper() == 'JOIN':
          self.stats.addchannel(conn, arg)
      except:
        pass
    return parsed 

  def handle(self, conn):
    if self.mode == 'TRANSPARENT':
      self.handle_transparent(conn)
    if self.mode == 'HALF':
      self.handle_half(conn)
    if self.mode == 'FULL':
      self.handle_full(conn)

  def handle_transparent(self, conn):
    print str(conn.outgoing)
    conn.outgoing = conn.outgoing[self.irc_methods(conn):]
    self.stats.addserver(conn.remote)

  def handle_half(self, conn):
    pass

  def handle_full(self, conn):
    pass
