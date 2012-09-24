from stats import Stats
import StringIO, re
from socket import inet_ntoa, inet_aton
from pprint import pprint
#from pudb import set_trace; set_trace()

def init(mode):
  return Irc(mode)

class Ircstats(Stats):
  
  def __init__(self):
    Stats.__init__(self)

  def __str__(self):
    ret = ''
    for server, irc in self.servers.items():
      ret += "\n%s %d\n" % (inet_ntoa(server[0]), server[1])
      for channel, log in irc.channel.items():
        ret += "\n  %s\n" % str(channel)
        for msg in log:
          ret += "    %s\n" % msg
    else:
      return ret

  def addchannel(self, conn, channel):
    if not self.servers[conn.remote].channel.has_key(channel):
      self.servers[conn.remote].channel[channel] = []
    return self.servers[conn.remote].channel[channel]

  def addnick(self, conn, nick):
    self.servers[conn.remote].meta['Nick'] = nick

  def getnick(self, conn):
    if self.servers[conn.remote].meta.has_key('Nick'):
      return self.servers[conn.remote].meta['Nick']
    else:
      return None

  def addmsg(self, conn, channel, msg):
    chan = self.addchannel(conn, channel)
    chan += [ msg ]

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
      print "FOUND IRC"
    return nick and user

  def get_stats(self):
    print self.stats
    #for server, details in self.servers.items():
    #  print "%15.15s:%-4d    via PROXY: %r" % (inet_ntoa(server[0]), server[1], details)

  def irc_methods(self, conn, direction):
    nick = 'DEFAULT'
    parsed = 0
    if direction == 'out':
      lines = conn.outgoing.splitlines()
    else:
      lines = conn.incoming.splitlines()
    #if conn.outgoing.endswith('\n'):
    #  msgs = len(lines)
    #else:
    #  # last message was not (yet) fully received
    #  msgs = len(lines) - 1

    for l in lines:
      parsed += len(l)+1
      try:
        command, arg = l.split(" ", 1)
        cmd = command.upper()
        if cmd == 'JOIN':
          self.stats.addchannel(conn, arg)
        elif cmd == 'NICK':
          self.stats.addnick(conn, arg)
          nick = arg
        # outgoing chatter
        elif cmd == 'PRIVMSG':
          chan, msg = arg.split(' :')
          self.stats.addmsg(conn, chan, ">%s< %s" % (self.stats.getnick(conn), msg))
        elif cmd in ['WHO', 'MODE', 'PING', 'WHOIS', 'PONG', 'PART', 'QUIT']:
          pass
        # incoming chatter
        elif arg.split()[0].upper() ==  'PRIVMSG':
          if command[0] == ':':
            sender = command[1:]
          else:
            sender = command
          chan = arg[8:].split()[0]
          msg = arg.split(':', 1)[1]
          #if chan[0] in [ '&', '#', '!' ]:
          self.stats.addmsg(conn, chan, "<%s> %s" % (sender, msg))
      except Exception, e:
        print e
        print l
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
    self.stats.addserver2(conn.remote)
    conn.outgoing = conn.outgoing[self.irc_methods(conn, 'out'):]
    conn.incoming = conn.incoming[self.irc_methods(conn, 'in'):]

  def handle_half(self, conn):
    pass

  def handle_full(self, conn):
    pass
