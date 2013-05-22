import nfqueue 
from transport import Transport
from connection import Connection
from socket import  inet_ntoa

class Udp(Transport):

  def __init__(self, mode, applications, own_ip):
    Transport.__init__(self, mode, applications, own_ip)
    self.connection = Connection
    self.name = 'UDP'

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

