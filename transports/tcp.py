import dpkt, nfqueue
from transport import Transport
from connection import Connection
from socket import  inet_ntoa
from Queue import PriorityQueue
#from pudb import set_trace; set_trace()

class Tcp(Transport):

  def __init__(self, mode, applications, own_ip):
    Transport.__init__(self, mode, applications, own_ip)
    # Template class used for new connections
    self.connection = Tcpconnection
    self.name = 'TCP'

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
    self.state = 0
    self.states = {0:'CLOSED', 1:'SYN_SENT', 2:'SYNACK_RECV', 3:'ESTABLISHED'}
    self.out_transitions = {(0,'SYN'):1, (2,'ACK'):3}
    self.in_transitions = {(1,'ACKSYN'):2 }

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

