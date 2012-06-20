#!/usr/bin/env bash

# Integration repo version
if [ -d unisubs-integration ]; then
    if [ "`cd unisubs-integration; git rev-parse head`" = "`cat optional/unisubs-integration`" ]; then
        echo "Integration repo matches (good)..."
    else
        tput bold
        echo
        echo "Mismatched integration repo!"
        exit 1
    fi
else
    echo "No integration repo (not a problem)..."
fi

# console.log()
CONSOLE_DOT_LOGGERS=$(find . -name '*.js' \
                    | grep -v 'jquery.*.js' \
                    | grep -v 'flowplayer.*.min.js' \
                    | xargs grep -l 'console.log')

if [ -z "$CONSOLE_DOT_LOGGERS" ]; then
    echo "No console.log() calls (good)..."
else
    tput bold
    echo
    echo "There are console.log() calls (which break IE)!  They are in the following files:"
    echo
    echo "$CONSOLE_DOT_LOGGERS"
    exit 1
fi

# Done!
echo
echo "Everything seems sane."
exit 0
