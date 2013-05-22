from dnslib import *
from stats import Stats
from application import Application

def init(mode):
  return Dns(mode)

class Dnsstats(Stats):
  dummy = None
  def log_query(self, server, q):
    self.log_server(server)
    self.cats['Server'][server] += [ 'Q: ' + str(q) ] 
  def log_response(self, server, a):
    self.log_server(server)
    self.cats['Server'][server] += [ 'A: ', a ] 

class Dns(Application):
  servers = {}

  def __init__(self, mode):
    # one of TRANSPARENT, FULL, HALF
    Application.__init__(self, mode)
    self.stats = Dnsstats()
    self.protos = ['dns']
    #print '%s initialisiert [%s]' % (__name__,self.mode)

  def setup(self, conn):
    conn.in_extra = {}

  def classify(self, conn):
    ret = False

    # will throw exception if data is not assigned to another variable *SIGH*
    if conn.outgoing:
      dns = conn.outgoing.getvalue()
      try:
        question = DNSRecord.parse(dns)
        ret = True
      except:
        pass

    if conn.incoming and not ret:
      dns = conn.incoming.getvalue()
      try:
        answer = DNSRecord.parse(conn.incoming)
        ret = True
      except:
        pass

    if ret:
      self.setup(conn)
    return ret

  def handle(self, conn):
    if self.mode == 'TRANSPARENT':
      return self.handle_transparent(conn)
    if self.mode == 'HALF':
      return self.handle_half(conn)
    if self.mode == 'FULL':
      return self.handle_full(conn)

  def handle_transparent(self, conn):
    question = None
    answer = None

    dns = conn.outgoing.getvalue() 
    while dns:
      try:
        #conn.outgoing.truncate(0)
        question = DNSRecord.parse(dns)
        self.stats.log_query(conn.remote, question.get_q())
        conn.outgoing.truncate(0)
        dns = ''
      except Exception, e:
        print 'xx',str(e)
        break

    dns = conn.incoming.getvalue()
    while dns:
      try:
        #conn.incoming.truncate(0)
        answer = DNSRecord.parse(dns)
        rlist = []
        for x in answer.rr:
          if x.rtype == 32:
            rlist.append('NB' + " " + str(x.rname) + " " + str(x.rdata))
          else:
            rlist.append(QTYPE.lookup(x.rtype) + " " + str(x.rname) + " " + str(x.rdata))
        self.stats.log_response(conn.remote, rlist)
        conn.incoming.truncate(0)
        dns = ''
      except KeyError:
        print 'Unsupported DNS record type encountered. Raw data:'
        print 'Connection: %s' % conn
        print answer
        break
      except Exception, e:
        print 'Exception for incoming DNS:\n',e
        break

    return (question, answer)    

  def handle_half(self, conn):
    # general outline:
    # receive request
    question, answer = self.handle_transparent(conn)
    assert(not answer)
    if question:
      print question.send(conn.remote[0])

    conn.in_extra['close'] = True
    # spawn new request, send
    # receive answer
    # pass result
    pass

  def handle_full(self, conn):
    # receive request
    # spawn new artifical result
    # pass result
    question, answer = self.handle_transparent(conn)
    if question:
      a = question.reply(data="1.2.3.4")
      conn.in_extra['buffer'] = a.pack()
    pass

