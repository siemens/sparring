import stats, urllib
import dnslib
from stats import Stats
from pudb import set_trace; set_trace()

def init(mode):
  return Dns(mode)

class Dnsstats(Stats):
  dummy = None
  def addquery(self, server, host, uri, file=None, original=None):
    self.addserver(server)
    if not self.cats.has_key('Files'):
      self.cats['Files'] = []
    if file:
      self.cats['Files'] += [file + ' original: ' + original]
    u = urlparse.urlparse('//' + host + uri, 'http')
    self.cats['Server'][server] += [ 'POST ' + u.geturl() ] 

class Dns():
  servers = {}

  def __init__(self, mode):
    # one of TRANSPARENT, FULL, HALF
    self.mode = mode
    self.stats = Dnsstats()
    #print '%s initialisiert [%s]' % (__name__,self.mode)

  def protocols(self):
    return ['dns']

  def classify(self, conn):
    ret = False

    if conn.outgoing:
      try:
        #dns = conn.outgoing.decode('hex')
        dns = conn.outgoing
        question = dnslib.DNSRecord.parse(dns)
        conn.outgoing = ''
        print "???"
        print question
        ret = True
      except:
        pass

    if conn.incoming:
      try:
        #dns = conn.incoming.decode('hex')
        dns = conn.incoming
        answer = dnslib.DNSRecord.parse(dns)
        conn.incoming = ''
        print "!!!"
        print answer
        ret = True
      except:
        pass

    return ret

  def get_stats(self):
    print self.stats

  def handle(self, conn):
    if self.mode == 'TRANSPARENT':
      return self.handle_transparent(conn)
    if self.mode == 'HALF':
      return self.handle_half(conn)
    if self.mode == 'FULL':
      return self.handle_full(conn)

  def handle_transparent(self, conn):
    while conn.outgoing:
        break

    while conn.incoming:
        break

  def handle_half(self, conn):
    pass

  def handle_full(self, conn):
    self.handle_transparent(conn)
    pass

