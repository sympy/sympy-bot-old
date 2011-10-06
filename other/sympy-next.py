#! /usr/bin/env python

# Tool to aggeregrate several branches, automatically merge them (if possible)
# and create statistics about unit tests.
#
# usage: sympy-next.py <options>
#        --help            -h  This message
#        --verbose         -v  Enable verbose output
#        --no-test         -n  Only recreate output
#        --stamp=name      -s  Identifier for this run [generated from date]
#        --logfile=name    -l  Name of logfile
#        --branchfile=file -b  File to get branches from
#        --outdir=dir      -o  Where to create output
#        --command=cmd     -c  Command to run for testing
#        --repo=dir        -r  Repository to use for testing
#
# TODO
#  o Html output, and output creation, are ugly.
#  o At some stage pruning reports, or at least not showing everything, is
#    probably helpful.
#  o Ordering of output is not necessarily very sensible.

import sys
import os
import re
import time
import subprocess
import pickle
import shutil
from optparse import OptionParser

picklef = "reports"
verbose = None
command = None
translate = None
interpreter = None
log = None

def logit(message):
    print >> log, '>', message
    log.flush()
    if verbose:
        print '>', message

def read_branchfile(f):
    ret = []
    with open(f) as fd:
        for line in fd:
            src, branch = line.split()
            ret.append((src, branch))

    return ret

def run_tests():
    cmd = [interpreter] + command
    logit("Running unit tests.")
    logit("Command: " + ' '.join(cmd))
    out = subprocess.Popen(cmd, stdout=subprocess.PIPE).stdout

    report = []
    def my_join(file):
        while True:
            char = file.read(1)
            if not char:
                break
            log.write(char)
            log.flush()
            if verbose:
                sys.stdout.write(char)
            yield char
    def my_split(iter):
        buf = ''
        for c in iter:
            buf += c
            splits = ['sympy/', 'doc/']
            for s in splits:
                if buf.endswith(s):
                    r = buf[:-len(s)]
                    buf = s
                    yield r
        yield buf

    for line in my_split(my_join(out)):
        good = None
        if line.find('[OK]') != -1:
            good = True
        elif line.find('[FAIL]') != -1:
            good = False
        elif re.search('     \[\d*\]', line):
            good = False
        if good is None:
            continue
        report.append((line.split('[')[0].split()[0], good))

    return report

py3k = "sympy-py3k"

def pre_python3():
    if translate:
        logit("Translating to Python 3 ... (this may take a few minutes)")

        if subprocess.call([interpreter, "bin/use2to3"], stdout=log, stderr=log) != 0:
            raise RuntimeError("Can't translate to Python 3.")

        logit("Entering %s" % py3k)
        os.chdir(py3k)

def post_python3():
    if translate:
        logit("Leaving %s" % py3k)
        os.chdir("..")
        logit("Removing %s" % py3k)
        shutil.rmtree(py3k, True)

def do_test(branches, name):
    def git(message, *args):
        logit("%s: git %s" % (message, ' '.join(args)))
        return subprocess.call(("git",) + args, stdout=log, stderr=log)
    def gitn(message, *args):
        if git(message, *args) != 0:
            raise RuntimeError('%s failed' % message)

    # first pull the main branch
    gitn("checkout master", "checkout", "master")
    gitn("reset tree", "reset", "--hard")
    gitn("pull master", "pull", branches[0][0], branches[0][1])

    todo = branches[1:]
    report = []
    tests = []

    i = 0
    while len(todo):
        if git("switch to temporary branch", "checkout", "-b", name):
            logit("Stale test branch?")
            gitn("delete stale temporary branch", "branch", "-D", name)
            gitn("switch to temporary branch", "checkout", "-b", name)

        # now try and fetch all other branches
        first = True
        cantest = False
        br = todo[:]
        todo = []
        for source, branch in br:
            logit("Merging branch %s from %s." % (branch, source))
            if git("Fetching branch " + branch, "fetch", source, branch):
                logit("Error fetching branch -- skipping.")
                report.append((source, branch, "fetch", None))
                continue
            if git("Merge branch " + branch, "merge", "FETCH_HEAD"):
                gitn("Error merging branch %s. See log for merge conflicts." % branch, "diff")
                gitn("Skipping...", "merge", "--abort")
                if first:
                    logit('Cannot merge into master -- dropping.')
                    report.append((source, branch, "merge", None))
                else:
                    todo.append((source, branch))
                continue
            first = False
            cantest = True
            report.append((source, branch, "clean", i))

        # run the tests
        if cantest:
            pre_python3()
            tests.append(run_tests())
            post_python3()
        else:
            assert len(todo) == 0

        # delete our temporary branch
        gitn("switch back to master", "checkout", "master")
        gitn("delete temporary branch", "branch", "-D", name)

        # increment counter
        i += 1

    return report, tests

