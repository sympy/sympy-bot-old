# This file contains predefined values for communicating with GitHub
# If you want to run bot on another repo, then replace "gh_user" and "gh_repo" with
# yours values
gh_api_url = "https://api.github.com"
gh_user = "sympy"
gh_repo = "sympy"
gh_pull_list_url = gh_api_url + "/repos" + "/" + gh_user + "/" + gh_repo + "/pulls" 
gh_pull_template = gh_pull_list_url + "/%d"
gh_user_info_template = gh_api_url + "/users/%s"
gh_issue_comment_template = gh_api_url + "/repos" + "/" + gh_user + "/" + gh_repo + \
                            "/issues/%d" + "/comments"
