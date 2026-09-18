#!/usr/bin/env bash
# Watson Asynchronous Restart Shortcut (ADR-056)
exec "$(dirname "$0")/service.sh" restart "$@"
