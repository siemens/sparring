#!/usr/bin/env python

from dpkt import ip
import dpkt
import sys, os, nfqueue
from socket import AF_INET, AF_INET6, inet_ntoa

count = 0
queueno = 0
protocols = []

# one of TRANSPARENT, HALF, FULL
mode = 'TRANSPARENT'

# key: connection identification (src, dst, sport, dport)
# data: connection details  [ protocolhandler = None, data ]
tcp_connections = {}

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

    tcp = pkt.data
    tuple = (pkt.src, pkt.dst, tcp.sport, tcp.dport)

    if tuple in tcp_connections:
      if tcp_connections[tuple][0] == None:
        protocol_classification(tcp_connections[tuple])
      # (possibly) append newly sent / received data
      tcp_connections[tuple][1] = tcp_connections[tuple][1] + tcp.data
    else:
      tcp_connections[tuple] = [None, tcp.data]
      protocol_classification(tcp_connections[tuple])

    # Annahme: irgendein Handler war passend TODO
    # Annahme2: alle Pakete sind schon da und in der richtigen Reihenfolge
    # Hier auch dann die Gegenrichtung verarbeiten, damit (HTTP) Request+Response
    # gemeinsam ausgewertet werden koennen
    if (tcp.flags & dpkt.tcp.TH_FIN) != 0 and tcp_connections[tuple][0]:
      #print "found FIN flag: %s->%s" % (inet_ntoa(pkt.src), inet_ntoa(pkt.dst))
      tcp_connections[tuple][0].handle(pkt, tcp_connections[tuple][1])
      del tcp_connections[tuple]  
              
    #print_status(payload, pkt)

    payload.set_verdict(nfqueue.NF_ACCEPT)
    sys.stdout.flush()
    return 1

def protocol_classification(connection):
  """ connection is a list [protocolhandler = None, data] """
  for protocol in protocols:
    if protocol.classify(connection[1]):
      connection[0] = protocol

def print_connections():
  for tuple, data in tcp_connections.items():
    print "%s:%d, %s:%d len: %d" % (inet_ntoa(tuple[0]), tuple[2], inet_ntoa(tuple[1]), tuple[3], len(data[1])) 

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
  q.set_queue_maxlen(50000)
  
  try:
      q.try_run()
  except KeyboardInterrupt, e:
      pass
      #print "interrupted"
  
  print "%d packets handled" % count
  print "Connection table"
  print_connections()

  for protocol in protocols:
    if [method for method in dir(protocol) if callable(getattr(protocol, method))].count('get_stats') == 1:
      print "INSERT STATS HERE"
    else:
      print "no stats available for protocol %s" % protocol.protocols()[0]
  q.unbind(AF_INET)
  q.close()

if __name__ == '__main__':
  #sys.path.append(os.path.realpath(__file__))

  print "sparring working in %s mode" % mode

  mod_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)),'modules')
  load_modules(mod_dir)

  print "Loaded modules ",
  for protocol in protocols:
    print protocol.protocols(),
  print 

  nfq_setup()