def write_report(reports):
    # create a html report
    allbranches = set()
    alltests    = set()
    for t in reports:
        for u in t[1]:
            allbranches.update([(u[0], u[1])])
        for u in t[2]:
            for v in u:
                alltests.update([v[0]])

    branchtable = {}
    testtable   = {}
    for branch in allbranches:
        branchtable[branch] = {}
    for test in alltests:
        testtable[test] = {}

    stampnums = {}
    for stamp, branches, tests in reports:
        for b1, b2, status, info in branches:
            branchtable[(b1, b2)][stamp] = (status, info)
        info = 0
        for l in tests:
            for test, status in l:
                testtable[test][(stamp, info)] = status
            info += 1
        stampnums[stamp] = info

    outf = open('report.html', 'w')
    outf.write('''
    <!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN"
           "http://www.w3.org/TR/html4/loose.dtd">
    <html>
    <head>
    <title>sympy-next</title>
    </head>
    <body>
    ''')

    outf.write('<h1> Merge Report </h1>\n')
    outf.write('<table border="1">\n')
    outf.write('  <tr>\n')
    outf.write('    <th> </th>\n')
    for stamp in stampnums:
        outf.write('    <th> %s </th\n' % stamp)
    outf.write('  </tr>\n')
    for name, branch in sorted(branchtable.iteritems()):
        outf.write('  <tr>\n')
        outf.write('    <th align="left"> %s %s </th>\n' % (name[0], name[1]))
        for stamp in stampnums:
            if stamp in branch:
                status, info = branch[stamp]
                if status == 'clean':
                    outf.write('    <td align="center" bgcolor="#00FF00"> clean %d </td>\n' % info)
                elif status == 'merge':
                    outf.write('    <td align="center" bgcolor="#FF0000"> conflicts </td>\n')
                else:
                    outf.write('    <td align="center" bgcolor="#FFFF00"> fetch </td>\n')
            else:
                outf.write('    <th> N/A </th>\n')
        outf.write('  </tr>\n')
    outf.write('</table>\n')

    # filter the reports into test/doctest/documentation test
    tests = {}
    doctests = {}
    documentation = {}
    for name, test in testtable.iteritems():
        if name.find('tests/') != -1:
            tests[name] = test
        elif name.find('doc/') != -1:
            documentation[name] = test
        else:
            doctests[name] = test

    # create a summary
    outf.write('<h1> Test Report Summary </h1>\n')
    outf.write('<table border="1">\n')
    outf.write('  <tr>\n')
    outf.write('    <th> </th>\n')
    for i in ['tests', 'doctests', 'documentation']:
        outf.write('<th> %s </th>\n' % i)
    outf.write('  </tr>\n')
    for stamp, num in stampnums.iteritems():
        for i in range(num):
            outf.write('<tr>\n')
            outf.write('    <th> %s-%d </th>\n' % (stamp, i))
            for table in [tests, doctests, documentation]:
                fail = 0
                for _, test in table.iteritems():
                    if (stamp, i) in test and not test[(stamp, i)]:
                        fail += 1
                if fail == 0:
                    outf.write('<td align="center" bgcolor="#00FF00"> OK </td>\n')
                else:
                    outf.write('<td align="center" bgcolor="#FF0000"> FAIL %d </td>\n' % fail)
            outf.write('</tr>\n')
    outf.write('</table>')

    # print all test reports
    for table, tname in [(tests, 'Test'), (doctests, 'Doctest'),
                         (documentation, 'Documentation Test')]:
        outf.write('<h1> %s Report </h1>\n' % tname)
        outf.write('<table border="1">\n')
        outf.write('  <tr>\n')
        outf.write('    <th> </th>\n')
        for stamp, num in stampnums.iteritems():
            for i in range(num):
                outf.write('    <th> %s-%d </th\n' % (stamp, i))
        outf.write('  </tr>\n')
        for name, test in sorted(table.iteritems()):
            outf.write('  <tr>\n')
            outf.write('    <th align="left"> %s </th>\n' % name)
            for stamp, num in stampnums.iteritems():
                for i in range(num):
                    if (stamp, i) in test:
                        if test[(stamp, i)]:
                            outf.write('<td align="center" bgcolor="#00FF00"> OK </td>\n')
                        else:
                            outf.write('<td align="center" bgcolor="#FF0000"> FAIL </td>\n')
                    else:
                        outf.write('    <td align="center"> N/A </td>\n')
            outf.write('  </tr>\n')
        outf.write('</table>\n')

    # Finally dump the log
    outf.write('<h1> Latest Log </h1>\n')
    outf.write('<pre>\n')
    log.seek(0)
    outf.write(log.read())
    outf.write('</pre>')

    outf.write('</body></html>')

