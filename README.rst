SymPy Bot
=========

The goal of SymPy Bot is to do all the automated testing for a pull request and
report back into the pull request with the results.

So far one has to run the bot manually, but eventually we would like to create
a web service for it.

Usage
-----

List all pull requests, sorted by date::

    ./sympy-bot list

Make an automatic review of a pull request::

    ./sympy-bot review 268

This will run all tests and then comment in the pull request (under your name)
with the results.

Tips
----

By default, the sympy repository is fully downloaded from the web, so you don't
need to have any local copy. However, if you do have a local copy already, you
can skip most of the download (which might take a few minutes on slower
connections) by passing a ``--reference`` option to sympy-bot::

    ./sympy-bot --reference ~/repo/git/sympy review 268

This gets passed to git, see ``git clone --help`` for more information. Then
sympy-bot starts testing the branch immediately, even if you have a slower
connections.

Configuration
-------------

You can avoid providing your username and password, give a reference to
a local clone of SymPy's repository, or use a custom test command every
time when you use SymPy Bot by creating a configuration file for SymPy
Bot at ``~/.sympy/sympy-bot.conf`` and adding the following lines to it::

    user = "your user name"
    token = "your GitHub API token"
    reference = "path to a local clone of SymPy's repository"
    repository = "remote SymPy's repository (default is sympy/sympy)"
    interpreter = "interpreter to run tests with (default is 'python')"
    testcommand = "command to run tests with (default is 'setup.py test')"

Note that with configuration file you can use only token-based GitHub
authentication mechanism (this is for your safety, but anyway make sure
that the configuration file has proper permissions assigned, e.g. 600).
You may leave any value that you don't want to include empty, and the
default will be used.  If you supply a username and not an API token,
then sympy-bot will ask you for your GitHub password on each invocation.

You can get your GitHub API token by going to https://github.com/account/admin.

Foreign repositories
--------------------

SymPy Bot can be also used with other remote repository than sympy/sympy.
You can change the remote with ``-R`` flag to sympy-bot or by setting
``repository`` in configuration file. The new remote doesn't have to be
SymPy's repository, but any repository on GitHub. Note that in this case
you man need to setup customized ``testcommand``.

Custom Master Commit
--------------------

By default, sympy-bot merges with master before testing, failing if the
merge fails.  You can customize this behavior with the ``-m`` option to
``sympy-bot``.  Pass any valid git commit name to this option, and it
will use it to merge the master branch.  The default is
``origin/master``, which is the current master.  If you don't want to
merge at all, pass ``HEAD``, which will perform a noop merge against the
branch you are testing.

If you use ``--reference``, git will pull in all commits from the local
repository. Thus, you can merge with commits that are not in the
official ``sympy/sympy`` repository by using this and passing the SHA1
of the commit you want.

This is also useful for using bisecting a problem with SymPy Bot.
Simply use git to bisect in your local SymPy repository and pass the
SHA1's it picks to ``sympy-bot -n -m``.
