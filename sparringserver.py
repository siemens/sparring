import asynchat
import asyncore
import socket
#from pudb import set_trace; set_trace()

#class Tcphandler(asynchat.async_chat):
class Tcphandler(asyncore.dispatcher):

  def __init__(self, conn, sock=None, map=None):
      #asynchat.async_chat.__init__(self, sock, map)
      asyncore.dispatcher.__init__(self, sock, map)
      self.conn = conn

  def handle_read(self):
      data = self.recv(8192)
      if data:
        # echo halt...
        #print "sending back %s" % data
        #self.send(data)

        # we don't use conn.put_in() because there's no need for TCP 
        # connections to reassemble the data as our underlying socket did that
        # already for us. So just fill the incoming buffer
        self.conn.outgoing += data
        if self.conn.classify():
          self.conn.handle()
        #if self.conn.out_extra and 'buffer' in self.conn.out_extra and \
        #      self.conn.out_extra['buffer'] :
        #  sent = self.send(self.conn.out_extra['buffer'])
        #  self.conn.out_extra['buffer'] = self.conn.out_extra['buffer'][sent:]
  
  def writeable(self):
    return self.conn.out_extra and 'buffer' in self.conn.out_extra and len(self.conn.out_extra['buffer']) > 0

  def handle_write(self):
    if self.conn.out_extra and 'buffer' in self.conn.out_extra and \
          self.conn.out_extra['buffer'] :
      try:
        sent = self.send(self.conn.out_extra['buffer'])
        self.conn.out_extra['buffer'] = self.conn.out_extra['buffer'][sent:]
      except Exception, e:
        print "die exception macht mir gar nix...",
        print e

      if len(self.conn.out_extra['buffer']) != 0:
        pass
        #print "buffer not fully sent :|"
      else:
        #print "buffer fully sent :3"
        self.handle_close()
      # TODO let application/*.py:handle_{half,full} determine connection
      # close actions?
      #if not self.conn.out_extra['buffer']:
      #  self.handle_close()

  def handle_close(self):
    if self.conn.incoming or self.conn.outgoing:
      print " 3: not all data handled!"

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

  # TODO Teile eventuell nach handle_connect() auslagern, das erst spaeter im
  # Verbindungsaufbau (erfolg) greift?
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
      # TODO may raise exception, too, WTF :)
      remote = sock.getpeername()
      dst = (socket.inet_aton(remote[0]),remote[1]) 
      src = (socket.inet_aton(local[0]),local[1])
      conn = self.transport.newconnection(src, dst)
      handler = Tcphandler(conn, sock)

  def handle_error(self):
    print "ERROR aussen (Sparringserver)"
    raise

if __name__ == 'main':
  import tcp # TODO will break :-)
  server = Sparringserver('localhost', 5000, tcp)
  asyncore.loop()
