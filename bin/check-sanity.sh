#!/usr/bin/env bash

# Integration repo file format
INTEGRATION_REPO_LINES=$(grep . optional/unisubs-integration | wc -l | tr -d ' ')

if [ $INTEGRATION_REPO_LINES -eq 1 ]; then
    tput sgr0
    echo "optional/unisubs-integration file looks good..."
else
    tput bold
    tput setaf 1
    echo
    echo "Bad optional/unisubs-integration file format!"
    tput sgr0
    exit 1
fi

# Integration repo version
if [ -d unisubs-integration ]; then
    if [ "`cd unisubs-integration; git rev-parse head`" = "`cat optional/unisubs-integration`" ]; then
        tput sgr0
        echo "Integration repo matches (good)..."
    else
        tput bold
        tput setaf 1
        echo
        echo "Mismatched integration repo!"
        tput sgr0
        exit 1
    fi
else
    tput sgr0
    echo "No integration repo (not a problem)..."
fi

# Duplicate migrations
DUPLICATE_MIGRATIONS=$(find . -name '*.py' | grep -E 'migrations.*\d+_\w+.py' | sed -e 's_.*/\([^/]*\)/migrations/_\1/_' -e 's/\([0-9][0-9]*\)_.*.py/\1/g' | sort | uniq -c | grep -Ev '^\s+1 ')

if [ -z "$DUPLICATE_MIGRATIONS" ]; then
    tput sgr0
    echo "No duplicate migration numbers (good)..."
else
    tput bold
    tput setaf 1
    echo
    echo "There are migrations with duplicate numbers!"
    echo
    echo "$DUPLICATE_MIGRATIONS"
    tput sgr0
    exit 1
fi

# console.log()
CONSOLE_DOT_LOGGERS=$(find . -name '*.js' \
                    | grep -v 'jquery.*.js' \
                    | grep -v 'flowplayer.*.min.js' \
                    | xargs grep -l 'console.log')

if [ -z "$CONSOLE_DOT_LOGGERS" ]; then
    tput sgr0
    echo "No console.log() calls (good)..."
else
    tput bold
    tput setaf 1
    echo
    echo "There are console.log() calls (which break IE)!  They are in the following files:"
    echo
    echo "$CONSOLE_DOT_LOGGERS"
    tput sgr0
    exit 1
fi

# Done!
tput bold
tput setaf 2
echo
echo "Everything seems sane."
tput sgr0
exit 0
