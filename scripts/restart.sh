#!/usr/bin/env bash
set -euo pipefail

TMUX_SESSION="ccbot"
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
MAX_WAIT=10

# Kill any running ccbot python processes directly
echo "Stopping ccbot processes..."
pkill -f 'uv run ccbot' 2>/dev/null || true
pkill -f 'ccbot/.venv/bin/ccbot' 2>/dev/null || true

waited=0
while pgrep -f 'ccbot/.venv/bin/ccbot' >/dev/null 2>&1 && [ "$waited" -lt "$MAX_WAIT" ]; do
    sleep 1
    waited=$((waited + 1))
    echo "  Waiting for process to exit... (${waited}s/${MAX_WAIT}s)"
done

if pgrep -f 'ccbot/.venv/bin/ccbot' >/dev/null 2>&1; then
    echo "Force killing..."
    pkill -9 -f 'ccbot/.venv/bin/ccbot' 2>/dev/null || true
    sleep 1
fi
echo "Process stopped."

# Kill existing tmux server and start fresh
# Avoids orphaned windows and stale state
echo "Restarting tmux session..."
tmux kill-server 2>/dev/null || true
sleep 1

# Clear Claude Code env vars so child windows can launch claude without
# "nested session" errors (restart.sh is often invoked from a Claude session)
unset CLAUDECODE CLAUDE_CODE_ENTRYPOINT

tmux new-session -d -s "$TMUX_SESSION" -x 120 -y 40 -c "$PROJECT_DIR" "uv run ccbot"

# Verify startup
sleep 3
if pgrep -f 'ccbot/.venv/bin/ccbot' >/dev/null 2>&1; then
    echo "ccbot restarted successfully. Recent logs:"
    echo "----------------------------------------"
    tmux capture-pane -t "${TMUX_SESSION}:0" -p 2>/dev/null | tail -20
    echo "----------------------------------------"
else
    echo "Warning: ccbot may not have started. Pane output:"
    echo "----------------------------------------"
    tmux capture-pane -t "${TMUX_SESSION}:0" -p 2>/dev/null | tail -30
    echo "----------------------------------------"
    exit 1
fi
