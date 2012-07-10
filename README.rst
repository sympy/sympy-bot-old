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

To review all open pull requests, do::

    ./sympy-bot review all

to only review mergeable pull requests, do::

    ./sympy-bot review mergeable

Requirements
------------

SymPy bot needs argparse to run. This is part of the standard library in
Python 2.7 and 3.2, however it can be installed in earlier versions of Python.

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

You can configure SymPy bot to remember your GitHub credentials, use an
existing clone of sympy and run interpreters under different profiles. This is
done in the ``~/.sympy/sympy-bot.conf`` file. The configuration supports
multiple profiles, but will always read in the [default] profile, so you should
start your configuration with your GitHub credentials in the default profile::

    [default]
    user = username
    password = password

If you have an existing clone of sympy, you can avoid having to clone the SymPy
repository every time the bot is run::

    reference = ~/path/to/sympy

You can specify the interpreters to use by giving a comma separated list of
Python interpreters::

    interpreter = /path/to/python, /path/to/other/python

If you pass the ``-3`` flag, the interpreters will be read from the
``interpreter3`` option. Specifying ``interpreter = None`` you can disable the
Python tests, which can be useful in setting up a profile just for testing
docs.

Any of the other options set by commandline parameters can be set in the
configuration file. See ``sympy-bot --help`` for more information.

The configuration also supports different profiles. To set these up, you put
the name of the profile between square brackets. Then, when you pass
``--profile profile_name``, the options in the specified section will override
the default section. This is done in the config file::

    [profile_name]
    interpreter = /path/to/different/python
    testcommand = bin/test --other-options

This can be useful for setting up various suites of tests, e.g. slow tests,
32-bit/64-bit tests, etc.

To see an example configuration file, see the ``sympy-bot.conf.example`` file.

Foreign repositories
--------------------

SymPy Bot can be also used with other remote repository than sympy/sympy.
You can change the remote with ``-R`` flag to sympy-bot or by setting
``repository`` in configuration file. The new remote doesn't have to be
SymPy's repository, but any repository on GitHub. Note that in this case
you may need to setup customized ``testcommand``.

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

This is also useful for bisecting problems with SymPy Bot. Simply use
git to bisect in your local SymPy repository and pass the SHA1's it
picks to ``sympy-bot -n -m``.
