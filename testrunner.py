import sys
import re
import subprocess

from utils import cmd, cmd2, CmdException, get_xpassed_info_from_log

def run_tests(master_repo_url, pull_request_repo_url, pull_request_branch,
        master_repo_path, test_command, interpreter, python3, master_commit):
    """
    This is a test runner function.

    It doesn't access any global variables. It assumes that the master
    repository is checked out at 'master_repo_path' (for example in the /tmp
    directory somewhere). It does the following:

    1) fetches the 'pull_request_branch' from 'pull_request_repo_url' and tries
    to apply it

    2) runs tests using 'test_command' and the Python 'interpreter'.

    3) saves report and logs into the out/ directory.

    4) Returns status, which is one of the following strings:

        error .. there was an error
        fetch ... fetch failed (no tests run)
        conflicts ... there were merge conflicts (no tests run)
        FAILED ... tests run, but failed
        PASSED ... tests run, passed

    """
    result = {
            "log": "",
            "xpassed": "",
            "master_hash": "",
            "branch_hash": "",
        }
    print "Running tests with the following setup:"
    print "master_repo_url =", master_repo_url
    print "pull_request_repo_url =", pull_request_repo_url
    print "pull_request_branch =", pull_request_branch
    print "master_repo_path =", master_repo_path
    print "test_command =", test_command
    print "interpreter =", interpreter
    try:
        cmd("cd %s; git fetch %s %s:test" % (master_repo_path,
            pull_request_repo_url, pull_request_branch), echo=True)
    except CmdException:
        result["result"] = "fetch"
        return result
    cmd("cd %s; git checkout test" % master_repo_path, echo=True)
    # remember the hashes before the merge occurs:
    try:
        result["master_hash"] = cmd("cd %s; git rev-parse %s" % (master_repo_path,
            master_commit), capture=True).strip()
    except CmdException:
        print "Could not parse commit %s." % master_commit
        result["result"]= "error"
        return result
    result["branch_hash"] = cmd("cd %s; git rev-parse test" % master_repo_path,
            capture=True).strip()

    try:
        cmd("cd %s; git merge %s" % (master_repo_path, master_commit),
            echo=True)
    except CmdException:
        result["result"] = "conflicts"
        return result
    if python3:
        cmd("cd %s; bin/use2to3" % master_repo_path)
        master_repo_path = master_repo_path + "/py3k-sympy"
    log, r = cmd2("cd %s; %s %s" % (master_repo_path,
        interpreter, test_command))
    result["log"] = log
    result["return_code"] = r


    result["xpassed"] = get_xpassed_info_from_log(log)
    print "Return code:", r
    if r == 0:
        result["result"] = "Passed"
    else:
        result["result"] = "Failed"
    return result
