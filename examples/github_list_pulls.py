"""
This example shows how to access github pull requests.
"""
from urllib2 import urlopen
import json

# v2:
base_url = "http://github.com/api/v2/json/pulls/"
data = json.load(urlopen(base_url + "sympy/sympy"))
for pull in data["pulls"]:
    print "#", pull["number"], ":", pull["title"]

print

# v3:
base_url = "https://api.github.com"
data = json.load(urlopen(base_url + "/repos/sympy/sympy/pulls"))
for pull in data:
    print "#", pull["number"], ":", pull["title"]
