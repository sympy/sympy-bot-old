import sys
import time
import urllib2

from jsonrpc import JSONRPCService
from urllib import urlencode

def reviews_pastehtml_upload(source, input_type="html"):
    """
    Uploads 'source' as an 'input_type' type to pastehtml.com.

    source ....... source of the webpage/text
    input_type ... txt or html (default html)

    """
    url = "http://pastehtml.com/upload/create?input_type=%s&result=address"
    request = urllib2.Request(url % input_type, data=urlencode([("txt", source)]))

    timer = 1
    while True:
        try:
            result = urllib2.urlopen(request)
            break
        except urllib2.HTTPError:
            print "Error while accessing pastehtml.com, retrying in %d seconds..." % timer
            time.sleep(timer)
            timer *= 2

    s = result.read()
    # There is a bug at pastehtml.com, that sometimes it returns:
    # http://pastehtml.comhttp://pastehtml.com/view/1eddmnp.html
    # instead of:
    # http://pastehtml.com/view/1eddmnp.html
    # So we check if this is the case, and correct it:
    if s.find("http", 2) != -1:
        s = s[s.find("http", 2):]
    return s

def reviews_sympy_org_upload(data, url_base):
    timer = 1
    while True:
        try:
            s = JSONRPCService(url_base + "/async")
            r = s.RPC.upload_task(data["num"], data["result"],
                    data["interpreter"], data["testcommand"], data["log"])
            if "task_url" in r:
                break
            else:
                # This happens for example when the server is over quota, see
                # https://github.com/sympy/sympy-bot/issues/110
                print "Server problem at %s, retrying in %d seconds..." % (url_base, timer)
        except (urllib2.HTTPError, urllib2.URLError):
            # The server is down or we cannot connect to the internet
            print "Error while accessing %s, retrying in %d seconds..." % (url_base, timer)

        time.sleep(timer)
        timer *= 2

    return r["task_url"]
