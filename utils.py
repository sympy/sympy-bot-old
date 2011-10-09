import json
from urllib2 import urlopen
import subprocess
import os
from os.path import expandvars
import urllib2
import base64
from urllib import urlencode
import time
import sys
from getpass import getpass

class CmdException(Exception):
    pass

class AuthenticationFailed(Exception):
    pass

def format_repo(string, repo):
    return string.format(repo=repo)

def cmd(s, capture=False, ok_exit_code_list=None, echo=False):
    """
    Executes the command "s".

    It raises an exception if the command fails to run.

    capture ... If True, it captures its output and returns it as a string.
    ok_exit_code_list ... a list of ok exit codes (otherwise cmd() raises an
    exception)
    """
    if ok_exit_code_list is None:
        ok_exit_code_list = [0]
    if echo:
        print s
    s = expandvars(s)
    if capture:
        p = subprocess.Popen(s, shell=True, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT)
        output = p.communicate()[0]
        r = p.returncode
    else:
        output = None
        r = os.system(s)
    if r not in ok_exit_code_list:
        raise CmdException("Command '%s' failed with err=%d." % (s, r))
    return output

def cmd2(cmd):
    """
    Runs the command "cmd", mirrors everything on the screen and returns a log
    as well as the return code.
    """
    print "Running unit tests."
    print "Command:", cmd
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT)

    log = ""
    while True:
        char = p.stdout.read(1)
        if not char:
            break
        log += char
        sys.stdout.write(char)
        sys.stdout.flush()
    log = log + p.communicate()[0]
    r = p.returncode

    return log, r


def github_get_pull_request_all(repo):
    """
    Returns all github pull requests.
    """
    return json.load(urlopen( \
            format_repo('http://github.com/api/v2/json/pulls/{repo}', repo)))

def github_get_pull_request(repo, n):
    """
    Returns pull request 'n'.
    """
    url = format_repo('http://github.com/api/v2/json/pulls/{repo}/%d', repo)
    data = json.load(urlopen(url % n))
    return data["pull"]

def github_check_authentication(username, password):
    """
    Checks that username & password is valid.
    """
    if username.endswith('/token'):
        user = username[:-6]
    else:
        user = username

    request = urllib2.Request("https://github.com/api/v2/json/user/show/%s" % user)
    base64string = base64.encodestring('%s:%s' % (username, password)).replace('\n', '')
    request.add_header("Authorization", "Basic %s" % base64string)
    s = json.load(urllib2.urlopen(request))
    if not ("user" in s and "plan" in s["user"]):
        raise AuthenticationFailed("invalid username or password")

def github_add_comment_to_pull_request(repo, n, comment, username, password):
    """
    Adds a 'comment' to the pull request 'n'.

    Currently it needs github username and password (as strings).
    """
    request = urllib2.Request(format_repo( \
            "https://github.com/api/v2/json/issues/comment/{repo}/%d", repo) % \
            n, data=urlencode([("comment", comment)]))
    base64string = base64.encodestring('%s:%s' % (username, password)).replace('\n', '')
    request.add_header("Authorization", "Basic %s" % base64string)
    s = json.load(urllib2.urlopen(request))
    assert s["comment"]["body"] == comment

def pastehtml_upload(source, input_type="html"):
    """
    Uploads 'source' as an 'input_type' type to pastehtml.com.

    source ....... source of the webpage/text
    input_type ... txt or html (default html)

    """
    url = "http://pastehtml.com/upload/create?input_type=%s&result=address"
    request = urllib2.Request(url % input_type, data=urlencode([("txt", source)]))

    while True:
        try:
            result = urllib2.urlopen(request)
            break
        except urllib2.HTTPError:
            print "Error while accessing pastehtml.com, retrying in 2s"
            time.sleep(2)

    s = result.read()
    # There is a bug at pastehtml.com, that sometimes it returns:
    # http://pastehtml.comhttp://pastehtml.com/view/1eddmnp.html
    # instead of:
    # http://pastehtml.com/view/1eddmnp.html
    # So we check if this is the case, and correct it:
    if s.find("http", 2) != -1:
        s = s[s.find("http", 2):]
    return s

def list_pull_requests(repo, numbers_only=False):
    p = github_get_pull_request_all(repo)
    pulls = []
    if numbers_only:
        for pull in p['pulls']:
            print pull['number']
        return
    for pull in p['pulls']:
        n = pull['number']
        repo = pull['head']['repository']['url']
        branch = pull['head']['ref']
        author = '"%s" <%s>' % (pull["user"].get("name", "unknown"),
                                pull["user"].get("email", ""))
        mergeable = pull["mergeable"]
        last_change = pull["updated_at"]
        last_change = time.strptime(last_change, "%Y-%m-%dT%H:%M:%SZ")
        last_change = time.mktime(last_change)
        pulls.append((last_change, n, repo, branch, author, mergeable))
    pulls.sort(key=lambda x: x[0])
    for last_change, n, repo, branch, author, mergeable in pulls:
        print "#%03d: %s %s" % (n, repo, branch)
        print "      Author   : %s" % author
        print "      Date     : %s" % time.ctime(last_change)
        print "      Mergeable: %s" % mergeable

_login_message = """\
Enter your GitHub username & password or press ^C to quit. The password
will be kept as a Python variable as long as sympy-bot is running and
https to authenticate with GitHub, otherwise not saved anywhere else:\
"""

def github_authenticate(config):
    def get_password():
        while True:
            password = getpass("Password: ")

            try:
                print "> Checking username and password ..."
                github_check_authentication(username, password)
            except AuthenticationFailed:
                print ">     Authentication failed."
            else:
                print ">     OK."
                return password

    if config.user:
        username = config.user

        if config.token:
            username = username + '/token'
            password = config.token

            try:
                print "> Checking username and password ..."
                github_check_authentication(username, password)
            except AuthenticationFailed:
                print ">     Authentication failed."
                password = get_password()
            else:
                print ">     OK."
        else:
            password = get_password()
    else:
        print _login_message

        username = raw_input("Username: ")
        password = get_password()

    return username, password


def create_report(log, status, test_command, interpreter,
            pullrequest_url, pullrequest_num):
    # Important note: currently the template is using Python string formatting.
    # If we switch to jinja (for example), we need to change '%%' -> '%' in the
    # template.
    template = open("report_template.html").read()
    if status == "PASSED":
        result = '<span class="result_ok">Passed</span>'
    elif status == "FAILED":
        result = '<span class="result_fail">Failed</span>'
    elif status == "conflict":
        result = "merge conflict"
    elif status == "fetch":
        result = "failed to fetch the branch"
    else:
        result = "unknown result"
    return template % {"log": log, "result": result,
            "testcommand": test_command,
            "interpreter": interpreter,
            "pullrequest_url": pullrequest_url,
            "pullrequest_num": pullrequest_num}
