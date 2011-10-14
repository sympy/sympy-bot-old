import os
from datetime import datetime
import logging
import sys
import traceback
from random import random

from google.appengine.dist import use_library
use_library("django", "1.2")

from django.utils import simplejson as json

from google.appengine.ext import webapp, db
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext.webapp import template
from google.appengine.api import taskqueue

from jsonrpc_client import JSONRPCService, JSONRPCError
from jsonrpc_server import JSONRPCServer
from models import PullRequest, Task
from github import (github_get_pull_request_all_v2,
        github_get_pull_request_all_v3, github_get_pull_request)
from utils import pretty_date

dev_server = os.environ["SERVER_SOFTWARE"].startswith("Development")
if dev_server:
    url_base = "http://localhost:8080"
else:
    url_base = "http://reviews.sympy.org"

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
        q.order("-last_updated")
        p = q.get()
        if p is None:
            last_update = None
            last_update_pretty = "never"
        else:
            last_update = p.last_updated
            last_update_pretty = pretty_date(last_update)
        p_mergeable = PullRequest.all()
        p_mergeable.filter("mergeable =", True)
        p_mergeable.order("-created_at")
        p_nonmergeable = PullRequest.all()
        p_nonmergeable.filter("mergeable =", False)
        p_nonmergeable.order("-created_at")
        self.render("index.html", {
            "pullrequests_mergeable": p_mergeable,
            "pullrequests_nonmergeable": p_nonmergeable,
            "last_update": last_update,
            "last_update_pretty": last_update_pretty})

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

class UpdatePage(RequestHandler):
    def get(self):
        data = github_get_pull_request_all_v3("sympy/sympy")
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
            p.author_name = pull["user"].get("name", "")
            p.author_email = pull["user"].get("email", "")
            created_at = pull["created_at"]
            created_at = datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%SZ")
            p.created_at = created_at
            p.put()
            # Update the rest with a specific query to the pull request:
            taskqueue.add(url="/worker", params={"type": "pullrequest",
                "num": num})
        self.redirect("/")

class Worker(webapp.RequestHandler):

    def post(self):
        _type = self.request.get("type")
        _num = int(self.request.get("num"))
        def txn():
            assert _type == "pullrequest"
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
            p.repo = pull['head']['repo']['url']
            p.branch = pull['head']['ref']
            p.author_name = pull["user"].get("name", "")
            p.author_email = pull["user"].get("email", "")
            created_at = pull["created_at"]
            created_at = datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%SZ")
            p.created_at = created_at
            p.put()
        # This raises:
        #BadRequestError: Only ancestor queries are allowed inside transactions.
        #db.run_in_transaction(txn)
        txn()

def main():
    urls =  [
        ('/', MainPage),
        ('/async/?', AsyncHandler),
        ('/pullrequest/(\d+)/?', PullRequestPage),
        ('/report/(.*)/?', ReportPage),
        ('/update/?', UpdatePage),
        ('/worker/?', Worker),
    ]
    application = webapp.WSGIApplication(urls, debug=True)
    run_wsgi_app(application)
