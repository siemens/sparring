# Copyright (C) 2012-2013 sparring Developers.
# This file is part of sparring - http://github.com/thomaspenteker/sparring
# See the file 'docs/LICENSE' for copying permission.

from twisted.words.service import InMemoryWordsRealm, IRCFactory
from twisted.words import service
from twisted.test import proto_helpers
from twisted.words.protocols import irc
from twisted.cred import checkers, portal, credentials
#from pudb import set_trace; set_trace()

class IRCUser(service.IRCUser):

  # Twisted callbacks
  def connectionMade(self):
    self.realm = self.factory.realm
    self.hostname = self.realm.name

  def irc_PASS(self, prefix, params):
    # we dont care if PASS was sent
    self.password = ""

  def irc_PONG(self, prefix, params):
    # we dont care
    pass

  def irc_NICK(self, prefix, params):
    """Nick message -- Set your nickname.

    Parameters: <nickname>

    [REQUIRED]
    """
    try:
        nickname = params[0].decode(self.encoding)
    except UnicodeDecodeError:
        self.privmsg(
            NICKSERV,
            nickname,
            'Your nickname cannot be decoded. Please use ASCII or UTF-8.')
        self.transport.loseConnection()
        return

    self.nickname = nickname
    self.name = nickname

    if not self.avatar:
      self.avatar = self.realm.createUser(unicode(nickname)).result
      self.avatar.loggedIn(self.realm, self)
      self.password = ''

    for code, text in self._motdMessages:
        self.sendMessage(code, text % self.factory._serverInfo)

  def _userMode(self, user, modes=None):
    if user is self.avatar:
      self.sendMessage(
        irc.RPL_UMODEIS,
        "+")
    else:
      self.sendMessage(
        irc.ERR_USERSDONTMATCH,
        ":You can't look at someone else's modes.")

  def _channelMode(self, group, modes=None, *args):
    self.channelMode(self.name, '#' + group.name, '+')

class IRCFactory(service.IRCFactory):
  """
  IRC server that creates instances of the L{IRCUser} protocol.
  
  @ivar _serverInfo: A dictionary mapping:
      "serviceName" to the name of the server,
      "serviceVersion" to the copyright version,
      "creationDate" to the time that the server was started.
  """
  protocol = IRCUser

  def __init__(self, realm, portal):
    self.realm = realm
    self.portal = portal
    self._serverInfo = {
        "serviceName": self.realm.name,
        "serviceVersion": '42.23-666',
        "creationDate": 1337
        }

class ircd(object):
  def __init__(self, chost):
    self.r = InMemoryWordsRealm(chost)
    self.r.createGroupOnRequest = True
    self.r.createUserOnRequest = True
    self.p = portal.Portal(self.r) #, [checkers.InMemoryUsernamePasswordDatabaseDontUse(john="pass")])
    self.f = IRCFactory(self.r, self.p)
    self.client = self.f.buildProtocol(None)
    self.server = proto_helpers.StringTransport()
    self.client.makeConnection(self.server)

