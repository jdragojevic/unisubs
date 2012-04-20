Sentry
======

This document describes how you can run the Sentry server inside Vagrant.
Amara uses the latest sentry server and the raven client.  Django exceptions
are logged.  Regular Django logging goes to sentry as well.

1.  Log in to your vagrant VM
2.  Make sure all Python requirements are up-to-date
3.  ``$ ./dev-sentry.sh``
4.  Create a user for yourself
5.  Open http://unisubs.example.com:9000
6.  Log in to the console 
7.  Navigate the menus and find your server's DSN string
8.  Open ``dev_settings.py`` and paste your string to ``SENTRY_DSN``.  Change
    the host to ``localhost``.
9.  Start your development server
10. Profit
