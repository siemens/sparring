import dpkt
import stats
import urlparse
import webob
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
    self.cats['Server'][server] += [ u.geturl() ]

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
    return (conn.incoming.split('\n')[0].startswith('HTTP/') or conn.outgoing.split('\n')[0][-9:][:5] == 'HTTP/')

  def get_stats(self):
    print self.stats
    #for server, details in self.servers.items():
    #  print "%15.15s:%-4d    via PROXY: %r" % (inet_ntoa(server[0]), server[1], details)

  def handle(self, conn):

    # gather stats
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

    while len(conn.outgoing) > 0:
      try:
        # TODO add hack to skip dpkt parsing if content obviously
        # is payload (i.e. large HTTP body during downloads) to
        # prevent performance degradation and an exception?
        http = dpkt.http.Request(conn.outgoing)
        qry = conn.outgoing[:len(http)]
        conn.outgoing = conn.outgoing[len(http):]

        # CONNECT method or transparent proxy used
        if http.method == 'CONNECT' or \
           (http.method == 'GET' and self.httpuri(http.uri)):
          conn.proxy = server
          self.stats.setproxy(self.uri2serverport(http.uri), conn.proxy)

        if http.method == 'GET':
          self.stats.addget(conn.server, http.headers['host'], http.uri)

        if http.method == 'POST':
          try:
            #r = webob.Request.from_string("%s %s HTTP/%s" % (http.method, http.uri, http.version))
            r = webob.Request.from_string(qry)
            for k, v in r.POST.items():
              try:
                if v.filename:
                  import shutil
                  print "writing %s" % v.name
                  w = open('/tmp/xxx', 'wb')
                  shutil.copyfileobj(v.file, w)
                  w.close()
              except:
                pass
          except:
            print 'kein OB'
      except:
        break

    while len(conn.incoming) > 0:
      try:
          http = dpkt.http.Response(conn.incoming)
          conn.incoming = conn.incoming[len(http):]
          #except dpkt.dpkt.UnpackError, IndexError:
      except:
        break
        #file = open('xxx','w') {{{
        #file.write(http.body)
        #file.close()
        #print self.decode_body(http) }}}

  def handle_half(self, conn):
    pass

  def handle_full(self, conn):
    pass

  def decode_body(self, http):
    if self.get_encoding(http.headers) == 'gzip':
      return self.fast_unzip(http.body)  
    if self.get_encoding(http.headers) == 'bzip2':
      return self.fast_unbzip(http.body)  
    if self.get_encoding(http.headers) == 'deflate':
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


