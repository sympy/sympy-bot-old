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

def generate_token(urls, username, password, name="SymPy Bot"):
    enc_data = json.dumps(
        {
            "scopes" : ["repo"],
            "note" : name
            }
    )

    url = urls.authorize_url
    rep = _query(url, username=username, password=password, data=enc_data)
    return rep["token"]

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
            print "Could not get pull request %d, retrying in %d seconds..." % (n, timer)
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

def github_check_authentication(urls, username, password, token):
    """
    Checks that username & password is valid.
    """
    _query(urls.api_url, username, password, token)

def github_add_comment_to_pull_request(urls, username, password, token, n, comment):
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
    response = _query(url, username, password, token, enc_comment)
    assert response["body"] == comment

def github_list_pull_requests(urls, numbers_only=False):
    """
    Returns the pull requests numbers.

    It returns a tuple of (nonmergeable, mergeable), where "nonmergeable"
    and "mergeable" are lists of the pull requests numbers.
    """
    pulls = github_get_pull_request_all(urls)
    formatted_pulls = []
    print "Total pull count", len(pulls)
    sys.stdout.write("Processing pulls...")
    for pull in pulls:
        n = pull["number"]
        sys.stdout.write(" %d" % n)
        sys.stdout.flush()
        pull_info = github_get_pull_request(urls, n)
        mergeable = pull_info["mergeable"]
        if pull["head"]["repo"]:
            repo = pull["head"]["repo"]["html_url"]
        else:
            repo = None
        branch = pull["head"]["ref"]
        created_at = pull["created_at"]
        created_at = time.strptime(created_at, "%Y-%m-%dT%H:%M:%SZ")
        created_at = time.mktime(created_at)
        username = pull["user"]["login"]
        user_info = github_get_user_info(urls, username)
        author = "\"%s\" <%s>" % (user_info.get("name", "unknown"),
                                  user_info.get("email", ""))
        branch_against = pull["base"]["ref"]
        formatted_pulls.append({
            'created_at': created_at,
            'n': n,
            'repo': repo,
            'branch': branch,
            'author': author,
            'mergeable': mergeable,
            'branch_against': branch_against,
        })
    formatted_pulls.sort(key=lambda x: x['created_at'])
    print "\nPatches that cannot be merged without conflicts:"
    nonmergeable = []
    for pull in formatted_pulls:
        if pull['mergeable']: continue
        nonmergeable.append(int(pull['n']))
        if numbers_only:
            print pull['n'],
        else:
            print "#%03d: %s %s (against %s)" % (pull['n'], pull['repo'], pull['branch'], pull['branch_against'])
            print unicode("      Author   : %s" % pull['author']).encode('utf8')
            print "      Date     : %s" % time.ctime(pull['created_at'])
    if numbers_only:
        print
    print
    print "-"*80
    print "Patches that can be merged without conflicts:"
    mergeable_list = []
    for pull in formatted_pulls:
        if not pull['mergeable']: continue
        mergeable_list.append(int(pull['n']))
        if numbers_only:
            print pull['n'],
        else:
            print "#%03d: %s %s (against %s)" % (pull['n'], pull['repo'], pull['branch'], pull['branch_against'])
            print unicode("      Author   : %s" % pull['author']).encode('utf8')
            print "      Date     : %s" % time.ctime(pull['created_at'])
    if numbers_only:
        print
        print
    return nonmergeable, mergeable_list

def github_authenticate(urls, username, token=None):
    if username:
        print "> Authenticating as %s" % username
    else:
        print _login_message
        username = raw_input("Username: ")

    authenticated = False

    if token:
        print "> Authenticating using token"
        try:
            github_check_authentication(urls, username, None, token)
        except AuthenticationFailed:
            print ">     Authentication failed"
        else:
            print ">     OK"
            password = None
            authenticated = True

    while not authenticated:
        password = getpass("Password: ")
        try:
            print "> Checking username and password ..."
            github_check_authentication(urls, username, password, None)
        except AuthenticationFailed:
            print ">     Authentication failed"
        else:
            print ">     OK."
            authenticated = True

    if password:
        generate = raw_input("> Generate API token? [Y/n] ")
        if generate.lower() in ["y", "ye", "yes", ""]:
            name = raw_input("> Name of token on GitHub? [SymPy Bot] ")
            if name == "":
                name = "SymPy Bot"
            token = generate_token(urls, username, password, name=name)

    return username, password, token

def _link2dict(l):
    """
    Converts the GitHub Link header to a dict:

    Example::

    >>> link2dict('<https://api.github.com/repos/sympy/sympy/pulls?page=2&state=closed>; rel="next",  <https://api.github.com/repos/sympy/sympy/pulls?page=21&state=closed>; rel="last"')
    {'last': 'https://api.github.com/repos/sympy/sympy/pulls?page=21&state=closed',  'next': 'https://api.github.com/repos/sympy/sympy/pulls?page=2&state=closed'}

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

def _query(url, username=None, password=None, token=None, data=""):
    """
    Query github API,
    if username and password are presented, then the query is executed from the user account

    In case of a multipage result, query the next page and return all results.
    """
    request = urllib2.Request(url)
    # Add authentication headers to request, if username and password presented
    if username:
        if token:
            request.add_header("Authorization", "bearer %s" % token)
        elif password:
            base64string = base64.encodestring('%s:%s' % (username, password)).replace('\n', '')
            request.add_header("Authorization", "Basic %s" % base64string)
    if data is not "":
        request.add_data(data)
    try:
        http_response = urllib2.urlopen(request)
        response_body = json.load(http_response)
    except urllib2.HTTPError as e:
        # Auth exception
        if e.code == 401:
            raise AuthenticationFailed("invalid username or password")
        # Other exceptions
        raise urllib2.HTTPError(e.filename, e.code, e.msg, None, None)
    except ValueError as e:
        # If auth was successful
        if http_response.code in (204, 302):
            return []
        # else return original error
        raise ValueError(e)

    link = http_response.headers.get("Link")
    nexturl = _link2dict(link).get("next") if link else None
    if nexturl:
        response_body.extend(_query(nexturl, username, password, token, data))

    return response_body
