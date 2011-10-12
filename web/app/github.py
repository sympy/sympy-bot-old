"""
Python API (that works on the GAE) for accessing GitHub.
"""

from urllib2 import urlopen

try:
    from django.utils.simplejson import load
except ImportError:
    from json import load


def github_get_pull_request_all(repo):
    """
    Returns all github pull requests.
    """
    return load(urlopen('http://github.com/api/v2/json/pulls/%s' % repo))
