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
import time
import subprocess
import pickle
import getopt

# options
verbose = False                  # --verbose
picklef = "reports"
command = ['./setup.py', 'test'] # --command

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
    logit("Running unit tests.")
    logit("Command: " + ' '.join(command))
    out = subprocess.Popen(command, stdout=subprocess.PIPE).stdout

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
        import re
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
                gitn("Error merging branch %s -- skipping." % branch,
                     "merge", "--abort")
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
            tests.append(run_tests())
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
    allstamps   = [t[0] for t in reports]
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


# MAIN PROGRAM

def usage(message):
    if None != message:
        print 'error:', message
    print 'usage: %s <options>' % os.path.basename(__file__)
    print '       --help            -h  This message'
    print '       --verbose         -v  Enable verbose output'
    print '       --no-test         -n  Only recreate output'
    print '       --stamp=name      -s  Identifier for this run [generated from date]'
    print '       --logfile=name    -l  Name of logfile'
    print '       --branchfile=file -b  File to get branches from'
    print '       --outdir=dir      -o  Where to create output'
    print '       --command=cmd     -c  Command to run for testing'
    print '       --repo=dir        -r  Repository to use for testing'
    sys.exit(1)

if __name__ == '__main__':
    stamp      = None
    logfile    = None
    branchfile = None

    repo       = None
    branchfile = None
    outdir     = None
    no_test    = False

    try:
        opts, args = getopt.getopt(sys.argv[1:], 'hvns:l:b:o:c:r:',
                                  ['help', 'verbose', 'no-test',
                                   'stamp=',
                                   'logfile=',
                                   'branchfile=',
                                   'outdir=',
                                   'command=',
                                   'repo='])
    except getopt.GetoptError, err:
        usage(err)

    for opt, arg in opts:
        if opt in ('-v', '--verbose'):
            verbose = True
        elif opt in ('-h', '--help'):
            usage(None)
        elif opt in ('-n', '--no-test'):
            no_test = True
        elif opt in ('-s', '--stamp'):
            stamp = arg
        elif opt in ('-l', '--logfile'):
            logfile = arg
        elif opt in ('-b', '--branchfile'):
            branchfile = arg
        elif opt in ('-o', '--outdir'):
            outdir = arg
        elif opt in ('-c', '--command'):
            command = arg.split()
        elif opt in ('-r', '--repo'):
            repo = arg
        else:
            usage('unhandled option: ' + opt)

    if outdir is None:
        usage('Need to specify an output directory.')
    outdir = os.path.abspath(outdir)

    if stamp is None:
        # create us a timestamp
        tm = time.localtime(time.time())
        stamp = "%s%s%s%s%s" % (tm.tm_year, tm.tm_mon,
                                tm.tm_mday, tm.tm_hour, tm.tm_min)

    if logfile is None:
        logfile = stamp

    # create out dir if necessary
    if not os.path.exists(outdir):
        os.mkdir(outdir)

    # we will log all output to here
    log = open(os.path.join(outdir, logfile), 'w+')

    if no_test:
        os.chdir(outdir)
        write_report(pickle.load(open(picklef, 'rb')))
        sys.exit(0)

    if branchfile is None:
        usage('Need to specify a branchfile.')
    branchfile = os.path.abspath(branchfile)

    if repo is None:
        usage('Need to specify a repo.')
    repo = os.path.abspath(repo)

    # find out which branches to test
    branches = read_branchfile(branchfile)

    # do the merging and testing
    os.chdir(repo)
    merges, tests = do_test(branches, "next-test")

    # create a report
    os.chdir(outdir)
    create_report(merges, tests, stamp)
