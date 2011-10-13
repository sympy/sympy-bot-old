"""
This example shows how to access github pull requests.
"""
from urllib2 import urlopen
import json

base_url = "http://github.com/api/v2/json/pulls/"
data = json.load(urlopen(base_url + "sympy/sympy"))
for pull in data["pulls"]:
    print "#", pull["number"], ":", pull["title"]
