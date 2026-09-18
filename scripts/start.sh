#!/usr/bin/env bash
# Watson Asynchronous Start Shortcut (ADR-056)
exec "$(dirname "$0")/service.sh" start "$@"
