#!/usr/bin/env bash
# Enforce the import seams declared in docs/LANGGRAPH-ARCHITECTURE.md §2.
#
#   langgraph                        -> graph/ and persistence/checkpointer.py only
#   langchain_anthropic / _openai    -> llm/factory.py only
#
# The point is reversibility: if LangChain or LangGraph has to go, exactly one file
# changes. Without a mechanical check, provider imports leak into nodes within weeks.
#
# Directories are checked even before they exist, so the rule is in force from the
# first graph PR rather than added after the leak.

set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/src/tafsirbot"
status=0

fail() {
    echo "✗ $1" >&2
    status=1
}

# $1 = import pattern, $2 = human name, rest = allowed path prefixes (relative to SRC)
check_seam() {
    local pattern="$1" name="$2"
    shift 2
    local allowed=("$@")

    # -l: filenames only. || true so an empty result is not a pipeline failure.
    local hits
    hits="$(grep -rlE "^[[:space:]]*(import|from)[[:space:]]+${pattern}" \
        --include='*.py' "$SRC" 2>/dev/null || true)"

    [ -z "$hits" ] && return 0

    while IFS= read -r file; do
        local rel="${file#"$SRC"/}"
        local ok=0
        for prefix in "${allowed[@]}"; do
            case "$rel" in
                "$prefix"*) ok=1; break ;;
            esac
        done
        if [ "$ok" -eq 0 ]; then
            fail "$rel imports $name — allowed only in: ${allowed[*]}"
        fi
    done <<< "$hits"
}

check_seam 'langgraph' 'langgraph' 'graph/' 'persistence/checkpointer.py'
check_seam 'langchain_(anthropic|openai)' 'a LangChain provider package' 'llm/factory.py'

if [ "$status" -eq 0 ]; then
    echo "✓ Import seams intact."
fi
exit "$status"
