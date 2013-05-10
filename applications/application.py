
class Application():
  def __init__(self, mode):
    self.mode = mode
    self.handle_ = None
    self.stats = None
    self.protos = []

    if self.mode == 'TRANSPARENT':
      self.handle_ = self.handle_transparent
    elif self.mode == 'HALF':
      self.handle_ = self.handle_half
    elif self.mode == 'FULL':
      self.handle_ = self.handle_full

  def classify(self, conn):
    """try to classify the specified connection
    @raise NotImplementedError: this method is abstract.
    """
    raise NotImplementedError

  def handle(self, conn):
    self.handle_(conn)
    #if self.mode == 'TRANSPARENT':
    #  self.handle_transparent(conn)
    #elif self.mode == 'HALF':
    #  self.handle_half(conn)
    #elif self.mode == 'FULL':
    #  self.handle_full(conn)
  
  def handle_transparent(self, conn):
    """handle data in transparent mode.
    @raise NotImplementedError: this method is abstract.
    """
    raise NotImplementedError

  def handle_half(self, conn):
    """handle data in half mode.
    @raise NotImplementedError: this method is abstract.
    """
    raise NotImplementedError

  def handle_full(self, conn):
    """handle data in full mode.
    @raise NotImplementedError: this method is abstract.
    """
    raise NotImplementedError

  def get_stats(self):
    print self.stats

  def protocols(self):
    return self.protos

  def setup(self, conn):
    """this function is meant to be called after a successful protocol
    identification for setting up the required entries in self.conn etc.
    """
    pass

