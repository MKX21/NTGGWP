#!/usr/bin/env bash
set -euo pipefail

python myproject/manage.py collectstatic --noinput
