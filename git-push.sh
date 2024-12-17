#!/bin/bash

# Add all changes
git add .

# Get the commit message as an argument, default to "Update" if none provided
commit_msg=${1:-"Update"}

# Commit with the provided or default message
git commit -m "$commit_msg"

# Push to the current branch
git push
