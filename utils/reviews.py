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

def list_pull_requests(urls, numbers_only=False):
    """
    Returns the pull requests numbers.

    It returns a tuple of (nonmergeable, mergeable), where "nonmergeable"
    and "mergeable" are lists of the pull requests numbers.
    """
    pulls = github_get_pull_request_all(urls.pull_list_url)
    formated_pulls = []
    print "Total pull count", len(pulls)
    sys.stdout.write("Processing pulls...")
    for pull in pulls:
        n = pull["number"]
        sys.stdout.write(" %d" % n)
        sys.stdout.flush()
        pull_info = github_get_pull_request(urls.single_pull_template, n)
        mergeable = pull_info["mergeable"]
        if pull["head"]["repo"]:
            repo = pull["head"]["repo"]["html_url"]
        else:
            repo = None
        branch = pull["head"]["ref"]
        created_at = pull["created_at"]
        created_at = time.strptime(created_at, "%Y-%m-%dT%H:%M:%SZ")
        created_at = time.mktime(created_at)
        username = pull["head"]["user"]["login"]
        user_info = github_get_user_info(urls.user_info_template, username)
        author = "\"%s\" <%s>" % (user_info.get("name", "unknown"),
                                  user_info.get("email", ""))
        formated_pulls.append((created_at, n, repo, branch, author, mergeable))
    formated_pulls.sort(key=lambda x: x[0])
    print "\nPatches that cannot be merged without conflicts:"
    nonmergeable = []
    for created_at, n, repo, branch, author, mergeable in formated_pulls:
        if mergeable: continue
        nonmergeable.append(int(n))
        if numbers_only:
            print n,
        else:
            print "#%03d: %s %s" % (n, repo, branch)
            print unicode("      Author   : %s" % author).encode('utf8')
            print "      Date     : %s" % time.ctime(created_at)
    if numbers_only:
        print
    print
    print "-"*80
    print "Patches that can be merged without conflicts:"
    mergeable_list = []
    for last_change, n, repo, branch, author, mergeable in formated_pulls:
        if not mergeable: continue
        mergeable_list.append(int(n))
        if numbers_only:
            print n,
        else:
            print "#%03d: %s %s" % (n, repo, branch)
            print unicode("      Author   : %s" % author).encode('utf8')
            print "      Date     : %s" % time.ctime(last_change)
    if numbers_only:
        print
    return nonmergeable, mergeable_list
