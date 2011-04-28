#!/usr/bin/env python

import json
from urllib2 import urlopen

def get_pull_requests():
    """Download metadata for all open pull requests for sympy."""
    return json.load(urlopen('http://github.com/api/v2/json/pulls/sympy/sympy'))

def get_urls(p):
    """Extract urls from pull request data.

    This usefull for merging."""
    for pull in p['pulls']:
        repo = pull['head']['repository']['url']
        branch = pull['head']['ref']
        yield repo + ' ' + branch

if __name__ == '__main__':
    p = get_pull_requests()
    for url in get_urls(p):
        print url
