from stats import Stats
import cStringIO, re, irclib, os, hashlib
from socket import inet_ntoa, inet_aton
from misc import ltruncate

from ircd import ircd

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
    if not channel in self.servers[conn.remote].channel:
      self.servers[conn.remote].channel[channel] = []
    return self.servers[conn.remote].channel[channel]

  def addnick(self, conn, nick):
    self.servers[conn.remote].meta['Nick'] = nick

  def getnick(self, conn):
    if 'Nick' in self.servers[conn.remote].meta:
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
    user = True
    pos = conn.outgoing.tell()
    conn.outgoing.seek(0)
    lines = conn.outgoing.readlines()
    conn.outgoing.seek(pos)
    for l in lines:
      if l.startswith('NICK'):
        nick = True
        continue
      if l.startswith('USER'):
        user = True
    if nick and user:
      self.setup(conn)
      return True

  def get_stats(self):
    print self.stats
    #for server, details in self.servers.items():
    #  print "%15.15s:%-4d    via PROXY: %r" % (inet_ntoa(server[0]), server[1], details)

  # parse data sent to the client
  def irc_in(self, conn):
    parsed = 0
    pos = conn.incoming.tell()
    conn.incoming.seek(0)
    lines = conn.incoming.readlines()
    conn.incoming.seek(pos)
    #if conn.outgoing.endswith('\n'):
    #  msgs = len(lines)
    #else:
    #  # last message was not (yet) fully received
    #  msgs = len(lines) - 1

    for l in lines:
      parsed += len(l)+1
      try:
        sender, arg = l.split(" ", 1)
        sender = sender[1:]
        arg = arg.rstrip()
        cmd, msg = arg.split(" ", 1)
        cmd = cmd.upper()
        # incoming chatter
        if cmd == 'JOIN':
          self.stats.addchannel(conn, msg)
        elif cmd == 'PRIVMSG':
          chan, msg = msg.split(' :', 1)
          self.stats.addmsg(conn, chan, "<%s> %s" % (sender, msg))
        elif cmd in ['WHO', 'MODE', 'PING', 'WHOIS', 'PONG', 'PART', 'QUIT']:
          pass
      # other commands are ignored for now
      except Exception, e:
        print e
        pass
    return parsed 

  # parse data sent by the client
  def irc_out(self, conn):
    parsed = 0
    pos = conn.outgoing.tell()
    conn.outgoing.seek(0)
    lines = conn.outgoing.readlines()
    conn.outgoing.seek(pos)
    #if conn.outgoing.endswith('\n'):
    #  msgs = len(lines)
    #else:
    #  # last message was not (yet) fully received
    #  msgs = len(lines) - 1

    for l in lines:
      parsed += len(l)+1
      try:
        command, arg = l.split(" ", 1)
        command = command.rstrip('\n')
        arg = arg.rstrip()
        cmd = command.upper()
        if cmd == 'NICK':
          self.stats.addnick(conn, arg)
        # outgoing chatter
        elif cmd == 'PRIVMSG':
          chan, msg = arg.split(' :')
          name = self.stats.servers[conn.remote].meta['Nick']
          message = ">%s< %s" % (name, msg)
          self.stats.addmsg(conn, chan, message)
        elif cmd == 'QUIT':
          conn.in_extra['close'] = True
        elif cmd in ['WHO', 'MODE', 'PING', 'WHOIS', 'PONG', 'PART', 'QUIT']:
          pass
      # other commands are ignored for now
      except Exception, e:
        pass
    return parsed 

  def setup(self, conn):
    conn.in_extra = {}
    if self.mode == 'TRANSPARENT':
      pass
    elif self.mode == 'HALF':
      # could be in_extra, too, does not really matter
      irc = irclib.IRC()
      conn.out_extra = {}
      conn.out_extra['irc'] = irc
      conn.out_extra['irc_server'] = irc.server()
      conn.in_extra['buffer'] = ""
      # close this connection
      conn.in_extra['close'] = False
    elif self.mode == 'FULL':
      conn.out_extra = {}
      conn.in_extra['buffer'] = ""
      # close this connection
      conn.in_extra['close'] = False
      irc = ircd(hashlib.md5(os.urandom(128)).hexdigest()[:16] + ".com")
      # data coming from our server
      conn.in_extra['irc_server'] = irc.server
      # data coming from the client
      conn.out_extra['irc_server'] = irc.client

  def handle(self, conn):
    if self.mode == 'TRANSPARENT':
      self.handle_transparent(conn)
    elif self.mode == 'HALF':
      self.handle_half(conn)
    elif self.mode == 'FULL':
      self.handle_full(conn)

  def handle_transparent(self, conn):
    self.stats.addserver2(conn.remote)
    out = self.irc_out(conn) 
    inc = self.irc_in(conn)
    conn.outgoing = ltruncate(conn.outgoing, out)
    conn.incoming = ltruncate(conn.incoming, inc)

  def handle_half(self, conn):
    self.stats.addserver2(conn.remote)
    server = conn.out_extra['irc_server']
    out = self.irc_out(conn)

    if not server.connected:
      server.connect(inet_ntoa(conn.remote[0]), conn.remote[1], self.stats.getnick(conn))
    conn.outgoing.reset()
    # take care that only full chunks (lines) of data are sent
    sendit = conn.outgoing.read(out)
    if sendit:
      server.send_raw(sendit)
      #print "sendt to server: %s" % sendit
    conn.outgoing = truncate(conn.outgoing)
    #print "left in out buffer: %s" % conn.outgoing.getvalue()

    sock = server.socket     
    # TODO take care that only full chunks are put in here, too
    # TODO 2 parsen in irc_in (string vs. file handle!) f. statistik!
    try:
      sock.setblocking(0)
      conn.in_extra['buffer'] += sock.recv(8192)
      sock.setblocking(1)
    # socket may not have any data to fetch
    except Exception, e:
      pass
    #print "recv from server:--\n%s\n--" % conn.in_extra['buffer']
    # TODO weiterer Puffer fuer unvollstaendige Zeilen
    if conn.in_extra['buffer']:
      conn.incoming.write(conn.in_extra['buffer'])
      self.irc_in(conn)
      conn.incoming.truncate(0)

    if conn.in_extra['close']:
      try:
        server.close()
      except:
        pass
 
  def handle_full(self, conn):
    self.stats.addserver2(conn.remote)
    i = conn.out_extra['irc_server']
    # TODO assure that only fully sent lines are parsed
    out = self.irc_out(conn)
    conn.outgoing.reset()
    sendit = conn.outgoing.read()
    if sendit:
      i.dataReceived(sendit)
    conn.outgoing = ltruncate(conn.outgoing)
    
    t = conn.in_extra['irc_server']
    conn.in_extra['buffer'] += t.value()
    t.clear()

    if conn.in_extra['buffer']:
      conn.incoming.write(conn.in_extra['buffer'])
      self.irc_in(conn)
      conn.incoming.truncate(0)

    if conn.in_extra['close']:
      try:
        i.connectionLost('asdf')
      except:
        pass

