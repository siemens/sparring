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
        log.warn('dns: DNSRecord.parse failed: %s', str(e))
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
        log.warn('dns: Unsupported DNS record type encountered. Raw data:')
        log.warn('Connection: %s' % conn)
        log.warn(answer)
        break
      except Exception, e:
        log.warn('dns: Exception for incoming DNS:\n',e)
        break

    return (question, answer)    

  def handle_half(self, conn):
    # general outline:
    # receive request
    question, answer = self.handle_transparent(conn)
    assert(not answer)
    if question:
      log.warn('dns: ' + question.send(conn.remote[0]))

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
      # this is done again to record our artifical answer, too
      conn.incoming.write(a.pack())
      self.handle_transparent(conn)
    pass

