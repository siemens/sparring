class Stats():
  cats = {}
  # default output is generated in a haskellesque way
  def p(self, x, level):
    ret = ''
    if type(x) == type([]):
      for xs in x:
        ret += "%s\n" % self.p(xs, level+2)
      return ret
    if type(x) == type(()):
      for xs in x:
        ret += "%s " % xs
      return "%s%s" % (" "*level, ret)
    elif type(x) == type({}):
      for k, v in x.items():
        ret += "\n%s%s\n%s" % (" "*level, k, self.p(v, level+2))
      return ret
    else:
      return "%s%s" % (" "*(level+2), x)

  def __str__(self):
    return self.p(self.cats, 0)

