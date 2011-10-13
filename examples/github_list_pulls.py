"""
This example shows how to access github pull requests.
"""
from urllib2 import urlopen
import json
from time import time

def v2():
    # v2:
    base_url = "http://github.com/api/v2/json/pulls/"
    data = json.load(urlopen(base_url + "sympy/sympy"))
    for pull in data["pulls"]:
        print "#", pull["number"], ":", pull["title"]
    print

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
        url = l[1:i-1]
        assert l[i-1] == ">"
        assert l[i+1:i+7] == ' rel="'
        j = l.find('"', i+7)
        assert j != -1
        param = l[i+7:j]
        d[param] = url

        if len(l) == j+1:
            break
        assert l[j+1] == ","
        j += 2
        l = l[j+1:]
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
        data = json.load(r)
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

# v3:
base_url = "https://api.github.com"
url = base_url + "/repos/sympy/sympy/pulls?state=closed"
#url = base_url + "/repos/sympy/sympy/pulls?state=open"
print "Getting all pull requests..."
t = time()
pulls = get_all_pages(url)
print "    Done in:", time()-t
for pull in pulls:
    print "#", pull["number"], ":", pull["title"]
    #print pull.keys()
    #stop
