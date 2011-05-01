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

    ./sympy-bot --reference /home/ondrej/repos/sympy review 268

This gets passed too git, see ``git clone --help`` for more information. Then
sympy-bot starts testing the branch immediatelly, even if you have a slower
connections.
