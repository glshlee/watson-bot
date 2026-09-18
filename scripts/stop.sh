#!/usr/bin/env bash
# Watson Stop Shortcut (ADR-056)
exec "$(dirname "$0")/service.sh" stop "$@"
