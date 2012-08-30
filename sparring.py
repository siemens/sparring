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
# data: connection details Connection 
tcp = {}

class Connection():
  def __init__(self, module, (dst, dport), (src, sport)):
    self.module = module
    self.outgoing = ''
    self.incoming = ''
    self.server = (dst, dport)
    self.client = (src, sport)
    self.proxy = None

def cb(payload):
    # TODO REMOVE
    payload.set_verdict(nfqueue.NF_ACCEPT)

    global count
    count += 1

    data = payload.get_data()
    # spawn IP packet
    pkt = ip.IP(data)

    # TCP only, for now.
    if pkt.p != dpkt.ip.IP_PROTO_TCP:
      return 1

    # TODO check needed that no unsolicited SYN package
    # from outside pollutes the tcp dictionary?

    tcp_frame = pkt.data

    # for now. TODO
    if len(tcp_frame.data) == 0:
      global nodata_count
      nodata_count += 1
      return 1

    src = (pkt.src, tcp_frame.sport)
    dst = (pkt.dst, tcp_frame.dport)

    # outgoing packet
    if pkt.src == inet_aton(own_ip):
      if src in tcp:
        tcp[src].outgoing += tcp_frame.data
        if not tcp[src].module:
          classify(tcp[src])
      else:
        tcp[src] = Connection(None, dst, src) 
        tcp[src].outgoing += tcp_frame.data
        classify(tcp[src])
    # incoming packet
    else:
      if dst in tcp:
        tcp[dst].incoming += tcp_frame.data
        if not tcp[dst].module:
          classify(tcp[dst])
      else:
        tcp[dst] = Connection(None, src, dst) 
        tcp[dst].incoming += tcp_frame.data
        classify(tcp[dst])

    if pkt.src == inet_aton(own_ip):
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
    print "%s:%d, %s:%d len: %d" % (inet_ntoa(id[0]), id[1], inet_ntoa(conn.server[0]), conn.server[1], len('0')) 

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
  own_ip = '192.168.1.149' #gethostbyname_ex(gethostname())[2][0]
  print "using %s as own IP address" % own_ip

  sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)),'lib'))

  mod_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)),'modules')

  load_modules(mod_dir)

  print "Loaded modules ",
  for protocol in protocols:
    print protocol.protocols(),
  print 

  nfq_setup()

