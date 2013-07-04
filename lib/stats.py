# Copyright (C) 2012-2013 sparring Developers.
# This file is part of sparring - http://github.com/thomaspenteker/sparring
# See the file 'docs/LICENSE' for copying permission.

from socket import inet_ntoa

class Stats():
  def __init__(self):
    self.cats = {}
    self.cats['Server'] = {}
    self.servers = {}

  def log_server(self, server, proxy = None):
    if server in self.cats['Server']:
      return
    self.cats['Server'][server] = []

  def log_server2(self, server, meta={}):
    if not server in self.servers:
      self.servers[server] = Server(server, meta)

  """ string representation of the stats object """
  def p(self, x, level):
    try:
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
    except UnicodeDecodeError:
      return "unicodeDecodeError"

  def __str__(self):
    return self.p(self.cats, 0)

class Server():

  def __init__(self, address, meta={}):
    self.address = address
    self.meta = meta
    self.channel = {}

  def __str__(self):
    return self.address + '\n' + self.meta + '\n' + self.channel

