from subprocess import Popen
from time import sleep
import re
from urllib import urlopen
from json import load


############################################################################################################
def really_ugly_solution_for_finding_the_last_test_sha(pr):
    html_link = pr['html_url']
    page = ''.join(urlopen(html_link).readlines())
    search = re.findall(r'<em>branch hash</em>: <a href="https://github.com/sympy/sympy/commit/(\w*)"', page)
    if search:
        return search[-1]
############################################################################################################

while True:

    open_pr = load(urlopen('https://api.github.com/repos/sympy/sympy/pulls'))
    for pr in open_pr:
        more_stuff = load(urlopen(pr['url']))
        pr.update(more_stuff)
    print "OPEN PRs"
    print [pr['number'] for pr in open_pr]

    lambd_filt = lambda pr : pr['head']['sha'] != really_ugly_solution_for_finding_the_last_test_sha(pr)
    to_be_tested = filter(lambd_filt, open_pr)

    print "TO BE TESTED"
    print [pr['number'] for pr in to_be_tested]
    for pr in to_be_tested:
        number = str(pr['number'])
        print 'Testing: ' + number
        command = ['./sympy-bot', 'review']
        command.append(number)
        Popen(command).wait()
        if pr['mergeable']:
            command = ['./sympy-bot', '-3', 'review']
            command.append(number)
            Popen(command).wait()
            command = ['./sympy-bot', '-i', 'python2.5', 'review']
            command.append(number)
            Popen(command).wait()

    sleep(3600)
