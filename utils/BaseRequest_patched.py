from webob import BaseRequest

# CHECK BaseRequest is only referenced by webob internally. How can this be
# monkey patched?
class BaseRequest_patched(BaseRequest)
