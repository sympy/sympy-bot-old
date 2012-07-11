import os
from datetime import datetime
import logging
import sys
import traceback
from random import random
import urllib2

from google.appengine.dist import use_library
use_library("django", "1.2")

from django.utils import simplejson as json

from google.appengine.ext import webapp, db
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext.webapp import template
from google.appengine.api import taskqueue

from jsonrpc_client import JSONRPCService, JSONRPCError
from jsonrpc_server import JSONRPCServer
from models import PullRequest, Task, User, UploadURL
from github import (github_get_pull_request_all_v2,
        github_get_pull_request_all_v3, github_get_pull_request,
        github_get_user)
from utils import pretty_date

dev_server = os.environ["SERVER_SOFTWARE"].startswith("Development")
if dev_server:
    url_base = "http://localhost:8080"
else:
    url_base = "http://reviews.sympy.org"

# default github user and repo
polled_user = "sympy"
polled_repo = "sympy"

class RequestHandler(webapp.RequestHandler):

    def render(self, temp, data=None):
        """
        Renders the template "temp" with data 'data'.

        Handles default data fields, as well as path to the templates.
        """
        name, _ = os.path.splitext(temp)
        d = {
                'dev_server': dev_server,
                name + '_selected': "selected",
            }
        if data is not None:
            d.update(data)
        path = os.path.join(os.path.dirname(__file__), "..", "templates", temp)
        s = template.render(path, d)
        self.response.out.write(s)

class MainPage(RequestHandler):
    def get(self):
        q = PullRequest.all()
        q.order("last_updated")
        # This is the request that wasn't updated for the longest time:
        p = q.get()
        if p is None:
            last_update = None
            last_update_pretty = "never"
        else:
            last_update = p.last_updated
            last_update_pretty = pretty_date(last_update)
        q = PullRequest.all()
        q.filter("state =", "open")
        q.order("last_updated")
        # This is the open request that wasn't updated for the longest time:
        p = q.get()
        if p is None:
            last_quick_update = None
            last_quick_update_pretty = "never"
        else:
            last_quick_update = p.last_updated
            last_quick_update_pretty = pretty_date(last_quick_update)
        p_mergeable = PullRequest.all()
        p_mergeable.filter("mergeable =", True)
        p_mergeable.filter("state =", "open")
        p_mergeable.order("-created_at")
        p_nonmergeable = PullRequest.all()
        p_nonmergeable.filter("mergeable =", False)
        p_nonmergeable.filter("state =", "open")
        p_nonmergeable.order("-created_at")
        self.render("index.html", {
            "pullrequests_mergeable": p_mergeable,
            "pullrequests_nonmergeable": p_nonmergeable,
            "last_update": last_update,
            "last_update_pretty": last_update_pretty,
            "last_quick_update": last_quick_update,
            "last_quick_update_pretty": last_quick_update_pretty,
            })

class ClosedPullRequestsPage(RequestHandler):
    def get(self):
        p_closed = PullRequest.all()
        p_closed.filter("state =", "closed")
        p_closed.order("-created_at")
        self.render("closed_pullrequests.html", {
            "pullrequests_closed": p_closed,
            })

class PullRequestPage(RequestHandler):
    def get(self, num):
        p = PullRequest.all()
        p.filter("num =", int(num))
        p = p.get()
        t = p.task_set
        t.order("uploaded_at")
        self.render("pullrequest.html", {'p': p, 'tasks': t})

class ReportPage(RequestHandler):
    def get(self, id):
        t = Task.get(id)
        logging.info(t.log)
        self.render("report.html", {'task': t})

class AsyncHandler(webapp.RequestHandler):
    def get(self):
        self.response.out.write("AsyncHandler.")

    def post(self):
        def upload_task(num, result, interpreter, testcommand, log):
            p = PullRequest.all()
            p.filter("num =", int(num))
            p = p.get()
            if p is None:
                # Create the pull request:
                p = PullRequest(num=num)
                p.put()
            t = Task(pullrequest=p)
            t.result = result
            t.interpreter = interpreter
            t.testcommand = testcommand
            t.log = log
            t.put()
            result = {
                "ok": True,
                "task_url": "%s/report/%s" % (url_base, t.key())
                }
            return result

        s = JSONRPCServer({
            "RPC.upload_task": upload_task,
            })
        output = s.handle_request_from_client(self.request.body)
        self.response.out.write(output)

