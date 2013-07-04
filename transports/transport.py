from socket import inet_ntoa, AF_INET, SOL_IP
import asyncore, logging

class Transport():

  def __init__(self, mode, applications, own_ip):
    # key: connection identification for {UDP,TCP}/IP: (src, sport)
    # data: connection details Connection object
    self.connections = {}
    self.mode = mode
    self.applications = applications 
    self.own_ip = own_ip
    # Template for new connections
    self.connection = None
    # Template for new (server) handlers in half and full mode. It is expected 
    # to extend asyncore.dispatcher
    self.server = None
    # Template for type of socket to use for this transport
    self.socktype = None
    log = logging

  def items(self):
    return self.connections
   
  # TODO src UND dst koennen beide != own_ip (BCast) sein
  def newconnection(self, src, dst):
    """ conntype: connection template class for data handling
    src: client tuple (ip, port)
    dst: server tuple(ip, port) """
    # 0.0.0.0: UDP case where dst cannot - yet - be determined in full/half
    # mode due to python restrictions. see sparringserver.py for gory details
    if src[0] == self.own_ip or dst[0] == '0.0.0.0':
      self.connections[src] = self.connection(self, src, dst) 
      return self.connections[src]
    else:
      self.connections[dst] = self.connection(self, dst, src) 
      return self.connections[dst]

  def newserver(self, port, transport, map):
    return self.server(port, transport, map)

  def classify(self, connection):
    for application in self.applications:
      if application.classify(connection):
        connection.module = application
        return True
    return False

  def handle(self, pkt):
    if self.mode == 'TRANSPARENT':
      return self.handle_transparent(pkt)
    if self.mode == 'HALF':
      return self.handle_half(pkt)
    if self.mode == 'FULL':
      return self.handle_full(pkt)

class Sparringserver(asyncore.dispatcher):

  def __init__(self, port, transport, map=None):
    self.transport = transport
    asyncore.dispatcher.__init__(self, map=map)
    #self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
    self.create_socket(AF_INET, self.transport.socktype)
    self.set_reuse_addr()
    # #define IP_TRANSPARENT 19 from linux/in.h
    # was not backported from python3 to python2:
    # http://bugs.python.org/issue12809
    self.socket.setsockopt(SOL_IP, 19, 1)
    self.socket.setblocking(0)
    self.bind(('127.0.0.1', port))

  def handle_error(self):
    log.error("ERROR aussen (Sparringserver)")
    raise
