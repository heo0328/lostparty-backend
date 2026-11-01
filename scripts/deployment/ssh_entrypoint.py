#!/usr/bin/python3
"""Forced SSH command for the deployment-only account. No shell/forwarding."""
import os
import re
import sys


def arguments(original):
    if original in ('submit', 'preflight'):
        return [original]
    if re.fullmatch(r'status [0-9]+-[0-9]+', original):
        return original.split(' ')
    raise ValueError('command not allowed')


def main():
    try:
        args = arguments(os.environ.get('SSH_ORIGINAL_COMMAND', ''))
    except ValueError:
        raise SystemExit('Deployment command not allowed') from None
    os.execv('/usr/bin/sudo', ['sudo', '-n', '/usr/bin/python3',
             '/usr/local/lib/lostparty-deploy/server.py', *args])


if __name__ == '__main__':
    main()
