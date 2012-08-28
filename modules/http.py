import dpkt
import gzip, StringIO
from socket import AF_INET, AF_INET6, inet_ntoa


def init(mode):
  return Http(mode)

class Http():
  def __init__(self, mode):
    # one of TRANSPARENT, FULL, HALF
    self.mode = mode
    #print '%s initialisiert [%s]' % (__name__,self.mode)

  def protocols(self):
    return ['http']

  def classify(self, data):
    if data.split('\n')[0][-9:][:5] == 'HTTP/' or data.split('\n')[0][:5] == 'HTTP/':
      return True
    else:
      return False

  def handle(self, pkt, data):
    if self.mode == 'TRANSPARENT':
      return self.handle_transparent(pkt, data)
    if self.mode == 'HALF':
      return self.handle_half(pkt, data)
    if self.mode == 'FULL':
      return self.handle_full(pkt, data)

  def handle_transparent(self, pkt, data):
    """ pkt is ip data, data is tcp _payload (i.e. tcp.data)  """
    tcp = pkt.data
    print "HTTP     %s:%d->%s:%d   (%d)" % (inet_ntoa(pkt.src), tcp.sport, inet_ntoa(pkt.dst), tcp.dport, tcp.seq)

    if data[:5] == 'HTTP/':
      try:
        http = dpkt.http.Response(data)
        print "%s <-- %s: HTTP %s %s" % (inet_ntoa(pkt.src), inet_ntoa(pkt.dst), http.status, http.reason)
        self.decode_body(http)
      except dpkt.dpkt.UnpackError:
        pass
      #if pkt.p == dpkt.ip.IP_PROTO_TCP: {{{
      #  print "%s -> %s" % (inet_ntoa(pkt.src), inet_ntoa(pkt.dst))
      #file = open('xxx','w')
      #file.write(http.body)
      #file.close()
      #print self.decode_body(http) }}}
    else: 
      http = dpkt.http.Request(data)
      hdrs = http.headers
      hdrs['accept-encoding'] = ''  # TODO support unzipping
      http.headers = hdrs
      print "HTTP     %s --> %s: %s %s" % (inet_ntoa(pkt.src), inet_ntoa(pkt.dst), http.method, http.uri)

  def handle_half(self, pkt):
    pass

  def handle_full(self, pkt):
    pass

  def decode_body(self, http):
    if self.get_encoding(http.headers) == 'gzip':
      return self.fast_unzip(http.body)  
    if self.get_encoding(http.headers) == 'bzip2':
      return self.fast_unbzip(http.body)  
      
  def get_encoding(self, headers):
    """ return enconding of given headers dictionary.
    Does not handle nested encodings yet TODO """
    for header, value in headers.items(): 
      if header.lower() == 'content-encoding':
        return value.lower()        

  def fast_unbzip(self, comp):
    # TODO stub
    pass

  def fast_unzip(self, comp):
    try:
      handle=StringIO.StringIO(comp)
      gzip_handle = gzip.GzipFile(fileobj=handle)
      dec = gzip_handle.read()
      gzip_handle.close()
    except IOError:
      print "no gzip payload"          
    return dec

