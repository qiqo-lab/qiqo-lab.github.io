#!/usr/bin/env python3
"""Suppress another content review after one was merged on the same Lisbon day."""
import datetime as dt
import json
import os
import sys
from zoneinfo import ZoneInfo

LISBON = ZoneInfo('Europe/Lisbon')
BRANCH = 'automation/weekly-content-review'

def merged_review_today(pages, repository, now=None):
    today = (now or dt.datetime.now(dt.timezone.utc)).astimezone(LISBON).date()
    for page in pages:
        for pr in page:
            if not pr.get('merged_at'):
                continue
            head, base = pr.get('head', {}), pr.get('base', {})
            if head.get('ref') != BRANCH or base.get('ref') != 'main':
                continue
            if (head.get('repo') or {}).get('full_name') != repository:
                continue
            if (base.get('repo') or {}).get('full_name') != repository:
                continue
            merged = dt.datetime.fromisoformat(pr['merged_at'].replace('Z', '+00:00'))
            if merged.astimezone(LISBON).date() == today:
                return pr['number']
    return None

def main():
    number = merged_review_today(json.load(sys.stdin), os.environ['GITHUB_REPOSITORY'])
    output = f'skip={str(number is not None).lower()}\n'
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'], 'a') as f:
            f.write(output)
    print(output, end='')
    if number is not None:
        message = f'Content review skipped: PR #{number} was already merged today (Europe/Lisbon).'
        print(message)
        if os.environ.get('GITHUB_STEP_SUMMARY'):
            with open(os.environ['GITHUB_STEP_SUMMARY'], 'a') as f:
                f.write(message + '\n')

if __name__ == '__main__':
    main()
