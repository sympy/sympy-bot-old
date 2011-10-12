"""Convenient interface to JSON RPC services. """

import logging
from uuid import uuid4
from urllib2 import urlopen, Request
try:
    from django.utils.simplejson import dumps, loads
except ImportError:
    from json import dumps, loads

from google.appengine.api.urlfetch import DownloadError

class JSONRPCError(Exception):

    def __init__(self, error):
        self.error = error

    def __str__(self):
        return self.error['message']

class JSONRPCMethod(object):
    """Represents a JSON RPC method of some service. """

    def __init__(self, url, method, auth=None):
        self.url = url
        self.method = method
        self.auth = auth

    def __repr__(self):
        return "<jsonrpc-method %s at %s>" % (self.method, self.url)

    def __getattr__(self, method):
        method = "%s.%s" % (self.method, method)
        return self.__class__(self.url, method, auth)

    def __call__(self, *params):
        if self.auth is not None:
            params = self.auth + params

        data = dumps({
            'jsonrpc': '2.0',
            'method': self.method,
            'params': params,
            'id': uuid4().hex,
        })

        request = Request(self.url, data, {
            'Content-Type': 'application/json',
        })

        logging.info("Sending JSON request: %s" % data)
        try:
            url = urlopen(request)
        except DownloadError, e:
            # This can happen for multiple reasons:
            #   * the engine is not running at all
            #   * the engine is warming up and the request fails (simple retry
            #   is needed)
            # We simply propagate this error up, and it should be handled in
            # JavaScript by retrying.
            logging.info("ulropen failed with DownloadError: %s" % e)
            raise JSONRPCError({
                "message": "ulropen failed with DownloadError"
                })
        response = loads(url.read())
        url.close()

        if response.get('error', None) is None:
            return response['result']
        else:
            raise JSONRPCError(response['error'])

class JSONRPCNamespace(object):
    """Represents a collection of JSON RPC methods. """

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return "<jsonrpc-namespace %s>" % self.name

class JSONRPCService(object):
    """
    Provides convenient access to a JSON RPC service.

    To use it, first connect to the service, for example:

    >>> from onlinelab.console.jsonrpc import JSONRPCService
    >>> s = JSONRPCService("http://lab.femhub.org/async")

    If there is no JSON RPC service running at the url, you get an exception:

    >>> s = JSONRPCService("http://lab.femhub.org/some_random_url")
    Traceback (most recent call last):
    ...
    ValueError: No JSON object could be decoded

    After you are connected, then you investigate what methods are available,
    for example in ipython, type:

    >>> s.<TAB>
    s.auth
    s.complete
    s.desc
    s.evaluate
    s.init
    s.interrupt
    s.kill
    s.stat
    s.url

    This shows you what methods the server offers. You need to study the
    documentation for the server to learn how those methods should be used. In
    this particular example, you first initialize the engine:


    >>> s.init("some_uuid")
    {'status': 'started'}

    And then use it:

    >>> s.evaluate("some_uuid", "2+3")
    {'err': '',
     'files': [],
     'index': 1,
     'interrupted': False,
     'out': '5\n',
     'plots': [],
     'source': '2+3',
     'time': 0.0,
     'traceback': False}


    >>> s.evaluate("some_uuid", "from sympy import sin, pi")
    {'err': '',
     'files': [],
     'index': 2,
     'interrupted': False,
     'out': '',
     'plots': [],
     'source': 'from sympy import sin, pi',
     'time': 0.0,
     'traceback': False}

    >>> s.evaluate("some_uuid", "sin(pi/3)")
    {'err': '',
     'files': [],
     'index': 3,
     'interrupted': False,
     'out': '3**(1/2)/2\n',
     'plots': [],
     'source': 'sin(pi/3)',
     'time': 0.010000000000000009,
     'traceback': False}

    Finally you kill the engine by::

    >>> s.kill("some_uuid")
    {'status': 'killed'}

    """

    def __init__(self, url, auth=None):
        self.url = url
        self.auth = auth

        self.desc = JSONRPCMethod(self.url, 'system.describe')()

        for proc in self.desc['procs']:
            names = proc['name'].split('.')
            namespace = self

            for name in names[:-1]:
                if not hasattr(namespace, name):
                    ns = JSONRPCNamespace(name)
                    setattr(namespace, name, ns)

                namespace = getattr(namespace, name)

            if proc.get('authenticated', False):
                auth = self.auth
            else:
                auth = None

            method = JSONRPCMethod(self.url, proc['name'], auth)
            method.__doc__ = proc.get('summary', None)

            setattr(namespace, names[-1], method)

    def __repr__(self):
        return "<jsonrpc-service %s>" % self.url

