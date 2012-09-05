#!/usr/bin/env python

#from pudb import set_trace; set_trace()

from dpkt import ip
import dpkt
import sys, os, nfqueue
from  heapq import heappop, heappush
from socket import AF_INET, AF_INET6, inet_ntoa, inet_aton, gethostbyname_ex, gethostname

count = 0
nodata_count = 0
queueno = 0
protocols = []
modes = ['TRANSPARENT', 'HALF', 'FULL']

# key: connection identification (src, sport)
# data: connection details Connection object
tcp = {}

class Connection():
  def __init__(self, module, (dst, dport), (src, sport)):
    self.module = module
    self.outgoing = ''
    self.outheap = []
    self.incoming = ''
    self.inheap = []
    self.server = (dst, dport)
    self.client = (src, sport)
    self.proxy = None
    self.outseq = 0 # last ACKed sequence number
    self.outseq_max = 0 # for detection of out of order packets
    self.inseq = 0 # last ACKed sequence number
    self.inseq_max = 0 # for detection of out of order packets
    self.in_extra = None # Optional information assigned by self.module routines
    self.out_extra = None # Optional information assigned by self.module routines

  def assemble_in(self):
    data = 0
    while len(self.inheap) > 0 and min(self.inheap)[0] <= self.inseq:
      data += len(min(self.inheap)[1])
      self.incoming += heappop(self.inheap)[1]

  def assemble_out(self):
    data = 0
    while len(self.outheap) > 0 and min(self.outheap)[0] <= self.outseq:
      data += len(min(self.outheap)[1])
      self.outgoing += heappop(self.outheap)[1]
    return data

  def push_in(self, t):
    """ push data tuple onto in-heap """
    print "pushed IN  seq %d len: %d" % (t[0],len(t[1]))
    heappush(self.inheap, t)

  def push_out(self, t):
    """ push data tuple onto out-heap """
    print "pushed OUT seq %d len: %d" % (t[0],len(t[1]))
    heappush(self.outheap, t)

  def handle(self):
    if self.module:
      self.module.handle(self)

def cb(payload):
    # TODO REMOVE
    payload.set_verdict(nfqueue.NF_ACCEPT)

    global count
    count += 1

    data = payload.get_data()
    # spawn IP packet
    try:
      pkt = ip.IP(data)
    except:
      print "unsupported Layer 2 protocol (not IP) dropped"
      payload.set_verdict(nfqueue.NF_DROP)

    frame = None

    # TCP only, for now.
    if pkt.p == dpkt.ip.IP_PROTO_TCP:
      frame = pkt.data      
    elif pkt.p == dpkt.ip.IP_PROTO_UDP:
      frame = pkt.data      
    elif pkt.p == dpkt.ip.IP_PROTO_ICMP:
      frame = pkt.data
      if frame.type == dpkt.icmp.ICMP_ECHO:
        print "ICMP ECHO %s" % inet_ntoa(pkt.dst)
        return 0
      elif frame.type == dpkt.icmp.ICMP_ECHOREPLY:
        print "ICMP REPLY from %s" % inet_ntoa(pkt.src)
        return 0
      #if frame.type >= dpkt.icmp.ICMP_UNREACH and \
      #   frame.type <= dpkt.icmp.ICMP_UNREACH_PRECEDENCE_CUTOFF:
      #  return 0
      else:
        return 1
    else:
      print "unsupported protocol %s recieved" % pkt.p
      #payload.set_verdict(nfqueue.NF_DROP)
      return 1

    # TODO check needed that no unsolicited SYN package
    # from outside pollutes the tcp dictionary?

    src = (pkt.src, frame.sport)
    dst = (pkt.dst, frame.dport)

    # for now. TODO
    if len(frame.data) == 0:
      # IF frame.flag = ACK and frame.type == outgoing:
      #   hand over from dictionary all (sorted) data
      #   with ACKNR < frame.ACKNR / set field to trigger
      #   passing of data below in else: ...
      if (frame.flags & dpkt.tcp.TH_ACK) != 0:
        if pkt.src == own_ip:
          if not src in tcp:
            newconnection(dst, src)
          tcp[src].inseq = frame.ack
          tcp[src].assemble_in()
          if tcp[src].module:
            tcp[src].handle()
          else:
            classify(tcp[src])
        elif dst in tcp:
          if not dst in tcp:
            newconnection(src, dst)
          tcp[dst].outseq = frame.ack
          tcp[dst].assemble_out()
          if tcp[dst].module:
            tcp[dst].handle()
          else:
            classify(tcp[dst])

      global nodata_count
      nodata_count += 1

      return 1

    # outgoing packet
    if pkt.src == own_ip:
      if src in tcp:
        if frame.seq < tcp[src].outseq:
          print "OUT OF ORDER PACKET --- OUTGOING --- ZOMG PONIES!!!"
        tcp[src].push_out((frame.seq, frame.data))
        tcp[src].assemble_out()
        if frame.seq >= tcp[src].outseq_max:
          tcp[src].outseq_max = frame.seq
        if not tcp[src].module:
          classify(tcp[src])
        else:
          tcp[src].handle()
      else:
        newconnection(dst, src, frame.data)
    # incoming packet
    else:
      if dst in tcp:
        if frame.seq < tcp[dst].inseq:
          print "OUT OF ORDER PACKET --- INCOMING --- ZOMG PONIES!!!"
        tcp[dst].push_in((frame.seq, frame.data))
        tcp[dst].assemble_out()
        if frame.seq >= tcp[dst].inseq_max:
          tcp[dst].inseq_max = frame.seq
        if not tcp[dst].module:
          classify(tcp[dst])
        else:
          tcp[dst].handle()
      else:
        newconnection(src, dst, frame.data)