class UpdateBase(RequestHandler):
    def update(self, full=False):
        data = github_get_pull_request_all_v3("sympy/sympy")
        if full:
            data += github_get_pull_request_all_v3("sympy/sympy", "closed")
        p = PullRequest.all()
        p.filter("state =", "open")
        open_list = [x.num for x in p]
        for pull in data:
            num = pull["number"]
            # Get the old entity or create a new one:
            p = PullRequest.all()
            p.filter("num =", int(num))
            p = p.get()
            if p is None:
                p = PullRequest(num=num)
            # Update all data that we can from GitHub:
            p.url = pull['html_url']
            p.state = pull["state"]
            p.title = pull["title"]
            p.body = pull["body"]
            created_at = pull["created_at"]
            created_at = datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%SZ")
            p.created_at = created_at

            u = User.all()
            u.filter("login =", pull["user"]["login"])
            u = u.get()
            if u is None:
                u = User(login=pull["user"]["login"])
                u.put()
            p.author = u

            p.put()
            # Update the rest with a specific query to the pull request:
            if num not in open_list:
                # open_list pull requests will be updated below
                taskqueue.add(url="/worker", queue_name="github",
                        params={"type": "pullrequest", "num": num})
        for num in open_list:
            taskqueue.add(url="/worker", queue_name="github",
                    params={"type": "pullrequest", "num": num})
        if full:
            for u in User.all():
                taskqueue.add(url="/worker", queue_name="github",
                        params={"type": "user", "login": u.login})

class UpdatePage(UpdateBase):
    def get(self):
        self.update(full=True)
        self.response.out.write("OK")

class QuickUpdatePage(UpdateBase):
    def get(self):
        self.update(full=False)
        self.response.out.write("OK")

class Worker(webapp.RequestHandler):

    def post(self):
        _type = self.request.get("type")
        def txn():
            assert _type == "pullrequest"
            _num = int(self.request.get("num"))
            pull = github_get_pull_request("sympy/sympy", _num)
            p = PullRequest.all()
            p.filter("num =", int(_num))
            p = p.get()
            if p is None:
                p = PullRequest(num=_num)
            p.url = pull['html_url']
            p.state = pull["state"]
            p.title = pull["title"]
            p.body = pull["body"]
            p.mergeable = pull["mergeable"]
            if pull['head']['repo']:
                p.repo = pull['head']['repo']['url']
            p.branch = pull['head']['ref']
            p.author_name = pull["user"].get("name", "")
            p.author_email = pull["user"].get("email", "")
            created_at = pull["created_at"]
            created_at = datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%SZ")
            p.created_at = created_at
            p.put()
        def user():
            assert _type == "user"
            login = self.request.get("login")
            data = github_get_user(login)
            u = User.all()
            u.filter("login =", data["login"])
            u = u.get()
            if u is None:
                u = User(login=data["login"])

            u.id = data['id']
            u.avatar_url = data['avatar_url']
            u.url = data['url']
            u.name = data.get("name")
            u.email = data.get("email")
            created_at = data["created_at"]
            created_at = datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%SZ")
            u.created_at = created_at
            u.put()
        # This raises:
        #BadRequestError: Only ancestor queries are allowed inside transactions.
        #db.run_in_transaction(txn)
        if _type == "pullrequest":
            txn()
        elif _type == "user":
            user()
        else:
            raise ValueError("wrong type")

