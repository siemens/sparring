# Copyright (c) Siemens AG, 2013
#
# This file is part of sparring.  sparring is free software: you can
# redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation; either version 2
# of the License, or(at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#

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

  """ call this before json.dump-ing stats to make sure ip addresses are converted """
  def json(self):
    cats = self.cats
    if cats.has_key('Server'):
      for key in cats['Server'].keys():
        try:
          newkey = "%s:%d" % (inet_ntoa(key[0]), key[1])
          self.cats['Server'][newkey] = self.cats['Server'][key]
          del self.cats['Server'][key]
        except:
          pass

  def __str__(self):
    return self.p(self.cats, 0)

class Server():

  def __init__(self, address, meta={}):
    self.address = address
    self.meta = meta
    self.channel = {}

  def __str__(self):
    return self.address + '\n' + self.meta + '\n' + self.channel

