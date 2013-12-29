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

import nfqueue 
from transport import Transport, Sparringserver
from connection import Connection
from socket import  inet_ntoa, inet_aton, SOCK_DGRAM, socket, AF_INET

class Udp(Transport):

  def __init__(self, mode, applications, own_ip):
    Transport.__init__(self, mode, applications, own_ip)
    self.connection = Connection
    self.name = 'UDP'
    self.socktype = SOCK_DGRAM
    self.server = Udpserver

  def handle_transparent(self, pkt):
    datagram = pkt.data
    src = (pkt.src, datagram.sport)
    dst = (pkt.dst, datagram.dport)
    
    # outgoing packet
    if pkt.src == self.own_ip:
      if not src in self.connections:
        self.newconnection(src, dst)
    
      self.connections[src].put_out(datagram.data)
    
      if not self.connections[src].module:
        self.classify(self.connections[src])
      if self.connections[src].module:
        self.connections[src].handle()
    
    # incoming packet
    else:
      if not dst in self.connections:
        self.newconnection(dst, src)
    
      try:
        self.connections[dst].put_in(datagram.data)

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

class Udpserver(Sparringserver):

  def handle_read(self):
    data, src = self.recvfrom(8192)
    transport = self.transport
    src = (transport.own_ip, src[1])
    dst = (inet_aton('127.0.0.1'), 5001)
    if data:
      if not src in transport.connections:
        log.warning('udp: %s', transport.newconnection(src, dst))
      transport.connections[src].put_out(data)
      if not transport.connections[src].module:
        transport.classify(transport.connections[src])
      if transport.connections[src].module:
        transport.connections[src].handle()

  def writable(self):
    for host, conn in self.transport.connections.items():
      if conn.module and conn.in_extra and conn.in_extra['buffer']:
        # TODO hard-coded localhost for now..
        #self.socket.sendto(conn.in_extra['buffer'], ('127.0.0.1', host[1]))

        s = socket(AF_INET, self.transport.socktype)
        s.setblocking(0)
        s.bind(('127.0.0.1', 5002))
        log.debug('udp: sending to 127.0.0.1:%i' % conn.local[1])
        s.sendto(conn.in_extra['buffer'], ('127.0.0.1', conn.local[1]))
        conn.in_extra['buffer'] = '' # TODO don't be so harsh and truncate properly?
        s.close()
    
    return False
    #return (not self.connected) or len(self.transport.connections)

  def handle_write(self):
    return
    #if self.transport.connection.in_extra['buffer']:
    #  print 'could write'
    #  self.transport.connection.in_extra['buffer'] = ''
