#!/usr/bin/env python
import sys, os, nfqueue, dpkt
from dpkt import ip
from socket import AF_INET, AF_INET6, inet_ntoa, inet_aton, gethostbyname_ex, gethostname, socket
from time import sleep
import getopt
import socket
#from pudb import set_trace; set_trace()

# local imports below!

count = 0
nodata_count = 0
queueno = 0
applications = []
modes = ['TRANSPARENT', 'HALF', 'FULL']

tcp = None
udp = None

def cb(payload):
    global count, nodata_count
    count += 1

    data = payload.get_data()
    # spawn IP packet
    try:
      pkt = ip.IP(data)
    except:
      print "unsupported Layer 3 protocol or broken IP packet dropped"
      payload.set_verdict(nfqueue.NF_DROP)
      return

    # TODO eigentlich besser: neue Model-Klasse, die die Unterscheidung
    # vornimmt. Hier ist ja nur Controller-Teil.
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
  for id, conn in tcp.connections.items() + udp.connections.items():
    #print "  inheap lang: %d incoming: %d" % (len(conn.inheap),len(conn.incoming))
    #print "  last ACKed : %d max seq: %d     " % (conn.inseq, conn.inseq_max)
    print "%s:%d" % (inet_ntoa(conn.remote[0]), conn.remote[1])
    #if conn.inseq < conn.inseq_max:
    #  print "  WARNING un-ACK-ed data in buffer"

def load_applications(app_dir):
  sys.path.append(app_dir)
  mod_list = os.listdir(app_dir)
  blacklist = ['application', 'generic']

  for module in mod_list:
    try:
      module_name, module_ext = os.path.splitext(module)
      # better? check for existance and callable() of init() 
      if module_ext == '.py' and not module_name in blacklist:
        mod = __import__(module_name)
        applications.append(mod.init(mode))
        del mod
    except ImportError, e:
      print "import of module %s failed: %s" % (module, e)

def nfq_setup():
  q = nfqueue.queue()
  q.set_callback(cb)
  try:
    q.fast_open(queueno, AF_INET)
  except RuntimeError, e:
    print "cannot bind to nf_queue %d. Already in use?" % queueno
  q.set_queue_maxlen(5000)
  
  try:
    q.try_run()
  except KeyboardInterrupt, e:
      pass

  q.unbind(AF_INET)
  q.close()

def print_stats():
  for application in applications:
    if [method for method in dir(application) if callable(getattr(application, method))].count('get_stats') == 1:
      print "\n STATISTICS for protocol %s" % application.protocols()[0]
      application.get_stats()
    else:
      print "no stats available for protocol %s" % application.protocols()[0]

def identify_generic():
  sys.path.append(app_dir)
  try:
    mod = __import__('generic')
    mod_instance = mod.init(mode)
    applications.append(mod_instance)
  except e:
    print "import of generic module failed"
    return

  #print "davor:"
  #for connection in tcp.connections.values() + udp.connections.values():
  #  try:
  #    print "(%s,%d)->(%s,%d) %s" % (inet_ntoa(connection.remote[0]),
  #        connection.remote[1], inet_ntoa(connection.local[0]),
  #        connection.local[1], connection.module.stats)
  #  except:
  #    print "one with NoneType"

  for connection in tcp.connections.values() + udp.connections.values():
    if not connection.module:
      connection.module = mod_instance
      connection.handle()

  #print "danach:"
  #for connection in tcp.connections.values() + udp.connections.values():
  #  print "%s %s" % (inet_ntoa(connection.remote[0]), connection.module)

def load_applications(app_dir):
  sys.path.append(app_dir)
  mod_list = os.listdir(app_dir)
  blacklist = ['application', 'generic']

  for module in mod_list:
    try:
      module_name, module_ext = os.path.splitext(module)
      # better? check for existance and callable() of init() 
      if module_ext == '.py' and not module_name in blacklist:
        mod = __import__(module_name)
        applications.append(mod.init(mode))
        del mod
    except ImportError, e:
      print "import of module %s failed: %s" % (module, e)

def setup(mode):
  if mode == 'TRANSPARENT':
    nfq_setup()
  else:
    create_listener()
  shutdown()

def create_listener():
  from sparringserver import Sparringserver 
  import asyncore
  server1 = Sparringserver(own_ip, 5000, tcp)
  #server2 = Sparringserver(own_ip, 5000, udp)
  try:
    while True:
      asyncore.loop(timeout=1, use_poll=True, count=1)
      sleep(.0009)
  except KeyboardInterrupt, e:
    pass
  
def shutdown():
  print "\n%d packets handled (%d without data)" % (count, nodata_count)
  #print "Connection table"
  #print_connections()

  # gather generic stats about unknown connections
  identify_generic()
  print_stats()

def usage():
  print "usage: sparring.py [mode]"
  print "modes:"
  print "            -t run in TRANSPARENT mode"
  print "            -h run in HALF        mode"
  print "            -f run in FULL        mode"

if __name__ == '__main__':
  modeopt = 0
  try:                                
    opts, args = getopt.getopt(sys.argv[1:], "thf") 
    for opt in opts:
      if opt[0][1] == 'f':
        modeopt = 2
      elif opt[0][1] == 'h':
        modeopt = 1
      else:
        modeopt = 0
  except: #getopt.GetoptError, ValueError:           
    usage()                          
    sys.exit(2)           

  mode = modes[modeopt]
  print "sparring working in %s mode" % mode
  global own_ip
  # TODO funktioniert nicht immer
  # eigentlich eine Liste (inkl. Broadcastadresse)
  #own_ip = inet_aton('172.16.0.7') #inet_aton(gethostbyname_ex(gethostname())[2][0])
  own_ip = inet_aton('192.168.1.134') #inet_aton(gethostbyname_ex(gethostname())[2][0])
  print "using %s as own IP address" % inet_ntoa(own_ip)

  cwd = os.path.dirname(os.path.realpath(__file__))
  sys.path.append(os.path.join(cwd, 'lib'))
  sys.path.append(os.path.join(cwd, 'transports'))
  # helper classes for applications/*.py
  sys.path.append(os.path.join(cwd, 'utils'))

  import tcp, udp
  tcp = tcp.Tcp(mode, applications, own_ip)
  udp = udp.Udp(mode, applications, own_ip)

  global app_dir
  app_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)),'applications')
  load_applications(app_dir)

  print "Loaded modules ",
  for application in applications:
    print application.protocols(),
  print 

  setup(mode)
