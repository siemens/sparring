from socket import inet_ntoa

class Stats():
  #cats = {} # 'statisch' geteiltes Objekt fuer alle Instantenzen
  def __init__(self):
    self.cats = {}
    self.cats['Server'] = {}

  def addserver(self, server, proxy = None):
    if server in self.cats['Server']:
      return
    self.cats['Server'][server] = [ proxy ]

  # default output is generated in a haskellesque way
  def p(self, x, level):
    ret = ''
    if type(x) == type([]):
      for xs in x:
        ret += "%s\n" % self.p(xs, level+2)
      return ret
    if type(x) == type(()):
      for xs in x:
        try:
          ret += "%s " % inet_ntoa(xs)
        except:
          ret += "%s " % xs
      return "%s%s" % (" "*level, ret)
    elif type(x) == type({}):
      for k, v in x.items():
        ret += "\n%s%s\n%s" % (" "*level, self.p(k, level), self.p(v, level+2))
      return ret
    else:
      return "%s%s" % (" "*(level+2), x)

  def __str__(self):
    return self.p(self.cats, 0)

