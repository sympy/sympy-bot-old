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

Tips
----

By default, the SymPy repository is fully downloaded from the web, so you don't
need to have any local copy. However, if you do have a local copy already, you
can skip most of the download (which might take a few minutes on slower
connections) by passing a ``--reference`` option to sympy-bot::

    ./sympy-bot --reference ~/repo/git/sympy review 268

This gets passed to git, see ``git clone --help`` for more information. Then
sympy-bot starts testing the branch immediately, even if you have a slower
connections.

Configuration
-------------

You can avoid providing your username and password, give a reference to a local
clone of SymPy's repository, or use a custom test command every time when you
use SymPy Bot by creating a configuration file for SymPy Bot at
``~/.sympy/sympy-bot.conf``. The first time you run sympy-bot and need to
authenticate with GitHub, you will be prompted to create a configuration file
and OAuth token. Alternately, you can create this file on you own and add the
following lines to it::

    user = "username"
    token = "your GitHub API token"

You can create a token on your own by running the following command::

    curl -u 'username' -d '{"scopes":["repo"],"note":"SymPy Bot"}' \
    https://api.github.com/authorizations

and enter your password at the prompt. In the information that is printed out,
take the token and add it to your configuration file, as above.

If you intend on publishing your dotfiles publicly, you can put your token in a
separate file and reference that file in your configuration like this::

    token_file = "~/path/to/token"

The token file then only has your token in it (without quotes around it).

You can manage your authorizations at https://github.com/settings/applications.
If you use token authentication, for your safety, be sure that the
configuration file and token have proper permissions assigned, e.g. 600.  If
you supply a username without a password or API token, then sympy-bot will ask
you for your GitHub password on each invocation.

To avoid having to clone the SymPy repository every time the bot is run, you
can add::

    reference = "~/path/to/local/sympy"

A typical configuration will look something like this::

    user = "sympy"
    token_file = "~/.sympy/token"
    reference = "~/sympy"
    interpreter = "/path/to/default/python"
    interpreter3 = "/path/to/default/python3"

If you do not have a configuration file, you will be prompted to make one after
logging in.

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

This is also useful for bisecting problems with SymPy Bot. Simply use
git to bisect in your local SymPy repository and pass the SHA1's it
picks to ``sympy-bot -n -m``.
