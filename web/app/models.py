from google.appengine.ext import db

class PullRequest(db.Model):
    num = db.IntegerProperty(required=True)
    url = db.StringProperty()
    last_updated = db.DateTimeProperty(auto_now=True)
    repo = db.StringProperty()
    branch = db.StringProperty()
    author_name = db.StringProperty()
    author_email = db.StringProperty()
    mergeable = db.BooleanProperty()
    created_at = db.DateTimeProperty()

class Task(db.Model):
    pullrequest = db.ReferenceProperty(PullRequest)
    result = db.StringProperty()
    log = db.TextProperty()
    interpreter = db.StringProperty()
    testcommand = db.StringProperty()
    uploaded_at = db.DateTimeProperty(auto_now_add=True)