#    if pkt.src == own_ip: {{{
#      if tcp[src].module:
#        tcp[src].handle()
#    else:
#      if tcp[dst].module:
#        tcp[dst].handle()

    # Annahme: irgendein Handler war passend TODO
    # TODO wenn FIN kommt, tcp[src|dst] aufraeumen
    # Annahme2: alle Pakete sind schon da und in der richtigen Reihenfolge
    # Hier auch dann die Gegenrichtung verarbeiten, damit (HTTP)
    # Request+Response gemeinsam ausgewertet werden koennen }}}
             
    #payload.set_verdict(nfqueue.NF_ACCEPT)
    #sys.stdout.flush()
    return 1

def newconnection(src, dst, data = ''):
  """ src: client tuple (ip, port)
  dst: server tuple(ip, port)
  data: sent/received data, may be empty """
  tcp[dst] = Connection(None, src, dst) 
  tcp[dst].incoming += data
  classify(tcp[dst])

def classify(connection):
  """ connection is a list [protocolhandler = None, data] """
  for protocol in protocols:
    if protocol.classify(connection):
      connection.module = protocol
      break

def print_connections():
  # TODO noch offene Verbindungen (i.e. len(data[1]) != 0) mit FIN,ACK
  # 'abschliessen'? -> NICHT im transparenten Modus
  for id, conn in tcp.items():
    #print "  inheap lang: %d incoming: %d" % (len(conn.inheap),len(conn.incoming))
    #print "  last ACKed : %d max seq: %d     " % (conn.inseq, conn.inseq_max)
    if conn.inseq < conn.inseq_max:
      print "Details for %s:%d" % (inet_ntoa(conn.server[0]), conn.server[1])
      print "  WARNING un-ACK-ed data in buffer"
    for k,v in conn.inheap:
      print "  seq: %s, data[%d]" % (k, len(v))

def load_modules(mod_dir):
  sys.path.append(mod_dir)
  mod_list = os.listdir(mod_dir)
  for module in mod_list:
    try:
      module_name, module_ext = os.path.splitext(module)
      if module_ext == '.py':
        mod = __import__(module_name)
        protocols.append(mod.init(mode))
        del mod
    except ImportError, e:
      print "import of module %s failed" % module

def nfq_setup():
  q = nfqueue.queue()
  q.set_callback(cb)
  try:
    q.fast_open(queueno, AF_INET)
  except RuntimeError, e:
    print "cannot bind to nf_queue %d" % queueno
  q.set_queue_maxlen(5000)
  
  try:
      q.try_run()
  except KeyboardInterrupt, e:
      pass
  
  print "\n%d packets handled (%d without data)" % (count, nodata_count)
  #print "Connection table"
  print_connections()
  q.unbind(AF_INET)
  q.close()
  #print_stats()

def print_stats():
  for protocol in protocols:
    if [method for method in dir(protocol) if callable(getattr(protocol, method))].count('get_stats') == 1:
      print "\n STATISTICS for protocol %s" % protocol.protocols()[0]
      protocol.get_stats()
    else:
      print "no stats available for protocol %s" % protocol.protocols()[0]

if __name__ == '__main__':
  mode = modes[0]
  print "sparring working in %s mode" % mode
  global own_ip
  # TODO funktioniert nicht immer
  own_ip = inet_aton('192.168.1.149') #inet_aton(gethostbyname_ex(gethostname())[2][0])
  print "using %s as own IP address" % inet_ntoa(own_ip)

  sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)),'lib'))

  mod_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)),'modules')

  load_modules(mod_dir)

  print "Loaded modules ",
  for protocol in protocols:
    print protocol.protocols(),
  print 

  nfq_setup()

