import os
import sys
import re
import subprocess

from utils.cmd import cmd, cmd2, CmdException

def run_tests(pull_request_repo_url, pull_request_branch, master_repo_path,
              test_command, python3, master_commit, run2to3=True):
    """
    This is a test runner function.

    It doesn't access any global variables. It assumes that the master
    repository is checked out at 'master_repo_path' (for example in the /tmp
    directory somewhere). It does the following:

    1) fetches the 'pull_request_branch' from 'pull_request_repo_url' and tries
    to apply it

    2) runs tests using 'test_command'.

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
        }
    if python3:
        if run2to3:
            use2to3 = os.path.join("bin", "use2to3")
            cmd("python %s" % use2to3, cwd=master_repo_path)
        master_repo_path = os.path.join(master_repo_path, "py3k-sympy")
    log, r = cmd2(test_command, cwd=master_repo_path)
    cmd("git checkout master", cwd=master_repo_path)
    result["log"] = log
    result["return_code"] = r

    result["xpassed"] = get_xpassed_info_from_log(log)
    print "Return code: ", r
    if r == 0:
        result["result"] = "Passed"
    else:
        result["result"] = "Failed"
    return result

def get_xpassed_info_from_log(log):
    re_xpassed = re.compile("\s+_+\s+xpassed tests\s+_+\s+(?P<xpassed>([^\n]+\n)+)\n", re.M)
    m = re_xpassed.search(log)
    if m:
        lines = m.group('xpassed')
        return lines.splitlines()
    return []

def get_hashes(master_repo_path, master_commit, pull_request_number):
    result = {}
    try:
        result["master_hash"] = cmd("git rev-parse %s" % master_commit,
                capture=True, cwd=master_repo_path).strip()
    except CmdException:
        print "Could not parse commit %s." % master_commit
        return None
    result["branch_hash"] = cmd("git rev-parse test_%s" % pull_request_number, capture=True,
            cwd=master_repo_path).strip()
    return result

def merge_branch(pull_request_repo_url, pull_request_branch, master_repo_path,
                 master_commit, pull_request_number):
    result = {
        'result': "",
        'log': "",
    }

    try:
        cmd("git fetch %s %s:test_%s" % (pull_request_repo_url,
            pull_request_branch, pull_request_number), echo=True,
            cwd=master_repo_path)
    except CmdException:
        result["result"] = "fetch"
        return result
    cmd("git checkout test_%s" % pull_request_number, echo=True, cwd=master_repo_path)
    # remember the hashes before the merge occurs:

    merge_log, r = cmd2("git merge %s" % master_commit, cwd=master_repo_path)
    if r != 0:
        conflicts = cmd("git --no-pager diff", capture=True,
                cwd=master_repo_path)
        result["result"] = "conflicts"
        result["log"] = merge_log + "\nLIST OF CONFLICTS\n" + conflicts
        cmd("git merge --abort && git checkout master", cwd=master_repo_path)
    return result