class UploadPull(RequestHandler):

    def post(self, url_path):
        last_row = UploadURL.all().order("-created_at").get()
        if last_row:
            if last_row.url_path == url_path:
                try:
                    payload = json.loads(self.request.get("payload"))
                    logging.info(payload)
                except json.JSONDecodeError:
                    self.error(400)
                    self.response.out.write("Incorrect request format\n")
                user_repo = payload["repository"]["full_name"]
                # Download complete pull request with information about mergeability
                pull_request = github_get_pull_request(user_repo, payload["number"])
                num = payload["number"]
                # Get the old entity or create a new one:
                p = PullRequest.all()
                p.filter("num =", int(num))
                p = p.get()
                if p is None:
                    p = PullRequest(num=num)
                # Update all data that we can from GitHub:
                p.url = pull_request["html_url"]
                p.state = pull_request["state"]
                p.title = pull_request["title"]
                p.body = pull_request["body"]
                p.mergeable = pull_request["mergeable"]
                if pull_request["head"]["repo"]:
                    p.repo = pull_request["head"]["repo"]["url"]
                p.branch = pull_request["head"]["ref"]
                p.author_name = pull_request["user"].get("name", "")
                p.author_email = pull_request["user"].get("email", "")
                created_at = pull_request["created_at"]
                created_at = datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%SZ")
                p.created_at = created_at
                u = User.all()
                u.filter("login =", pull_request["user"]["login"])
                u = u.get()
                if u is None:
                    u = User(login=pull_request["user"]["login"])
                    u.id = pull_request["user"]["id"]
                    u.avatar_url = pull_request["user"]['avatar_url']
                    u.url = pull_request["user"]["url"]
                    u.put()
                p.author = u
                p.put()
            else:
                self.error(404)
                self.response.out.write("Requesting URL doesn't exist\n")
        else:
            self.error(500)
            self.response.out.write("URL for posting data not defined yet\n")

    def get(self, url_path):

        def notify_admins(user, new_url):
            from google.appengine.api.mail import send_mail_to_admins
            mail = user.email()
            subject = "SymPy bot notification"
            body = "New upload URL " + new_url
            send_mail_to_admins(sender=mail, subject=subject, body=body)

        from google.appengine.api import users
        user = users.get_current_user()
        is_admin = users.is_current_user_admin()
        rows = []
        upload_url = ""
        if user:
            if is_admin:
                if self.request.get("generate"):
                    import sha
                    rand_string = os.urandom(10)
                    sha_hash = sha.new(rand_string)
                    new_record = UploadURL(url_path=sha_hash.hexdigest(), user=user.nickname())
                    new_record.put()
                    new_url = self.request.host_url + "/upload_pull/" + \
                              sha_hash.hexdigest()
                    notify_admins(user, new_url)
                if self.request.get("populate"):
                    taskqueue.add(url="/worker-ng", queue_name="github")
                rows = UploadURL.all()
                last_row = rows.order("-created_at").get()
                if last_row:
                    upload_url = (last_row.url_path)
                else:
                    upload_url = ("")

        self.render("upload_url.html", {"user": user,
                                        "upload_url": upload_url,
                                        "is_admin": is_admin,
                                        "rows": rows,
                                        "login_url": users.create_login_url("/upload_pull"),
                                        "logout_url": users.create_logout_url("/upload_pull"),
                                       }
                   )


class WorkerNG(webapp.RequestHandler):
    """
    This class using for populating pull requests database and users
    (calls when admin press "Populate" button)
    """
    def post(self):
        user_repo = polled_user + "/" + polled_repo
        payload = github_get_pull_request_all_v3(user_repo)
        # checkout mergeability
        for pos in xrange(len(payload)):
            pull = github_get_pull_request(user_repo, payload[pos]["number"])
            payload[pos]["mergeable"] = pull["mergeable"]
        # Process each pull request from payload
        for pull in payload:
            p = PullRequest.all()
            num = pull["number"]
            p.filter("num =", num)
            p = p.get()
            if p is None:
                p = PullRequest(num=num)
            p.url = pull["html_url"]
            p.state = pull["state"]
            p.title = pull["title"]
            p.body = pull["body"]
            p.mergeable = pull["mergeable"]
            if pull["head"]["repo"]:
                p.repo = pull["head"]["repo"]["url"]
            p.branch = pull["head"]["ref"]
            created_at = pull["created_at"]
            created_at = datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%SZ")
            p.created_at = created_at

            # Collect public information about user
            u = User.all()
            login = pull["user"]["login"]
            u.filter("login =", login)
            u = u.get()
            if u is None:
                u = User(login=login)
            u.id = pull["user"]["id"]
            u.avatar_url = pull["user"]["avatar_url"]
            u.url = pull["user"]["url"]
            u.put()

            p.author = u
            p.put()


def main():
    urls =  [
        ('/', MainPage),
        ('/closed_pullrequests/?', ClosedPullRequestsPage),
        ('/async/?', AsyncHandler),
        ('/pullrequest/(\d+)/?', PullRequestPage),
        ('/report/(.*)/?', ReportPage),
        ('/update/?', UpdatePage),
        ('/quickupdate/?', QuickUpdatePage),
        ('/worker/?', Worker),
        ('/upload_pull/?(.*)/?', UploadPull),
        ('/worker-ng/?', WorkerNG),
    ]
    application = webapp.WSGIApplication(urls, debug=True)
    run_wsgi_app(application)
