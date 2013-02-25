import sys
import time
import urllib2

from jsonrpc import JSONRPCService
from urllib import urlencode

from utils.cmd import keep_trying

def reviews_pastehtml_upload(source, input_type="html"):
    """
    Uploads 'source' as an 'input_type' type to pastehtml.com.

    source ....... source of the webpage/text
    input_type ... txt or html (default html)

    """
    url = "http://pastehtml.com/upload/create?input_type=%s&result=address"
    request = urllib2.Request(url % input_type, data=urlencode([("txt", source)]))

    result = keep_trying(lambda: urllib2.urlopen(request), urllib2.URLError, "access pastehtml.com")

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
    def _do_upload():
        s = JSONRPCService(url_base + "/async")
        r = s.RPC.upload_task(data["num"], data["result"],
                data["interpreter"], data["testcommand"], data["log"])
        if "task_url" not in r:
            # This happens for example when the server is over quota, see
            # https://github.com/sympy/sympy-bot/issues/110

            # Note that this exact error message is checked below, in case
            # something else raises a ValueError
            raise urllib2.URLError("Quota")

        return r

    def _handler(e):
        if e.message == "Quota":
            print "Server appears to be over quota."
        else:
            raise e

    r = keep_trying(_do_upload, urllib2.URLError, "access %s" %
                    url_base, _handler)

    return r["task_url"]
