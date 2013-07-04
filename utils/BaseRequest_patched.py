# Copyright (C) 2012-2013 sparring Developers.
# This file is part of sparring - http://github.com/thomaspenteker/sparring
# See the file 'docs/LICENSE' for copying permission.

from webob import BaseRequest

# CHECK BaseRequest is only referenced by webob internally. How can this be
# monkey patched?
class BaseRequest_patched(BaseRequest)
