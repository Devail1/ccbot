# CCBot on Windows via WSL

CCBot requires tmux, which is Linux-only. On Windows, run ccbot inside WSL (Windows Subsystem for Linux).

## Prerequisites

- Windows 10/11 with WSL2 enabled
- A WSL distribution (Ubuntu recommended)
- A Telegram bot token (from @BotFather, with Threaded Mode enabled)
- A Telegram group with Topics mode enabled
- Claude Max/Pro subscription

## Step 1: Install Node.js in WSL

CCBot needs Claude Code CLI, which requires Node.js.

```bash
# Install nvm (no sudo required)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash

# Reload shell
source ~/.bashrc

# Install Node.js 20
nvm install 20
nvm use 20
```

## Step 2: Install Claude Code CLI

```bash
npm install -g @anthropic-ai/claude-code
claude --version  # Should show version
```

## Step 3: Authenticate Claude Code

Start Claude interactively to complete the first-time OAuth flow:

```bash
claude
```

This will show an OAuth URL. Open it in your Windows browser, sign in with your Claude account, and paste the code back into the terminal. You only need to do this once — subsequent sessions will authenticate automatically.

**Important:** The OAuth URL contains a `#` character. If pasting via tmux `send-keys`, use the `-l` (literal) flag to prevent tmux from interpreting `#` as a comment:
```bash
tmux send-keys -t session:window -l "code_with#hash" Enter
```

## Step 4: Install uv (Python package manager)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.local/bin/env
```

## Step 5: Clone and install ccbot

```bash
cd ~
git clone https://github.com/six-ddc/ccbot.git
cd ccbot
uv sync
```

## Step 6: Configure ccbot

```bash
mkdir -p ~/.ccbot
```

Create `~/.ccbot/.env`:
```ini
TELEGRAM_BOT_TOKEN=your_bot_token_here
ALLOWED_USERS=your_telegram_user_id
CLAUDE_COMMAND=/home/your-user/.nvm/versions/node/v20.x.x/bin/claude
TMUX_SESSION_NAME=ccbot
MONITOR_POLL_INTERVAL=2.0
```

**Note:** Use the full path for `CLAUDE_COMMAND` since tmux windows may not have nvm in PATH. Find it with `which claude`.

## Step 7: Install the session tracking hook

```bash
cd ~/ccbot
uv run ccbot hook --install
```

This adds a `SessionStart` hook to `~/.claude/settings.json` so ccbot tracks which Claude session runs in each tmux window.

## Step 8: Clone your project repos

Clone repos natively in WSL (not via `/mnt/c` — native WSL filesystem is much faster):

```bash
cd ~
git clone https://user:token@github.com/your-user/your-repo.git
```

You can get a GitHub token from Windows: run `git credential fill` with `protocol=https` and `host=github.com` as input.

## Step 9: Set up Telegram

1. Create a Telegram **group** (or supergroup)
2. Enable **Topics** mode in group settings
3. Add your bot to the group as **admin** with permissions:
   - Send Messages
   - Manage Topics
   - Delete Messages

## Step 10: Start ccbot

```bash
cd ~/ccbot
source ~/.nvm/nvm.sh
source ~/.local/bin/env
uv run ccbot
```

## Step 11: Create a session

### Option A: Via Telegram (recommended)
1. Create a new topic in your Telegram group
2. Send any message — ccbot shows a directory browser or window picker
3. Select your project directory (or bind to a running window)
4. Claude Code starts in a tmux window, bound to that topic

### Option B: Pre-spawn manually
Start Claude in a named tmux window first, then bind from Telegram:

```bash
# From a Windows terminal:
wsl -d Ubuntu -- bash -lc 'source ~/.nvm/nvm.sh && \
  tmux new-window -t ccbot -n my-project -c ~/my-project && \
  tmux send-keys -t ccbot:my-project claude Enter'
```

Then in Telegram, create a topic and send a message — ccbot will show a window picker with the running session.

## Customizing the directory browser start path

By default, the directory browser starts at the current working directory. To change it, edit `src/ccbot/bot.py` and replace all instances of:

```python
start_path = str(Path.cwd())
default_path = str(Path.cwd())
```

with your preferred path:

```python
start_path = "/home/your-user"
default_path = "/home/your-user"
```

## Accessing Windows files

WSL can access Windows files via `/mnt/c/...`, but performance is significantly slower than native WSL filesystem. For best results:

- Clone repos natively in WSL (`~/your-repo`)
- Use `/mnt/c/` only for occasional file access
- Create symlinks for convenience: `ln -s /mnt/c/Users/you/Documents/GitHub ~/github`

## Running as a background service

To keep ccbot running after closing the terminal:

```bash
# Option 1: Persistent tmux session (separate from ccbot session)
tmux new-session -d -s bot-runner \
  "cd ~/ccbot && source ~/.local/bin/env && source ~/.nvm/nvm.sh && uv run ccbot"

# Option 2: nohup
cd ~/ccbot
nohup bash -lc "source ~/.local/bin/env && uv run ccbot" > ~/ccbot.log 2>&1 &
```

## Troubleshooting

### Claude asks to log in despite credentials existing
Claude Code runs a first-time setup wizard on first interactive launch, even if `~/.claude/.credentials.json` exists. Complete the OAuth flow once interactively (Step 3), then all subsequent sessions work automatically.

### tmux send-keys drops text after `#`
Use `tmux send-keys -l "text"` — the `-l` flag sends literal text without interpreting `#` as a tmux comment character.

### Slow file operations on /mnt/c
Known WSL limitation. Clone repos to the native WSL filesystem (`~/`) instead of working through `/mnt/c/`.

### Git credential issues in WSL
Don't try to use the Windows credential manager from WSL (path spaces break it). Instead:
```bash
# Clone with token directly
git clone https://user:ghp_token@github.com/user/repo.git

# Or use credential cache
git config --global credential.helper cache
```

### WSL needs sudo password
Install everything in userspace (nvm, uv, npm global packages). No sudo is required for the full setup.
