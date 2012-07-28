import base64
import json
import sys
import time
import urllib2
from getpass import getpass

class AuthenticationFailed(Exception):
    pass

_login_message = """\
Enter your GitHub username & password or press ^C to quit. The password
will be kept as a Python variable as long as sympy-bot is running and
https to authenticate with GitHub, otherwise not saved anywhere else:\
"""

def github_get_pull_request_all(urls):
    """
    Returns all github pull requests.
    """
    return _query(urls.pull_list_url)

def github_get_pull_request(urls, n):
    """
    Returns pull request 'n'.
    """
    url = urls.single_pull_template % n
    timer = 1
    while True:
        try:
            pull = _query(url)
            break
        except urllib2.URLError:
            print "Could not get pull request, retrying in %d seconds..." % timer
            time.sleep(timer)
            timer *= 2

    return pull

def github_get_user_info(urls, username):
    url = urls.user_info_template % username
    timer = 1
    while True:
        try:
            user_info = _query(url)
            break
        except urllib2.URLError:
            print "Could not get user information, retrying in %d seconds..." % timer
            time.sleep(timer)
            timer *= 2

    return user_info

def github_check_authentication(urls, username, password):
    """
    Checks that username & password is valid.
    """
    _query(urls.api_url, username, password)

def github_add_comment_to_pull_request(urls, username, password, n, comment):
    """
    Adds a 'comment' to the pull request 'n'.

    Currently it needs github username and password (as strings).
    """
    enc_comment = json.dumps(
        {
            "body" : comment
        }
    )
    url = urls.issue_comment_template % n
    response = _query(url, username, password, enc_comment)
    assert response["body"] == comment

def github_list_pull_requests(urls, numbers_only=False):
    """
    Returns the pull requests numbers.

    It returns a tuple of (nonmergeable, mergeable), where "nonmergeable"
    and "mergeable" are lists of the pull requests numbers.
    """
    pulls = github_get_pull_request_all(urls)
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

def github_authenticate(urls, user, password):
    def get_password(password=None):
        while True:
            if password:
                try:
                    print "> Checking username and password ..."
                    github_check_authentication(urls, username, password)
                except AuthenticationFailed:
                    print ">     Authentication failed."
                else:
                    print ">     OK."
                    return password
            password = getpass("Password: ")

    if user:
        username = user
        print "> Authenticating as %s" % username
    else:
        print _login_message
        username = raw_input("Username: ")

    if password:
        password = get_password(password)
    else:
        password = get_password()

    return username, password

def _query(url, username="", password="", data=""):
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
        http_response = urllib2.urlopen(request)
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
