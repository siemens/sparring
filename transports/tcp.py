import dpkt, nfqueue
from transport import Transport
from connection import Connection
from socket import  inet_ntoa
from Queue import PriorityQueue

class Tcp(Transport):

  def __init__(self, mode, applications, own_ip):
    Transport.__init__(self, mode, applications, own_ip)
    # Template class used for new connections
    self.connection = Tcpconnection

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
  
        self.connections[dst].put_in((segment.seq, segment.data))
  
        if not self.connections[dst].module:
          self.classify(self.connections[dst])
        if self.connections[dst].module:
          self.connections[dst].handle()
  
      return (0, nfqueue.NF_STOP)

  def handle_half(self, data):
      # TODO check needed that no unsolicited SYN package
      # from outside pollutes the tcp dictionary?

      if not self.classify(self.connection):
        return
      self.connection.handle()

     
class Tcpconnection(Connection):
  def __init__(self, module, (dst, dport), (src, sport)):
    Connection.__init__(self, module, (dst, dport), (src, sport))
    self.outqueue = PriorityQueue()
    self.inqueue = PriorityQueue()
    self.outseq = 0 # last ACKed sequence number
    self.outseq_max = 0 # for detection of out of order packets
    self.inseq = 0 # last ACKed sequence number
    self.inseq_max = 0 # for detection of out of order packets
    self.state = 0
    self.states = {0:'CLOSED', 1:'SYN_SENT', 2:'SYNACK_RECV', 3:'ESTABLISHED'}
    self.out_transitions = {(0,'SYN'):1, (2,'ACK'):3}
    self.in_transitions = {(1,'ACKSYN'):2 }

  def assemble_in(self):
    #while len(self.inbuf) > 0 and min(self.inbuf)[0] <= self.inseq:
    try:
      while self.inqueue.queue[0][0] <= self.inseq:
        self.incoming.write(self.inqueue.get()[1])
    except:
      pass

  def assemble_out(self):
    try:
      while self.outqueue.queue[0][0] <= self.outseq:
        self.outgoing.write(self.outqueue.get()[1])
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

  def transition(self, input=None, output=None):
    if input:
      try:
        self.state = self.in_transitions[(self.state, input)]
      except:
        print "ERROR: illegal transition from: %s via %s" % (self.states[self.state], input)
        return False
    if output:
      try:
        self.state = self.out_transitions[(self.state, output)]
      except:
        print "ERROR: illegal transition from: %s via %s" % (self.states[self.state], output)
        return False
    return True

