#!/usr/bin/env bash

if [ -d unisubs-integration ]; then
    if [ "`cd unisubs-integration; git rev-parse head`" = "`cat optional/unisubs-integration`" ]; then
        echo "Integration repo matches..."
    else
        tput bold
        echo
        echo "Mismatched integration repo!"
        exit 1
    fi
else
    echo "No integration repo (not a problem)..."
fi


echo "Everything seems sane."
exit 0
