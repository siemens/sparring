#!/usr/bin/env python

#from pudb import set_trace; set_trace()

from dpkt import ip
import dpkt
import sys, os, nfqueue
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
    self.outdict = {}
    self.incoming = ''
    self.indict = {}
    self.server = (dst, dport)
    self.client = (src, sport)
    self.proxy = None
    self.seq = 0 # last ACKed sequence number

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
        if pkt.src == own_ip and src in tcp:
          tcp[src].seq = frame.ack

      global nodata_count
      nodata_count += 1
      return 1

    # outgoing packet
    if pkt.src == own_ip:
      if src in tcp:
        tcp[src].outgoing += frame.data
        #if frame.seq < tcp[src].seq:
        #  pass
        #  print "OUT OF ORDER PACKET! ZOMG PONIES!!!"
        #tcp[src].seq = frame.seq
        if not tcp[src].module:
          classify(tcp[src])
      else:
        tcp[src] = Connection(None, dst, src) 
        tcp[src].outgoing += frame.data
        classify(tcp[src])
    # incoming packet
    else:
      if dst in tcp:
        tcp[dst].incoming += frame.data
        tcp[dst].indict[frame.seq] = [frame.data, len(frame.data)]
        #if frame.seq < tcp[dst].seq:
        #  pass
        #  print "OUT OF ORDER PACKET! ZOMG PONIES!!!"
        #tcp[dst].seq = frame.seq
        if not tcp[dst].module:
          classify(tcp[dst])
      else:
        print "new connection from %s" % inet_ntoa(src[0])
        tcp[dst] = Connection(None, src, dst) 
        tcp[dst].incoming += frame.data
        tcp[dst].indict[frame.seq] = [frame.data, len(frame.data)]
        classify(tcp[dst])

    if pkt.src == own_ip:
      if tcp[src].module:
        tcp[src].module.handle(tcp[src])
    else:
      if tcp[dst].module:
        tcp[dst].module.handle(tcp[dst])

    # Annahme: irgendein Handler war passend TODO {{{
    # TODO wenn FIN kommt, tcp[src|dst] aufraeumen
    # Annahme2: alle Pakete sind schon da und in der richtigen Reihenfolge
    # Hier auch dann die Gegenrichtung verarbeiten, damit (HTTP)
    # Request+Response gemeinsam ausgewertet werden koennen }}}
             
    #payload.set_verdict(nfqueue.NF_ACCEPT)
    #sys.stdout.flush()
    return 1

def classify(connection):
  """ connection is a list [protocolhandler = None, data] """
  for protocol in protocols:
    if protocol.classify(connection):
      connection.module = protocol
      break

def print_connections():
  # TODO noch offene Verbindungen (i.e. len(data[1]) != 0) mit FIN,ACK
  # 'abschliessen'?
  for id, conn in tcp.items():
    #print "%s:%d, %s:%d len: %d" % (inet_ntoa(id[0]), id[1], inet_ntoa(conn.server[0]), conn.server[1], len('0')) 
    print "%s:%d" % (inet_ntoa(conn.server[0]), conn.server[1])
    for k,v in conn.indict.items():
      print "  seq: %s, data[%d]" % (k, v[1])

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
  #print_connections()
  q.unbind(AF_INET)
  q.close()
  print_stats()

def print_stats():
  for protocol in protocols:
    if [method for method in dir(protocol) if callable(getattr(protocol, method))].count('get_stats') == 1:
      print "\n STATISTICS for protocol %s\n" % protocol.protocols()[0]
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

