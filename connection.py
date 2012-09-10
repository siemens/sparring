from Queue import Queue, PriorityQueue

class Connection():
  def __init__(self, module, (dst, dport), (src, sport)):
    self.module = module
    self.outgoing = ''
    self.outqueue = Queue()
    self.incoming = ''
    self.inqueue = Queue()
    self.server = (dst, dport)
    self.client = (src, sport)
    self.proxy = None
    self.in_extra = None # Optional information assigned by self.module routines
    self.out_extra = None # Optional information assigned by self.module routines

  def put_in(self, t):
    """ add new data to the buffer """
    self.incoming += t

  def put_out(self, t):
    """ add new data to the buffer """
    self.outgoing += t

  def handle(self):
    if self.module:
      self.module.handle(self)

class Tcpconnection(Connection):
  def __init__(self, module, (dst, dport), (src, sport)):
    Connection.__init__(self, module, (dst, dport), (src, sport))
    self.outqueue = PriorityQueue()
    self.inqueue = PriorityQueue()
    self.outseq = 0 # last ACKed sequence number
    self.outseq_max = 0 # for detection of out of order packets
    self.inseq = 0 # last ACKed sequence number
    self.inseq_max = 0 # for detection of out of order packets

  def assemble_in(self):
    #while len(self.inbuf) > 0 and min(self.inbuf)[0] <= self.inseq:
    try:
      while self.inqueue.queue[0][0] <= self.inseq:
        self.incoming += self.inqueue.get()[1]
    except:
      pass

  def assemble_out(self):
    try:
      while self.outqueue.queue[0][0] <= self.outseq:
        self.outgoing += self.outqueue.get()[1]
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
