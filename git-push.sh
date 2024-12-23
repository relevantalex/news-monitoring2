#!/bin/bash

# Run pre-commit checks
echo "Running pre-commit checks..."
/Users/alexanderuttendorfer/Library/Python/3.9/bin/pre-commit run --all-files
if [ $? -ne 0 ]; then
    echo "Pre-commit checks failed. Please fix the issues and try again."
    exit 1
fi

# Add all changes
git add .

# Get the commit message as an argument, default to "Update" if none provided
commit_msg=${1:-"Update"}

# Commit with the provided or default message
git commit -m "$commit_msg"

# Push to the current branch
git push
