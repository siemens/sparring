#!/usr/bin/env python
import sys, os, nfqueue, dpkt
from dpkt import ip
from socket import AF_INET, AF_INET6, inet_ntoa, inet_aton, gethostbyname_ex, gethostname
#from pudb import set_trace; set_trace()

# local import below!

count = 0
nodata_count = 0
queueno = 0
protocols = []
modes = ['TRANSPARENT', 'HALF', 'FULL']

tcp = None
udp = None

def cb(payload):
    global count, nodata_count

    # TODO REMOVE
    payload.set_verdict(nfqueue.NF_STOP)

    count += 1

    data = payload.get_data()
    # spawn IP packet
    try:
      pkt = ip.IP(data)
    except:
      print "unsupported Layer 3 protocol (not IP) dropped"
      payload.set_verdict(nfqueue.NF_DROP)
      return

    # TODO XXX  return-Wert nur das VERDICT, wir wollen aber auch, falls
    # noetig, set_verdict_modified() aufrufen koennen. Meer returnen oder
    # payload uebergeben und die Funktion selber VERDICT setzen lassen?
    if pkt.p == dpkt.ip.IP_PROTO_TCP:
      ret = tcp.handle(pkt)
      payload.set_verdict(ret[1])
      nodata_count += ret[0]
    elif pkt.p == dpkt.ip.IP_PROTO_UDP:
      ret = udp.handle(pkt)
      payload.set_verdict(ret[1])
      nodata_count += ret[0]
    elif pkt.p == dpkt.ip.IP_PROTO_ICMP:
      frame = pkt.data
      if frame.type == dpkt.icmp.ICMP_ECHO:
        print "ICMP ECHO %s" % inet_ntoa(pkt.dst)
        return
      elif frame.type == dpkt.icmp.ICMP_ECHOREPLY:
        print "ICMP REPLY from %s" % inet_ntoa(pkt.src)
        return
      #if frame.type >= dpkt.icmp.ICMP_UNREACH and \
      #   frame.type <= dpkt.icmp.ICMP_UNREACH_PRECEDENCE_CUTOFF:
      #  return
      else:
        return
    else:
      print "unsupported protocol %s recieved" % pkt.p
      return
#    if pkt.src == own_ip: {{{
#      if tcp[src].module:
#        tcp[src].handle()
#    else:
#      if tcp[dst].module:
#        tcp[dst].handle()

# Annahme: irgendein Handler war passend TODO }}}
             
def print_connections():
  # TODO noch offene Verbindungen (i.e. len(data[1]) != 0) mit FIN,ACK
  # 'abschliessen'? -> NICHT im transparenten Modus
  for id, conn in tcp.items():
    #print "  inheap lang: %d incoming: %d" % (len(conn.inheap),len(conn.incoming))
    #print "  last ACKed : %d max seq: %d     " % (conn.inseq, conn.inseq_max)
    print "Details for %s:%d" % (inet_ntoa(conn.server[0]), conn.server[1])
    if conn.inseq < conn.inseq_max:
      print "  WARNING un-ACK-ed data in buffer"

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
      print "\n STATISTICS for protocol %s" % protocol.protocols()[0]
      protocol.get_stats()
    else:
      print "no stats available for protocol %s" % protocol.protocols()[0]

if __name__ == '__main__':
  mode = modes[0]
  print "sparring working in %s mode" % mode
  global own_ip
  # TODO funktioniert nicht immer
  # eigentlich eine Liste (inkl. Broadcastadresse)
  own_ip = inet_aton('172.16.0.7') #inet_aton(gethostbyname_ex(gethostname())[2][0])
  own_ip = inet_aton('192.168.0.100') #inet_aton(gethostbyname_ex(gethostname())[2][0])
  print "using %s as own IP address" % inet_ntoa(own_ip)

  sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)),'lib'))
  sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)),'protocols'))

  mod_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)),'modules')
  load_modules(mod_dir)

  print "Loaded modules ",
  for protocol in protocols:
    print protocol.protocols(),
  print 

  import tcp, udp
  tcp = tcp.Tcp(mode, protocols, own_ip)
  udp = udp.Udp(mode, protocols, own_ip)

  nfq_setup()

