#!/usr/bin/env python

# Copyright (c) Siemens AG, 2013
#
# This file is part of sparring.  sparring is free software: you can
# redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation; either version 2
# of the License, or(at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#

import sys, os, nfqueue, dpkt, user, signal
from socket import AF_INET, AF_INET6, inet_ntoa, inet_aton, gethostbyname_ex, gethostname, socket
from time import sleep
import getopt
import socket
import logging
import transports.tcp as tcp
import transports.udp as udp
#from dpkt import ip
# import patched dpkt ip class
from utils.ip_patched import ip
#from pudb import set_trace; set_trace()
# local imports below!

MODES = ['TRANSPARENT', 'HALF', 'FULL']

def handle_term(arg1, arg2):
  pass
  

class Sparring(object):
  def __init__(self, mode, myip, port = 5001, queueno = 0):
    self.count = 0
    self.nodata_count = 0
    self.applications = []
    self.tcp = None
    self.udp = None
    log = logging

    self.tcp = tcp.Tcp(mode, self.applications, myip)
    self.udp = udp.Udp(mode, self.applications, myip)
  
    self.app_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)),'applications')
    self.load_applications(self.app_dir, mode)

    if __name__ == '__main__':
      modules = "loaded modules:"
      for application in self.applications:
        modules = modules + ' ' + str(application.protocols())
  
    log.info(modules)
    self.setup(mode, myip, port, queueno)
  
  
  def cb(self, payload):
      self.count += 1
  
      data = payload.get_data()
      # spawn IP packet
      try:
        pkt = ip.IP(data)
      except Exception, e:
        log.warning("unsupported Layer 3 protocol or broken IP packet dropped: %s" % e)
        payload.set_verdict(nfqueue.NF_DROP)
        return
  
      if pkt.p == dpkt.ip.IP_PROTO_TCP:
        ret = self.tcp.handle(pkt)
        payload.set_verdict(ret[1])
        self.nodata_count += ret[0]
      elif pkt.p == dpkt.ip.IP_PROTO_UDP:
        ret = self.udp.handle(pkt)
        payload.set_verdict(ret[1])
        self.nodata_count += ret[0]
      elif pkt.p == dpkt.ip.IP_PROTO_ICMP:
        frame = pkt.data
        if frame.type == dpkt.icmp.ICMP_ECHO:
          log.info("ICMP ECHO %s" % inet_ntoa(pkt.dst))
          return
        elif frame.type == dpkt.icmp.ICMP_ECHOREPLY:
          log.info("ICMP REPLY from %s" % inet_ntoa(pkt.src))
          return
        else:
          return
      else:
        log.warning("unsupported protocol %s recieved (ignored)" % pkt.p)
        return
               
  def print_connections(self):
    # TODO noch offene Verbindungen (i.e. len(data[1]) != 0) mit FIN,ACK
    # 'abschliessen'? -> NICHT im transparenten Modus
    for id, conn in self.tcp.connections.items() + self.udp.connections.items():
      #print "  inheap lang: %d incoming: %d" % (len(conn.inheap),len(conn.incoming))
      #print "  last ACKed : %d max seq: %d     " % (conn.inseq, conn.inseq_max)
      log.info("%s:%d" % (inet_ntoa(conn.remote[0]), conn.remote[1]))
      #if conn.inseq < conn.inseq_max:
      #  print "  WARNING un-ACK-ed data in buffer"
  
  def nfq_setup(self, queueno):
    q = nfqueue.queue()
    q.set_callback(self.cb)
    try:
      q.fast_open(queueno, AF_INET)
    except RuntimeError, e:
      log.error("cannot bind to nf_queue %d: %s. Already in use or not root?" % (queueno, e))
      return False
    q.set_queue_maxlen(5000)
       
    # won't work as try_run() still requires CAP_? ...
    #user.os.setuid(100)

    try:
      q.try_run()
    except KeyboardInterrupt, e:
        pass
  
    q.unbind(AF_INET)
    q.close()
    return True
  
  def print_stats(self):
    for application in self.applications:
      if [method for method in dir(application) if callable(getattr(application, method))].count('get_stats') == 1:
        print("\n STATISTICS for protocol %s" % application.protocols()[0])
        #print application.get_stats()
        if application.protos == ['dns']:
          #application.stats.log_response('pooh', 'what the?')
          pass
        print(application.stats)
      else:
        log.warning("no stats available for protocol %s" % application.protocols()[0])
  
  def identify_generic(self):
    sys.path.append(self.app_dir)
    try:
      mod = __import__('generic')
      mod_instance = mod.init(mode)
      self.applications.append(mod_instance)
    except Exception, e:
      log.error("import of generic module failed: %s" % e)
      return
  
    #print "davor:"
    #for connection in tcp.connections.values() + udp.connections.values():
    #  try:
    #    print "(%s,%d)->(%s,%d) %s" % (inet_ntoa(connection.remote[0]),
    #        connection.remote[1], inet_ntoa(connection.local[0]),
    #        connection.local[1], connection.module.stats)
    #  except:
    #    print "one with NoneType"
  
    for connection in self.tcp.connections.values() + self.udp.connections.values():
      if not connection.module:
        connection.module = mod_instance
        connection.handle()
  
    #print "danach:"
    #for connection in tcp.connections.values() + udp.connections.values():
    #  print "%s %s" % (inet_ntoa(connection.remote[0]), connection.module)
  
  def load_applications(self, app_dir, mode):
    sys.path.append(app_dir)
    mod_list = os.listdir(app_dir)
    blacklist = ['application', 'generic', '__init__']
  
    for module in mod_list:
      try:
        module_name, module_ext = os.path.splitext(module)
        # better? check for existance and callable() of init() 
        if module_ext == '.py' and not module_name in blacklist:
          mod = __import__(module_name)
          self.applications.append(mod.init(mode))
          del mod
      except ImportError, e:
        log.error("import of module %s failed: %s" % (module, e))
  
  def setup(self, mode, ip, port, queueno = 0):
    if mode == MODES[0]:
      if not self.nfq_setup(queueno):
        return
    else:
      self.create_listener(ip, port)
    self.shutdown()
  
  def create_listener(self, ip, port):
    import asyncore
    servers = {}
    server1 = self.tcp.newserver(port, self.tcp, servers)
    server2 = self.udp.newserver(port, self.udp, servers)
    try:
      asyncore.loop(1, True, servers) 
    except KeyboardInterrupt, e:
      pass
    except asyncore.ExitNow, e:
      pass
    
  def shutdown(self):
    log.info("\n%d packets handled (%d without data)" % (self.count, self.nodata_count))
    if log.getLogger().level <= log.DEBUG:
      print "Connection table"
      print_connections()
  
    # gather generic stats about unknown connections
    self.identify_generic()
    self.print_stats()


