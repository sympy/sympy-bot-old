import os
from datetime import datetime
import logging
import sys
import traceback
from random import random

from google.appengine.dist import use_library
use_library("django", "1.2")

from django.utils import simplejson as json

from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext.webapp import template

from jsonrpc_client import JSONRPCService, JSONRPCError
from jsonrpc_server import JSONRPCServer
from models import PullRequest, Task
from github import github_get_pull_request_all
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
        if 0:
            # Generate some data for development:
            p = PullRequest(num=int(random()*1000), url="http://dev-server/")
            p.put()
            t = Task(pullrequest=p)
            t.result = "Passed"
            t.interpreter = "python"
            t.testcommand = "./setup.py test"
            t.log = """Some log\n====\n XXX\n OK\n"""
            t.put()
            t = Task(pullrequest=p)
            t.result = "Failed"
            t.interpreter = "python3"
            t.testcommand = "./setup.py test"
            t.log = """Some log\n====\n XXX\n Tests failed\n"""
            t.put()
        q = PullRequest.all()
        q.order("-last_updated")
        p = q.get()
        if p is None:
            last_update = None
            last_update_pretty = "never"
        else:
            last_update = p.last_updated
            last_update_pretty = pretty_date(last_update)
        self.render("index.html", {"pullrequests": PullRequest.all(),
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
        data = github_get_pull_request_all("sympy/sympy")
        for pull in data['pulls']:
            num = pull['number']
            url = pull['html_url']
            repo = pull['head']['repository']['url']
            branch = pull['head']['ref']
            author_name = pull["user"].get("name", "")
            author_email = pull["user"].get("email", "")
            mergeable = pull["mergeable"]
            created_at = pull["created_at"]
            created_at = datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%SZ")
            # Get the old entity or create a new one:
            p = PullRequest.all()
            p.filter("num =", int(num))
            p = p.get()
            if p is None:
                p = PullRequest(num=num)
            # Update all data from GitHub:
            p.num = num
            p.url = url
            p.repo = repo
            p.branch = branch
            p.author_name = author_name
            p.author_email = author_email
            p.mergeable = mergeable
            p.created_at = created_at
            p.put()
        self.redirect("/")

def main():
    urls =  [
        ('/', MainPage),
        ('/async/?', AsyncHandler),
        ('/pullrequest/(\d+)/?', PullRequestPage),
        ('/report/(.*)/?', ReportPage),
        ('/update/?', UpdatePage),
    ]
    application = webapp.WSGIApplication(urls, debug=True)
    run_wsgi_app(application)
