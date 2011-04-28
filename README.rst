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
