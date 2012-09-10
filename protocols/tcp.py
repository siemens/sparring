import dpkt, nfqueue
from protocol import Protocol
from connection import Tcpconnection, Connection
from socket import  inet_ntoa

class Tcp(Protocol):

  # key: connection identification (src, sport)
  # data: connection details Connection object
  tcp = {}

  def items(self):
    return self.tcp

  def handle_transparent(self, pkt):
      # TODO check needed that no unsolicited SYN package
      # from outside pollutes the tcp dictionary?
  
      segment = pkt.data
      src = (pkt.src, segment.sport)
      dst = (pkt.dst, segment.dport)
  
      # TODO wenn FIN kommt, self.tcp[src|dst] aufraeumen (leeren/letzes handle())
      if len(segment.data) == 0:
        if (segment.flags & dpkt.tcp.TH_ACK) != 0:
          # outgoing packet
          if pkt.src == self.own_ip:
            if not src in self.tcp:
              self.newconnection(self.tcp, Tcpconnection, src, dst)
            self.tcp[src].inseq = segment.ack
            self.tcp[src].assemble_in()
            if not self.tcp[src].module:
              self.classify(self.tcp[src])
            if self.tcp[src].module:
              self.tcp[src].handle()
          # incoming packet
          elif dst in self.tcp:
            if not dst in self.tcp:
              self.newconnection(self.tcp, Tcpconnection, dst, src)
            self.tcp[dst].outseq = segment.ack
            self.tcp[dst].assemble_out()
            if not self.tcp[dst].module:
              self.classify(self.tcp[dst])
            if self.tcp[dst].module:
              self.tcp[dst].handle()
  
        return (1, nfqueue.NF_STOP)
  
      # outgoing packet
      if pkt.src == self.own_ip:
        if src in self.tcp:
          if segment.seq >= self.tcp[src].outseq_max:
            self.tcp[src].outseq_max = segment.seq
        else:
          self.newconnection(self.tcp, Tcpconnection, src, dst)
  
        self.tcp[src].put_out((segment.seq, segment.data))
  
        if not self.tcp[src].module:
          self.classify(self.tcp[src])
        if self.tcp[src].module:
          self.tcp[src].handle()
  
      # incoming packet
      else:
        if dst in self.tcp:
          if segment.seq >= self.tcp[dst].inseq_max:
            self.tcp[dst].inseq_max = segment.seq
        else:
          self.newconnection(self.tcp, Tcpconnection, dst, src)
  
        self.tcp[dst].put_in((segment.seq, segment.data))
  
        if not self.tcp[dst].module:
          self.classify(self.tcp[dst])
        if self.tcp[dst].module:
          self.tcp[dst].handle()
  
      return (0, nfqueue.NF_STOP)

