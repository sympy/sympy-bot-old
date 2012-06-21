import json
from urllib2 import urlopen, URLError
import subprocess
import os
from os.path import expandvars
import urllib2
import base64
from urllib import urlencode
import time
import sys
import re
from getpass import getpass

from jsonrpc import JSONRPCService

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

def get_interpreter_version_info(interpreter):
    """
    Get python version of `interpreter`
    """

    code = "import sys; print('%s.%s.%s-%s-%s' % sys.version_info[:])"
    cmd = '%s -c "%s"' % (interpreter, code)
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT)
    ouput = p.stdout.read()

    return ouput.strip()

def get_interpreter_exe(interpreter):
    """
    Get python executable path for 'nt'
    """

    code = "import sys; print(sys.executable)"
    cmd = '%s -c "%s"' % (interpreter, code)
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT)
    ouput = p.stdout.read()

    return ouput.strip()

def get_xpassed_info_from_log(log):
    re_xpassed = re.compile("\s+_+\s+xpassed tests\s+_+\s+(?P<xpassed>([^\n]+\n)+)\n", re.M)
    m = re_xpassed.search(log)
    if m:
        lines = m.group('xpassed')
        return lines.splitlines()
    return []

def github_get_pull_request_all(url):
    """
    Returns all github pull requests.
    """
    return query2github(url)

def github_get_pull_request(url, n):
    """
    Returns pull request 'n'.
    """
    url = url % n
    timer = 1
    while True:
        try:
            pull = query2github(url)
            break
        except URLError:
            print "Could not get pull request, retrying in %d seconds..." % timer
            time.sleep(timer)
            timer *= 2

    return pull

def github_get_user_info(url, username):
    url = url % username
    timer = 1
    while True:
        try:
            user_info = query2github(url)
            break
        except URLError:
            print "Could not get user information, retrying in %d seconds..." % timer
            time.sleep(timer)
            timer *= 2

    return user_info

def github_check_authentication(url, username, password):
    """
    Checks that username & password is valid.
    """
    query2github(url, username, password)

def github_add_comment_to_pull_request(url, username, password, n, comment):
    """
    Adds a 'comment' to the pull request 'n'.

    Currently it needs github username and password (as strings).
    """
    enc_comment = json.dumps(
        {
            "body" : comment
        }
    )
    url = url % n
    response = query2github(url, username, password, enc_comment)
    assert response["body"] == comment

def pastehtml_upload(source, input_type="html"):
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
        except urllib2.HTTPError:
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
        repo = pull["head"]["repo"]["html_url"]
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

_login_message = """\
Enter your GitHub username & password or press ^C to quit. The password
will be kept as a Python variable as long as sympy-bot is running and
https to authenticate with GitHub, otherwise not saved anywhere else:\
"""

def github_authenticate(url, config):
    def get_password():
        while True:
            password = getpass("Password: ")

            try:
                print "> Checking username and password ..."
                github_check_authentication(url, username, password)
            except AuthenticationFailed:
                print ">     Authentication failed."
            else:
                print ">     OK."
                return password

    if config.user:
        username = config.user

        if config.password:
            password = config.password

            try:
                print "> Checking username and password ..."
                github_check_authentication(url, username, password)
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

def query2github(url, username="", password="", data=""):
    """
    Query github API,
    if username and password are presented, then the query is executed from the user account
    """
    request = urllib2.Request(url)
    # Add authentication headers to request, if username and password presented
    if username is not "" and password is not "":
        base64string = base64.encodestring('%s:%s' % (username, password)).replace('\n', '')
        request.add_header("Authorization", "Basic %s" % base64string)
    if data is not "":
        request.add_data(data)
    try:
        http_response = urlopen(request)
        response_body = json.load(http_response)
    except urllib2.HTTPError, e:
        # Auth exception
        if e.code == 401:
            raise AuthenticationFailed("invalid username or password")
        # Other exceptions
        raise urllib2.HTTPError(e.filename, e.code, e.msg, None, None)
    except ValueError, e:
        # If auth was successful
        if http_response.code in (204, 302):
            return []
        # else return original error
        raise ValueError(e)

    return response_body
