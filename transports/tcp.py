# Copyright (c) Siemens AG, 2013
#
# This file is part of sparring.  sparring is free software: you can
# redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation; either version 2
# of the License, or(at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#

import dpkt, nfqueue
from transport import Transport, Sparringserver
from lib.connection import Connection
from socket import  inet_ntoa, inet_aton, SOCK_STREAM
from Queue import PriorityQueue
import asyncore
#from pudb import set_trace; set_trace()

class Tcp(Transport):

  def __init__(self, mode, applications, own_ip):
    Transport.__init__(self, mode, applications, own_ip)
    self.connection = Tcpconnection
    self.name = 'TCP'
    self.socktype = SOCK_STREAM
    self.server = Tcpserver

  def handle_transparent(self, pkt):
      # TODO check needed that no unsolicited SYN package
      # from outside pollutes the tcp dictionary?
  
      segment = pkt.data
      src = (pkt.src, segment.sport)
      dst = (pkt.dst, segment.dport)
  
      # TODO wenn FIN kommt, self.connections[src|dst] aufraeumen (leeren/letzes handle())
      if len(segment.data) == 0:
        if (segment.flags & dpkt.tcp.TH_ACK) != 0:
          #print "src: %s dst:%s" % (src, dst)
          # outgoing packet
          if pkt.src == self.own_ip:
            if not src in self.connections:
              self.newconnection(src, dst)
            self.connections[src].inseq = segment.ack
            self.connections[src].assemble_in()
            if not self.connections[src].module:
              self.classify(self.connections[src])
            if self.connections[src].module:
              self.connections[src].handle()
          # incoming packet
          #elif dst in self.connections:
          else:
            if not dst in self.connections:
              self.newconnection(dst, src)
            self.connections[dst].outseq = segment.ack
            self.connections[dst].assemble_out()
            if not self.connections[dst].module:
              self.classify(self.connections[dst])
            if self.connections[dst].module:
              self.connections[dst].handle()
  
        return (1, nfqueue.NF_STOP)
  
      # outgoing packet
      if pkt.src == self.own_ip:
        if src in self.connections:
          if segment.seq >= self.connections[src].outseq_max:
            self.connections[src].outseq_max = segment.seq
        else:
          self.newconnection(src, dst)
  
        self.connections[src].put_out((segment.seq, segment.data))
  
        if not self.connections[src].module:
          self.classify(self.connections[src])
        if self.connections[src].module:
          self.connections[src].handle()
  
      # incoming packet
      else:
        if dst in self.connections:
          if segment.seq >= self.connections[dst].inseq_max:
            self.connections[dst].inseq_max = segment.seq
        else:
          self.newconnection(dst, src)
  
        try:
          self.connections[dst].put_in((segment.seq, segment.data))
  
          if not self.connections[dst].module:
            self.classify(self.connections[dst])
          if self.connections[dst].module:
            self.connections[dst].handle()
        except KeyError:
          # This is triggered by Multicast packets sent from _other_ hosts so
          # we don't care for now.
          # print "%s:%d -> %s:%d" % (inet_ntoa(src[0]), src[1], inet_ntoa(dst[0]), dst[1])
          # 192.168.1.222:5353 -> 224.0.0.251:5353
          pass

      return (0, nfqueue.NF_STOP)
     
