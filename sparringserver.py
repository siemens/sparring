import asyncore, asynchat
import socket
from time import sleep
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
        # already for us. So just fill the outgoing buffer
        self.conn.outgoing.write(data)
        if self.conn.classify():
          self.conn.handle()
        if self.writable():
          self.handle_write()
  
  def writable(self):
    self.conn.handle()
    return True
    #print "was geht raus?"
    return self.conn.in_extra and 'buffer' in self.conn.in_extra and self.conn.in_extra['buffer']

  def readable(self):
    return True

  def handle_write(self):
    try:
      #self.conn.handle()
      sent = self.send(self.conn.in_extra['buffer'])
      #print "sendt to client: %s" % self.conn.in_extra['buffer'][:sent]
      self.conn.in_extra['buffer'] = self.conn.in_extra['buffer'][sent:]
    except Exception, e:
      # TODO ja doch macht schon was : )
      #print "handle_write() ",
      #print e
      return

    # application has no work left and all data was sent
    if self.conn.in_extra['close'] and not self.conn.in_extra['buffer']:
      self.handle_close()

  def handle_close(self):
    """ seems get called multiple times for the same connection, so pay
    attention wether self.conn still is set or not """
    # TODO klappt so nicht. Wieso denn nicht?
    if not self.conn:
      self.close()
      return

    if self.conn.incoming.getvalue() or self.conn.outgoing.getvalue():
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
      # socket.error: [Errno 107] Transport endpoint is not connected
      try:
        remote = sock.getpeername()
        dst = (socket.inet_aton(remote[0]),remote[1]) 
        src = (socket.inet_aton(local[0]),local[1])
        conn = self.transport.newconnection(src, dst)
        handler = Tcphandler(conn, sock)
      except Exception, e:
        print "handle_accept() ",
        print e

  def handle_error(self):
    print "ERROR aussen (Sparringserver)"
    raise

if __name__ == 'main':
  import tcp # TODO will break :-)
  server = Sparringserver('localhost', 5000, tcp)
  while True:
    asyncore.loop(timeout=1, use_poll=True, count=1)
    sleep(.0001)