def create_report(merges, tests, stamp):
    # load old reports
    reports = []
    if os.path.exists(picklef):
        f = open(picklef, "rb")
        reports = pickle.load(f)
        f.close()

    reports.append((stamp, merges, tests))

    # dump all reports
    f = open(picklef, "wb")
    pickle.dump(reports, f)
    f.close()

    write_report(reports)

def get_python_version(options):
    cmd = [options.interpreter, "-c", "import sys; sys.stdout.write(str(sys.version_info[:2]))"]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output, _ = proc.communicate()

    if proc.returncode == 0:
        match = re.match("\((\d+), (\d+)\)", output)

        if match is not None:
            major, minor = match.groups()
            return int(major), int(minor)

    raise RuntimeError("unable to run '%s'" % options.interpreter)

# MAIN PROGRAM

def main():
    parser = OptionParser()

    parser.add_option("-v", "--verbose",
        action="store_true", default=False, dest="verbose",
        help="Enable verbose output")
    parser.add_option("-n", "--no-test",
        action="store_true", default=False, dest="no_test",
        help="Only recreate output")
    parser.add_option("-s", "--stamp",
        action="store", type="str", default=None, dest="stamp",
        help="Identifier for this run")
    parser.add_option("-l", "--logfile",
        action="store", type="str", default=None, dest="logfile",
        help="Name of logfile")
    parser.add_option("-b", "--branchfile",
        action="store", type="str", default=None, dest="branchfile",
        help="File to get branches from")
    parser.add_option("-o", "--outdir",
        action="store", type="str", default=None, dest="outdir",
        help="Where to create output")
    parser.add_option("-c", "--command",
        action="store", type="str", default=None, dest="command",
        help="Command to run tests with")
    parser.add_option("-i", "--interpreter",
        action="store", type="str", default=None, dest="interpreter",
        help="Python interpreter to run test with")
    parser.add_option("-r", "--repo",
        action="store", type="str", default=None, dest="repo",
        help="Repository to use for testing")

    options, args = parser.parse_args()

    if options.command is not None:
        options.command = options.command.split()
    else:
        options.command = ['setup.py', 'test']

    if options.interpreter is None:
        options.interpreter = 'python'

    major, _ = get_python_version(options)

    if options.outdir is not None:
        options.outdir = os.path.abspath(options.outdir)
    else:
        print 'You have to specify an output directory.'
        sys.exit(1)

    if options.stamp is None:
        # create us a timestamp
        tm = time.localtime(time.time())
        options.stamp = "%s%s%s%s%s" % (tm.tm_year, tm.tm_mon,
                                        tm.tm_mday, tm.tm_hour, tm.tm_min)

    if options.logfile is None:
        options.logfile = options.stamp

    # create output directory if necessary
    if not os.path.exists(options.outdir):
        os.mkdir(options.outdir)

    # we will log all output to here
    global log
    log = open(os.path.join(options.outdir, options.logfile), 'w+')

    # TODO: rewrite all this code as a class
    global verbose
    verbose = options.verbose
    global command
    command = options.command
    global interpreter
    interpreter = options.interpreter
    global translate
    translate = (major == 3)

    if options.no_test:
        os.chdir(options.outdir)
        write_report(pickle.load(open(picklef, 'rb')))
        sys.exit(0)

    if options.branchfile is not None:
        options.branchfile = os.path.abspath(options.branchfile)
    else:
        print "You have to specify a branchfile."
        sys.exit(1)

    if options.repo is not None:
        options.repo = os.path.abspath(options.repo)
    else:
        print "You have to specify a repo."
        sys.exit(1)

    # find out which branches to test
    branches = read_branchfile(options.branchfile)

    # do the merging and testing
    os.chdir(options.repo)
    merges, tests = do_test(branches, "next-test")

    # create a report
    os.chdir(options.outdir)
    create_report(merges, tests, options.stamp)

if __name__ == '__main__':
    main()
