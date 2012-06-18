class URLs(object):
    """
    This class contains URLs and templates which used in requests to GitHub API
    """

    def __init__(self, user="sympy", repo="sympy", api_url="https://api.github.com"):
        """ Generates all URLs and templates """

        self.user = user
        self.repo = repo
        self.api_url = api_url

        self.pull_list_url = api_url + "/repos" + "/" + user + "/" + repo + "/pulls" 
        self.single_pull_template = self.pull_list_url + "/%d"
        self.user_info_template = api_url + "/users/%s"
        self.issue_comment_template = \
            api_url + "/repos" + "/" + user + "/" + repo + "/issues/%d" + "/comments"
