import nfqueue 
from protocol import Protocol
from connection import Connection
from socket import  inet_ntoa

class Udp(Protocol):

  # key: connection identification (src, sport)
  # data: connection details Connection object
  udp = {}

  def items(self):
    return self.udp

  def handle_transparent(self, pkt):
    datagram = pkt.data
    src = (pkt.src, datagram.sport)
    dst = (pkt.dst, datagram.dport)
    
    # outgoing packet
    if pkt.src == self.own_ip:
      if not src in self.udp:
        self.newconnection(self.udp, Connection, src, dst)
    
      self.udp[src].put_out(datagram.data)
    
      if not self.udp[src].module:
        self.classify(self.udp[src])
      if self.udp[src].module:
        self.udp[src].handle()
    
    # incoming packet
    else:
      if not dst in self.udp:
        self.newconnection(self.udp, Connection, dst, src)
    
      # TODO handle
      try:
        self.udp[dst].put_in(datagram.data)
        if not self.udp[dst].module:
          self.classify(self.udp[dst])
        if self.udp[dst].module:
          self.udp[dst].handle()
      except Exception,e:
        print "%s:%d -> %s:%d" % (inet_ntoa(src[0]), src[1], inet_ntoa(dst[0]), dst[1])
        print str(e)
    
    return (0, nfqueue.NF_STOP)

