import base64
import json
import sys
import time
import urllib2
import os
import ConfigParser
from getpass import getpass

from utils.cmd import keep_trying

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
            "scopes": ["public_repo"],
            "note": name
        }
    )

    url = urls.authorize_url
    rep = _query(url, data=enc_data, username=username, password=password)
    return rep["token"]


def github_get_pull_request_all(urls):
    """
    Returns all github pull requests.
    """
    return keep_trying(lambda: _query(urls.pull_list_url), urllib2.URLError,
                       "get list of all pull requests")

def github_get_pull_request(urls, n):
    """
    Returns pull request 'n'.
    """
    url = urls.single_pull_template % n
    issue_url = urls.single_issue_template % n

    def _check_issue(e):
        """
        It's possible the "pull request" is really an issue. If it is, the
        issue url will exist.
        """
        try:
            issue = _query(issue_url)
        except urllib2.URLError:
            pass
        else:
            print ("Pull request %d appears to be an issue "
                   "(no code is attached). Skipping..." % n)
            return False

    return keep_trying(lambda: _query(url), urllib2.URLError,
                       "get pull request %d" % n, _check_issue)

def github_get_user_info(urls, user):
    url = urls.user_info_template % user
    return keep_trying(lambda: _query(url), urllib2.URLError, "get user information")

def github_get_user_repos(urls, user):
    url = urls.user_repos_template % user
    return keep_trying(lambda: _query(url), urllib2.URLError, "get user repository information")

def github_check_authentication(urls, username, password, token):
    """
    Checks that username & password is valid.
    """
    _query(urls.api_url, None, username=username, password=password, token=token)


def github_add_comment_to_pull_request(urls, n, comment):
    """
    Adds a 'comment' to the pull request 'n'.
    """
    enc_comment = json.dumps(
        {
            "body": comment
        }
    )
    url = urls.issue_comment_template % n
    response = _query(url, enc_comment)
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
        if not pull_info:
            # Pull request is an issue
            continue
        mergeable = pull_info["mergeable"]
        if pull["head"]["repo"]:
            repo = pull["head"]["repo"]["html_url"]
        else:
            repo = None
        branch = pull["head"]["ref"]
        created_at = pull["created_at"]
        created_at = time.strptime(created_at, "%Y-%m-%dT%H:%M:%SZ")
        created_at = time.mktime(created_at)
        user = pull["user"]["login"]
        user_info = github_get_user_info(urls, user)
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
        if pull['mergeable']:
            continue
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
        if not pull['mergeable']:
            continue
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
        url = l[1:i - 1]
        assert l[i - 1] == ">"
        assert l[i + 1:i + 7] == ' rel="'
        j = l.find('"', i + 7)
        assert j != -1
        param = l[i + 7:j]
        d[param] = url

        if len(l) == j + 1:
            break
        assert l[j + 1] == ","
        j += 2
        l = l[j + 1:]
    return d


def _query(url, data="", **kwargs):
    """
    Query github API,
    if username and password are presented, then the query is executed from the user account

    In case of a multipage result, query the next page and return all results.
    """
    username = kwargs.get("username", None)
    password = kwargs.get("password", None)
    token = kwargs.get("token", None)

    if not ((username and password) or (username and token)):
        conf_file = load_conf_file()
        username = conf_file.get("user", None)
        token = conf_file.get("token", None)

        if not token:
            token_path = conf_file.get("token_file", None)
            if token_path:
                token = load_token(token_path)

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
        response_body.extend(_query(nexturl, data, username=username, password=password, token=token))

    return response_body

def load_conf_file(**kwargs):
    profile = kwargs.get("profile", None);
    default_section = "DEFAULT"
    conf_file = os.path.normpath("~/.sympy/sympy-bot.conf")  #Set to default config path
    conf_file = os.path.expanduser(conf_file)

    parser = ConfigParser.SafeConfigParser()
    default_items = {}
    if os.path.exists(conf_file):
        if profile is not None:
            print "> Using config file %s" % conf_file
        with open(conf_file) as f:
            try:
                parser.readfp(f)
            except IOError as e:
                if profile is not None:
                    print "> WARNING: Unable to open config file:", e
            except ConfigParser.Error as e:
                if profile is not None:
                    print "> WARNING: Unable to parse config file:", e
            else:
                if profile is not None:
                    print "> Loaded configuration file"

                # Try to get default items, as the following will not be true:
                # parser.has_section("DEFAULT")
                try:
                    default_items = dict(parser.items(default_section, raw=True))
                except ConfigParser.NoSectionError:
                    pass

                if profile is not None:
                    if profile.upper() == default_section:
                        items = default_items
                    elif parser.has_section(profile):
                        items = dict(parser.items(profile, vars=default_items))
                    else:
                        raise ConfigParser.Error("Configuration file does not contain profile: %s" % profile)

                    return items
    return default_items

def load_token(path):
    token = None
    if path is None:
        return token
    path = os.path.expanduser(path)
    path = os.path.abspath(path)
    if os.path.isfile(path):
        try:
            with open(path) as f:
                token = f.readline()
                token = token.strip()
        except IOError as e:
            print "Unable to open token file:", e
    return token
