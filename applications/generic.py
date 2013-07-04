# Copyright (C) 2012-2013 sparring Developers.
# This file is part of sparring - http://github.com/thomaspenteker/sparring
# See the file 'docs/LICENSE' for copying permission.

from dnslib import *
from stats import Stats
from application import Application
from os import SEEK_END

def init(mode):
  return Generic(mode)

""" statistic class suitable for about any type of application protocol """
class Genericstats(Stats):

  def __init__(self):
    Stats.__init__(self)

  def log_server(self, server):
    if server in self.cats['Server']:
      return
    self.cats['Server'][server] = {}

  def log_detail(self, server, key, value):
    self.log_server(server)
    self.cats['Server'][server][key] = value
    #print "logged detail %s: %s:%s" % (server, key, value)


""" Class for characterisation of connection of unknown type.

Generic application protocol classification class it is designed to be
invoked as a last resort if a connection could not be classified during its
whole life time. Thus it should be called on conncetion or program shutdown
for all unidentified connections. """
class Generic(Application):
  servers = {}

  def __init__(self, mode):
    # one of TRANSPARENT, FULL, HALF
    Application.__init__(self, mode)
    self.stats = Genericstats()
    self.protos = ['generic']
    self.active = False

  def setactive(self, state):
    self.active  = state

  def setup(self, conn):
    conn.in_extra = {}

  def classify(self, conn):
    return self.active

  def handle(self, conn):
    conn.outgoing.seek(0, SEEK_END)
    conn.incoming.seek(0, SEEK_END)
    byte_out = conn.outgoing.tell()
    byte_in = conn.incoming.tell()
    self.stats.log_detail(conn.remote, 'Byte In', byte_in)
    self.stats.log_detail(conn.remote, 'Byte Out', byte_out)
    self.stats.log_detail(conn.remote, 'Transport', conn.transport.name)
