import asynchat
import asyncore
import socket
#from pudb import set_trace; set_trace()

class Tcphandler(asynchat.async_chat):

  def __init__(self, conn, sock=None, map=None):
      asynchat.async_chat.__init__(self, sock, map)
      self.conn = conn

  def handle_read(self):
      data = self.recv(8192)
      if data:
        # echo halt...
        #print "sending back %s" % data
        #self.send(data)

        # we don't use conn.put_in() because for TCP connections there's no
        # need to reassemble the data as our underlying socket did that
        # already for us. So just fill the incoming buffer
        self.conn.outgoing += data
        if self.conn.classify():
          self.conn.handle()

  def handle_write(self):
    pass
    # TODO buffering a la man page?
    #if self.conn.outgoing:
    #  self.send(conn.outgoing)

  def handle_close(self):
    if self.conn.incoming or self.conn.outgoing:
      print "not all data handled!"

    del self.conn # TODO aus oberer instanz loeschen?
    self.close()

class Udphandler(asynchat.async_chat):
  def handle_read(self):
      data = self.recv(8192)
      if data:
          self.send(data)

class Sparringserver(asyncore.dispatcher):

  def __init__(self, host, port, transport):
    self.transport = transport
    asyncore.dispatcher.__init__(self)
    self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
    self.set_reuse_addr()
    # #define IP_TRANSPARENT 19 from linux/in.h
    # was not backported from python3 to python2:
    # http://bugs.python.org/issue12809
    self.socket.setsockopt(socket.SOL_IP, 19, 1)
    self.bind(('', port))
    self.listen(5)

  def handle_accept(self):
    pair = self.accept()
    if pair is None:
      pass
    else:
      sock, addr = pair
      # addr == client == sock.getpeername() == addr
      # sock.getsockname() == us
      # TODO noch nicht ganz richtig ;)
      local = sock.getsockname()
      remote = sock.getpeername()
      src = (socket.inet_aton(remote[0]),remote[1]) 
      dst = (socket.inet_aton(local[0]),local[1])
      conn = self.transport.newconnection(src, dst)
      handler = Tcphandler(conn, sock)

if __name__ == 'main':
  import tcp # TODO will break :-)
  server = Sparringserver('localhost', 5000, tcp)
  asyncore.loop()