def usage():
  print "usage: sparring.py -a ipaddress [-n queuenum] [mode] [-p portnum]"
  print "-a ipaddress: specify own IPv4 address"
  print "-n queuenuno: use given nfqueue-number instead of the default (0)"
  print "       modes:"
  print "              -t run in TRANSPARENT mode (default)"
  print "              -h run in HALF        mode"
  print "              -f run in FULL        mode"
  print "-p portno   : half/full mode: listen locally on port portno (default: 5000)"
  print "-v verbose  : emit info messages during simulation"

if __name__ == '__main__':
  myip = None
  modeopt = 0
  port = 5000
  queueno = 0
  verbose = False

  try:                                
    opts, args = getopt.getopt(sys.argv[1:], "thfa:n:p:v")
    for opt in opts:
      if opt[0] == "-a":
        myip = inet_aton(opt[1])
      if opt[0] == "-f":
        modeopt = 2
      elif opt[0] == "-h":
        modeopt = 1
      elif opt[0] == "-n":
        queueno = int(opt[1])
      elif opt[0] == "-p":
        port = opt[1]
        port = int(port)
      elif opt[0] == "-v":
        verbose = True
      else:
        modeopt = 0
  except: #getopt.GetoptError, ValueError:           
    usage()                          
    sys.exit(2)           
  if not myip:
    usage()
    sys.exit(2)

  signal.signal(signal.SIGTERM, handle_term)
  mode = MODES[modeopt]

  log = logging
  log.getLogger().setLevel(logging.INFO if verbose else logging.WARNING)

  log.info("""                     _
   _________  ____ ___________(_)___  ____ _
  / ___/ __ \/ __ `/ ___/ ___/ / __ \/ __ `/
 (__  ) /_/ / /_/ / /  / /  / / / / / /_/ / 
/____/ .___/\__,_/_/  /_/  /_/_/ /_/\__, /  
    /_/                            /____/   
""")

  log.info("mode: %s" % mode)
  # TODO funktioniert nicht immer
  # eigentlich eine Liste (inkl. Broadcastadresse)
  #myip = inet_aton('172.16.0.7') #inet_aton(gethostbyname_ex(gethostname())[2][0])
  #myip = inet_aton('192.168.1.127') #inet_aton(gethostbyname_ex(gethostname())[2][0])
  log.info("own IP address: %s" % inet_ntoa(myip))
  s = Sparring(mode, myip, port, queueno)

