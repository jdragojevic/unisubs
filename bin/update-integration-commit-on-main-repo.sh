#!/usr/bin/env bash

cd unisubs-integration &&
git rev-parse HEAD > ../optional/unisubs-integration
cd ..
git add optional/unisubs-integration
git commit -m "Updated integration repo"