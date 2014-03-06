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

from lib.stats import Stats
from applications.application import Application
from os import SEEK_END
from dnslib import *

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
