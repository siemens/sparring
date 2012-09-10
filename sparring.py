#!/usr/bin/env python
from dpkt import ip
import dpkt
import sys, os, nfqueue 
from socket import AF_INET, AF_INET6, inet_ntoa, inet_aton, gethostbyname_ex, gethostname
from connection import Tcpconnection, Connection

#from pudb import set_trace; set_trace()

count = 0
nodata_count = 0
queueno = 0
protocols = []
modes = ['TRANSPARENT', 'HALF', 'FULL']

# key: connection identification (src, sport)
# data: connection details Connection object
tcp = {}
udp = {}

def cb(payload):
    # TODO REMOVE
    payload.set_verdict(nfqueue.NF_STOP)

    global count
    count += 1

    data = payload.get_data()
    # spawn IP packet
    try:
      pkt = ip.IP(data)
    except:
      print "unsupported Layer 3 protocol (not IP) dropped"
      payload.set_verdict(nfqueue.NF_DROP)

    # TODO XXX  return-Wert nur das VERDICT, wir wollen aber auch, falls
    # noetig, set_verdict_modified() aufrufen koennen. Meer returnen oder
    # payload uebergeben und die Funktion selber VERDICT setzen lassen?
    if pkt.p == dpkt.ip.IP_PROTO_TCP:
      payload.set_verdict(handle_tcp(pkt))
    elif pkt.p == dpkt.ip.IP_PROTO_UDP:
      payload.set_verdict(handle_udp(pkt))
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

def handle_udp(pkt):
  datagram = pkt.data
  src = (pkt.src, datagram.sport)
  dst = (pkt.dst, datagram.dport)

  # outgoing packet
  if pkt.src == own_ip:
    if not src in udp:
      newconnection(udp, Connection, src, dst)

    udp[src].put_out(datagram.data)

    if not udp[src].module:
      classify(udp[src])
    if udp[src].module:
      udp[src].handle()

  # incoming packet
  else:
    if not dst in udp:
      newconnection(udp, Connection, dst, src)


    # TODO handle
    try:
      udp[dst].put_in(datagram.data)
      if not udp[dst].module:
        classify(udp[dst])
      if udp[dst].module:
        udp[dst].handle()
    except:
      print "%s:%d -> %s:%d" % (inet_ntoa(src[0]), src[1], inet_ntoa(dst[0]), dst[1])

  return nfqueue.NF_STOP

def handle_tcp(pkt):
    # TODO check needed that no unsolicited SYN package
    # from outside pollutes the tcp dictionary?

    segment = pkt.data
    src = (pkt.src, segment.sport)
    dst = (pkt.dst, segment.dport)

    # TODO wenn FIN kommt, tcp[src|dst] aufraeumen (leeren/letzes handle())
    if len(segment.data) == 0:
      if (segment.flags & dpkt.tcp.TH_ACK) != 0:
        # outgoing packet
        if pkt.src == own_ip:
          if not src in tcp:
            newconnection(tcp, Tcpconnection, src, dst)
          tcp[src].inseq = segment.ack
          tcp[src].assemble_in()
          if not tcp[src].module:
            classify(tcp[src])
          if tcp[src].module:
            tcp[src].handle()
        # incoming packet
        elif dst in tcp:
          if not dst in tcp:
            newconnection(tcp, Tcpconnection, dst, src)
          tcp[dst].outseq = segment.ack
          tcp[dst].assemble_out()
          if not tcp[dst].module:
            classify(tcp[dst])
          if tcp[dst].module:
            tcp[dst].handle()

      global nodata_count
      nodata_count += 1

      return nfqueue.NF_STOP

    # outgoing packet
    if pkt.src == own_ip:
      if src in tcp:
        if segment.seq >= tcp[src].outseq_max:
          tcp[src].outseq_max = segment.seq
      else:
        newconnection(tcp, Tcpconnection, src, dst)

      tcp[src].put_out((segment.seq, segment.data))

      if not tcp[src].module:
        classify(tcp[src])
      if tcp[src].module:
        tcp[src].handle()

    # incoming packet
    else:
      if dst in tcp:
        if segment.seq >= tcp[dst].inseq_max:
          tcp[dst].inseq_max = segment.seq
      else:
        newconnection(tcp, Tcpconnection, dst, src)

      tcp[dst].put_in((segment.seq, segment.data))

      if not tcp[dst].module:
        classify(tcp[dst])
      if tcp[dst].module:
        tcp[dst].handle()

    return nfqueue.NF_STOP
#    if pkt.src == own_ip: {{{
#      if tcp[src].module:
#        tcp[src].handle()
#    else:
#      if tcp[dst].module:
#        tcp[dst].handle()

# Annahme: irgendein Handler war passend TODO }}}
             

def newconnection(l3, conntype, src, dst):
  """ l3 layer3-dict to use (tcp/udp/..)
  conntype: connection instance for data handling
  src: client tuple (ip, port)
  dst: server tuple(ip, port) """
  if src[0] == own_ip:
    l3[src] = conntype(None, src, dst) 
  else:
    l3[dst] = conntype(None, dst, src) 

def classify(connection):
  for protocol in protocols:
    if protocol.classify(connection):
      connection.module = protocol
      return True
  return False

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
  print_connections()
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
  print "using %s as own IP address" % inet_ntoa(own_ip)

  sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)),'lib'))

  mod_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)),'modules')

  load_modules(mod_dir)

  print "Loaded modules ",
  for protocol in protocols:
    print protocol.protocols(),
  print 

  nfq_setup()