class Tcpconnection(Connection):
  def __init__(self, module, (dst, dport), (src, sport)):
    Connection.__init__(self, module, (dst, dport), (src, sport))
    self.outqueue = PriorityQueue()
    self.inqueue = PriorityQueue()
    self.outseq = 0 # last ACKed sequence number
    self.outseq_max = 0 # for detection of out of order packets
    
    # minimum sequence number that is allowed to get appended
    # i.e. packets that got inserted, ack'd AND retransmitted must not
    # be appended to the {incoming,outgoing} buffer again
    self.outseq_min = 0 
    self.inseq_min = 0

    self.inseq = 0 # last ACKed sequence number
    self.inseq_max = 0 # for detection of out of order packets

  def assemble_in(self):
    #while len(self.inbuf) > 0 and min(self.inbuf)[0] <= self.inseq:
    try:
      while self.inqueue.queue[0][0] <= self.inseq:
        seq, data = self.inqueue.get()
        if seq > self.inseq_min:
          #print data
          self.inseq_min = seq
          self.incoming.write(data)
    except:
      pass

  def assemble_out(self):
    try:
      while self.outqueue.queue[0][0] <= self.outseq:
        seq, data = self.outqueue.get()
        if seq > self.outseq_min:
          #print data
          self.outseq_min = seq
          self.outgoing.write(data)
    except:
      pass

  def put_in(self, t):
    """ put data tuple (seqnum, data) into the in_queue  """
    #print "pushed IN  seq %d len: %d" % (t[0],len(t[1]))
    self.inqueue.put(t)
    self.assemble_in()

  def put_out(self, t):
    """ put data tuple (seqnum, data) into the out_queue  """
    #print "pushed OUT seq %d len: %d" % (t[0],len(t[1]))
    self.outqueue.put(t)
    self.assemble_out()

class Tcpserver(Sparringserver):
  def __init__(self, port, transport, map):
    self.map = map
    Sparringserver.__init__(self, port, transport, map)
    self.listen(5)

  # TODO Teile eventuell nach handle_connect() auslagern, das erst spaeter im
  # Verbindungsaufbau (erfolg) greift?
  def handle_accept(self):
    pair = self.accept()
    if pair is None:
      pass
    else:
      sock, addr = pair
      # addr == client == sock.getpeername() == addr
      # sock.getsockname() == us
      # TODO noch nicht ganz richtig ;)
      local = sock.getsockname()
      # TODO may raise exception, too, WTF :)
      # socket.error: [Errno 107] Transport endpoint is not connected
      try:
        remote = sock.getpeername()
        dst = (inet_aton(remote[0]),remote[1]) 
        src = (inet_aton(local[0]),local[1])
        conn = self.transport.newconnection(src, dst)
        handler = Tcphandler(conn, sock, self.map)

      except Exception, e:
        log.warn("tcp: while accepting new connection")
        log.warn(e)

class Tcphandler(asyncore.dispatcher):

  def __init__(self, conn, sock=None, map=None):
      asyncore.dispatcher.__init__(self, sock, map)
      self.conn = conn

  def handle_read(self):
    data = self.recv(8192)
    if data:
      # echo halt...
      #print "sending back %s" % data
      #self.send(data)

      # we don't use conn.put_in() because there's no need for TCP 
      # connections to reassemble the data as our underlying socket did that
      # already for us. So just fill the outgoing buffer
      self.conn.outgoing.write(data)
      if self.conn.classify():
        self.conn.handle()
      else:
        log.debug("tcp: application protocol not identified")
        log.debug("tcp: " + self.conn)
      if self.writable():
        self.handle_write()
  
  def writable(self):
    #self.conn.handle()
    #return True
    return self.conn.in_extra and 'buffer' in self.conn.in_extra and self.conn.in_extra['buffer']

  def readable(self):
    return True

  def handle_write(self):
    try:
      #self.conn.handle()
      sent = self.send(self.conn.in_extra['buffer'])
      #print "sendt to client: %s" % self.conn.in_extra['buffer'][:sent]
      self.conn.in_extra['buffer'] = self.conn.in_extra['buffer'][sent:]
    except Exception, e:
      # TODO ja doch macht schon was : )
      log.warn("tcp: while handling outgoing data")
      log.warn(e)
      return

    # application has no work left and all data was sent
    if self.conn.in_extra['close'] and not self.conn.in_extra['buffer']:
      self.handle_close()

  def handle_close(self):
    """ seems to get called multiple times for the same connection, so pay
    attention wether self.conn still is set or not """
    self.close()
    return

    if self.conn.incoming.getvalue() or self.conn.outgoing.getvalue():
      log.warn("tcp: not all data handled")

    del self.conn # TODO aus oberer instanz loeschen?
    log.debug("tcp: closing socket")
    self.close()


