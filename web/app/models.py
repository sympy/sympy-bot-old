from google.appengine.ext import db

class User(db.Model):
    login = db.StringProperty(required=True)
    id = db.IntegerProperty()
    url = db.StringProperty()
    gravatar_url = db.StringProperty()
    name = db.StringProperty()
    email = db.StringProperty()

class PullRequest(db.Model):
    num = db.IntegerProperty(required=True)
    url = db.StringProperty()
    state = db.StringProperty()
    title = db.StringProperty()
    body = db.TextProperty()
    last_updated = db.DateTimeProperty(auto_now=True)
    repo = db.StringProperty()
    branch = db.StringProperty()
    author = db.ReferenceProperty(User)
    mergeable = db.BooleanProperty()
    created_at = db.DateTimeProperty()

class Task(db.Model):
    pullrequest = db.ReferenceProperty(PullRequest)
    result = db.StringProperty()
    log = db.TextProperty()
    interpreter = db.StringProperty()
    testcommand = db.StringProperty()
    uploaded_at = db.DateTimeProperty(auto_now_add=True)
