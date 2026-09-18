#!/usr/bin/env bash
# Watson Status Check Shortcut (ADR-056)
exec "$(dirname "$0")/service.sh" status "$@"
