from socket import inet_ntoa
class Protocol():

  def __init__(self, mode, applications, own_ip):
    self.mode = mode
    self.applications = applications 
    self.own_ip = own_ip
   
  def newconnection(self, l3, conntype, src, dst):
    """ l3 layer3-dict to use (tcp/udp/..)
    conntype: connection instance for data handling
    src: client tuple (ip, port)
    dst: server tuple(ip, port) """
    if src[0] == self.own_ip:
      l3[src] = conntype(None, src, dst) 
    else:
      l3[dst] = conntype(None, dst, src) 

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
