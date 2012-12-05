"""
Python API (that works on the GAE) for accessing GitHub.
"""

from urllib2 import urlopen

try:
    from django.utils.simplejson import load
except ImportError:
    from json import load


def github_get_pull_request_all_v2(repo):
    """
    Returns all github pull requests.
    """
    data = load(urlopen('http://github.com/api/v2/json/pulls/%s' % repo))
    return data["pulls"]


def github_get_pull_request_all_v3(repo, state="open"):
    assert state in ["open", "closed"]
    base_url = "https://api.github.com"
    url = base_url + "/repos/%s/pulls?state=%s" % (repo, state)
    return get_all_pages(url)


def github_get_pull_request(repo, n):
    base_url = "https://api.github.com"
    url = base_url + "/repos/%s/pulls/%d" % (repo, n)
    return load(urlopen(url))


def github_get_user(user):
    base_url = "https://api.github.com"
    url = base_url + "/users/%s" % (user)
    return load(urlopen(url))


def link2dict(l):
    """
    Converts the GitHub Link header to a dict:

    Example::

    >>> link2dict('<https://api.github.com/repos/sympy/sympy/pulls?page=2&state=closed>; rel="next", <https://api.github.com/repos/sympy/sympy/pulls?page=21&state=closed>; rel="last"')
    {'last': 'https://api.github.com/repos/sympy/sympy/pulls?page=21&state=closed', 'next': 'https://api.github.com/repos/sympy/sympy/pulls?page=2&state=closed'}

    """
    d = {}
    while True:
        i = l.find(";")
        assert i != -1
        assert l[0] == "<"
        url = l[1:i - 1]
        assert l[i - 1] == ">"
        assert l[i + 1:i + 7] == ' rel="'
        j = l.find('"', i + 7)
        assert j != -1
        param = l[i + 7:j]
        d[param] = url

        if len(l) == j + 1:
            break
        assert l[j + 1] == ","
        j += 2
        l = l[j + 1:]
    return d


def get_all_pages(url):
    """
    Retrieves all pages.

    The url must return a list, and it should not contain the per_page
    parameter, that will be overriden to 100.

    Note: if there are lots of items, this may take very long.
    """
    assert url.find("per_page") == -1
    url = url + "&per_page=100"
    l = []
    while True:
        #print url
        r = urlopen(url)
        data = load(r)
        assert isinstance(data, list)
        l.extend(data)
        link = r.headers.get("Link")
        if not link:
            break
        d = link2dict(link)
        url = d.get("next")
        if not url:
            break
    return l
