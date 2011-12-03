from subprocess import Popen
import re
from urllib import urlopen
from json import load


############################################################################################################
def really_ugly_solution_for_finding_the_last_test_sha(pr):
    html_link = pr['html_url']
    page = ''.join(urlopen(html_link).readlines())
    search = re.search(r'<em>branch hash</em>: <a href="https://github.com/sympy/sympy/commit/(\w*)"', page)
    if search:
        return search.groups()[-1]
############################################################################################################

while True:

    open_pr = load(urlopen('https://api.github.com/repos/sympy/sympy/pulls'))
    for pr in open_pr:
        more_stuff = load(urlopen(pr['url']))
        pr.update(more_stuff)

    mergeable_pr = filter(lambda p : p['mergeable'], open_pr)

    to_be_tested = []
    for pr in mergeable_pr:
        last_test_head = really_ugly_solution_for_finding_the_last_test_sha(pr)
        if last_test_head != pr['head']['sha']:
            to_be_tested.append(str(pr['number']))

    print to_be_tested
    for pr in to_be_tested:
        print 'Testing: ' + pr
        command = ['./sympy-bot', 'review']
        command.append(pr)
        Popen(command).wait()

    sleep(6*3600)
