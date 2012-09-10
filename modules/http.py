import stats
import urlparse
import webob
from socket import inet_ntoa
#from pudb import set_trace; set_trace()

def init(mode):
  return Http(mode)

class Httpstats(stats.Stats):
  def setproxy(self, server, proxy): 
    self.addserver(server)
    self.cats['Server'][server][0] = proxy

  def addget(self, server, host, uri):
    self.addserver(server)
    # TODO: http vs. https!
    u = urlparse.urlparse('//' + host + uri, 'http')
    self.cats['Server'][server] += [ 'GET ' + u.geturl() ]
  
  def addpost(self, server, host, uri, file=None, original=None):
    self.addserver(server)
    if not self.cats.has_key('Files'):
      self.cats['Files'] = []
    if file:
      self.cats['Files'] += [file + ' original: ' + original ]
    u = urlparse.urlparse('//' + host + uri, 'http')
    self.cats['Server'][server] += [ 'POST ' + u.geturl() ] 

class Http():
  stats = Httpstats()
  servers = {}

  def __init__(self, mode):
    # one of TRANSPARENT, FULL, HALF
    self.mode = mode
    #print '%s initialisiert [%s]' % (__name__,self.mode)

  def protocols(self):
    return ['http']

  def classify(self, conn):
    return (conn.incoming.split('\n', 1)[0].startswith('HTTP/') or conn.outgoing.split('\n', 1)[0][-9:][:5] == 'HTTP/')

  def get_stats(self):
    print self.stats
    #for server, details in self.servers.items():
    #  print "%15.15s:%-4d    via PROXY: %r" % (inet_ntoa(server[0]), server[1], details)

  def handle(self, conn):
    if self.mode == 'TRANSPARENT':
      return self.handle_transparent(conn)
    if self.mode == 'HALF':
      return self.handle_half(conn)
    if self.mode == 'FULL':
      return self.handle_full(conn)

  def handle_transparent(self, conn):
    # be careful to count the connection for http://server,
    # not the proxy server (conn.server)!
    # TODO ACHTUNG es kann zu einem Proxy/Server immer mehrere Verbindungen
    # durch unterschiedliche (lokale) Ports geben, diese koennen auch
    # ueberlappen, ist das in den Statistiken ein Problem?
    server = conn.proxy if conn.proxy else conn.server

    while conn.outgoing:
      try:
        http = webob.Request.from_bytes(conn.outgoing) 
        conn.outgoing = conn.outgoing[len(http.as_string()):]

        # CONNECT method or transparent proxy used
        if http.method == 'CONNECT' or \
           (http.method == 'GET' and self.httpuri(http.path)):
          conn.proxy = server
          self.stats.setproxy(self.uri2serverport(http.path), conn.proxy)

        if http.method == 'GET':
          self.stats.addget(conn.server, http.host, http.path)

        if http.method == 'POST':
          #print "qry: %d, header: %d\nbody:\n%s" % (len(qry), len(qry.split('\r\n\r\n', 1)[0])+4, qry[:368])
          try:
            filename = None
            for k, v in http.POST.items():
              #print k
              try:
                if v.filename:
                  import shutil, tempfile
                  print "writing %s" % v.filename
                  w = tempfile.NamedTemporaryFile(dir='/tmp', delete = False)
                  #w = open('/tmp/xxx', 'wb')
                  shutil.copyfileobj(v.file, w)
                  w.close()
                  filename = v.filename
                  self.stats.addpost(conn.server, http.host, http.path + " %s=%s %s" % (k, v.filename, w.name), w.name, filename)
              except Exception,e:
                  self.stats.addpost(conn.server, http.host, http.path + " %s=%s" % (k, v))
          except Exception,e:
            # stuff the query back into the send buffer
            conn.outgoing = qry + conn.outgoing
            print "-----%s\n>>>\n%s<<<" % (e, conn.outgoing)
            break
      except:
        break

    while conn.incoming:
      if not conn.in_extra:
        conn.in_extra = {}
      if not 'length' in conn.in_extra:
        header = conn.incoming.split('\r\n\r\n', 1)[0]
        for val in header.split('\r\n'):
          if val.split(':')[0].lower() == 'content-length':
            conn.in_extra['length'] = int(val.split(':')[1])
            #print "found len %d" % conn.in_extra['length']

      if 'length' in conn.in_extra and len(conn.incoming) < conn.in_extra['length']:
        #print "zu kurz %d sollte  %d" % (len(conn.incoming), conn.in_extra['length'])
        break

      try:
        split = conn.incoming.split('\r\n\r\n', 1)
        header = split[0]
        body = split[1]
        size = len(header) + len(body) + 4
        http = webob.Response(split[1])

        # TODO des kanns ja eigentlich nicht sein...
        for val in header.split('\r\n'):
          try:
            http.headers.add(val.split(':', 1)[0], val.split(': ', 1)[1])
          except:
            pass

        conn.incoming = conn.incoming[size:]

        if http.content_type != 'text/html':
          pass
        else:
          pass
          #print "%s" % self.decode_body(http)

        # parsing succeeded, clear Content-Length of http-header
        try:
          del conn.in_extra['length'] # TODO re-enable
        except:
          print "xxxx"
      except Exception, e: 
        print str(e) + " yyy"
        break
        #file = open('xxx','w') {{{
        #file.write(http.body)
        #file.close()
        #print self.decode_body(http) }}}

  def handle_half(self, conn):
    pass

  def handle_full(self, conn):
    self.handle_transparent(conn)
    pass

  def decode_body(self, http):
    if http.content_encoding == 'gzip':
      return self.fast_unzip(http.body)  
    if http.content_encoding == 'identity':
      return http.body
    if http.content_encoding == 'bzip2':
      return self.fast_unbzip(http.body)  
    if http.content_encoding == 'deflate':
      return self.fast_deflate(http.body)  
      
  def get_encoding(self, headers):
    # TODO
    """ return enconding of given headers dictionary.
    Does not handle nested encodings yet """
    for header, value in headers.items(): 
      if header.lower() == 'content-encoding':
        return value.lower()        

  def fast_deflate(self, comp):
    try:
      import zlib
      return zlib.decompress(comp)
    except:
      print "no zlib payload"

  def fast_unbzip(self, comp):
    try:
      import bz2
      return bz2.decompress(comp)
    except:
      print "no bz2 payload"

  def fast_unzip(self, comp):
    # TODO was passiert bei exception und return dec?
    try:
      import gzip, StringIO
      handle = StringIO.StringIO(comp)
      gzip_handle = gzip.GzipFile(fileobj=handle)
      dec = gzip_handle.read()
      gzip_handle.close()
    except IOError:
      print "no gzip payload"          
    return dec

  def uri2serverport(self, uri):
    u = urlparse.urlparse(uri)
    server = u.hostname
    port = u.port
    if not real_port:
      port = 80 if u.scheme == 'http' else 443 
    return (server, port)

  def httpuri(self, uri):
    return uri.startswith('http://') or uri.startswith('https://')


