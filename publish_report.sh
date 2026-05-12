#!/bin/bash
set -e

python generate_report.py

git add docs/index.html
git commit -m "Update positions report $(date -u '+%Y-%m-%d %H:%M UTC')"
git push
