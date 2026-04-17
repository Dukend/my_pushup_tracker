# 💪 Pushup Tracker Bot

A lightweight Telegram bot to track your daily pushups, set goals, and stay consistent with smart reminders.

Built with **Python 3.11+**, **aiogram 3**, and a single **JSON file** — no database required.

---

## Features

- **Track pushups** — send a number or use `/add 30`
- **Daily goal** with progress bar — `/goal 100`
- **7-day history** with visual bars
- **Streak counter** — days in a row with at least one pushup
- **Personal record** tracking
- **Undo** last entry — `/undo`
- **Inline keyboard menu** — all actions via buttons, no commands needed
- **Quick-add buttons** — +10, +20, +30, +50 in one tap
- **Todo list** with priorities, done/undo, delete, edit — fully inline
- **Smart reminders:**
  - 🌅 Morning — motivation + yesterday's result + today's task list
  - 💪 Evening — only fires if daily goal isn't met yet + urgent tasks
  - 📋 End-of-day summary — pushups + tasks done/remaining
  - ➕ Custom reminders with your own label and time + current task list
- **Auto-archive** — completed tasks archived at midnight, history preserved
- **Private** — single-user mode via `ALLOWED_USER_ID`
- **Timezone-aware** — configure via `TZ` env var

---

## Project structure

```
pushup_tracker/
├── main.py                  # entry point
├── requirements.txt
├── .env.example
├── pushup_tracker.service   # systemd unit
│
├── bot/
│   ├── config.py            # settings from env vars
│   ├── storage.py           # pushup JSON persistence
│   ├── todo.py              # todo list persistence
│   ├── keyboards.py         # all InlineKeyboardMarkup builders
│   ├── formatters.py        # reusable message text builders
│   ├── scheduler.py         # background reminder loop
│   └── handlers/
│       ├── commands.py      # slash-command handlers
│       ├── inline.py        # callback_query handlers (pushups)
│       ├── todo.py          # /todo command + todo inline callbacks
│       └── reminders_cmd.py # /remind subcommands
│
└── data/
    └── pushups.json         # auto-created, gitignored
```

---

## Quick start

### 1. Clone & install

```bash
git clone https://github.com/Dukend/my_pushup_tracker.git
cd my_pushup_tracker

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
```

Edit `.env`:

```env
BOT_TOKEN=your_token_from_BotFather
ALLOWED_USER_ID=your_telegram_user_id_from_userinfobot
TZ=Europe/Moscow
DAILY_GOAL=100
```

### 3. Run

```bash
python main.py
```

---

## Deploy on a server (systemd)

```bash
# Copy project
sudo cp -r . /opt/pushup_tracker
cd /opt/pushup_tracker

# Create virtualenv & install
python3 -m venv venv
venv/bin/pip install -r requirements.txt

# Configure
cp .env.example .env
nano .env   # fill in BOT_TOKEN and ALLOWED_USER_ID

# Install service
sudo cp pushup_tracker.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now pushup_tracker

# Check logs
sudo journalctl -u pushup_tracker -f
```

Resource usage: ~20 MB RAM, ~0% CPU (event-driven polling).

---

## Bot commands

| Command | Description |
|---|---|
| `/start` | Show menu |
| `/add 30` | Add 30 pushups |
| `30` | Same — just send a number |
| `/today` | Today's count |
| `/total` | All-time total |
| `/stats` | Full stats (today, total, streak, record) |
| `/history` | Last 7 days with bars |
| `/record` | Personal best for one day |
| `/undo` | Remove last entry |
| `/goal` | View current goal |
| `/goal 150` | Set new daily goal |
| `/remind` | Show reminders menu |
| `/remind morning 07:30` | Change morning reminder time |
| `/remind on evening` | Enable evening reminder |
| `/remind off evening` | Disable evening reminder |
| `/remind add 13:00 Lunch workout` | Create custom reminder |
| `/remind del <key>` | Delete custom reminder |

### Todo list

| Command | Description |
|---|---|
| `/todo` | Show active tasks |
| `/todo add Купить хлеб` | Add normal task |
| `/todo add ! Срочно` | Add high-priority task |
| `/todo done <id>` | Mark task done |
| `/todo del <id>` | Delete task |
| `/todo edit <id> New text` | Edit task |
| `/todo all` | Show active + completed today |

---

## Reminders

Three built-in reminders (can be toggled and rescheduled, not deleted):

| Key | Default | Fires when |
|---|---|---|
| `morning` | 07:30 | Every day |
| `evening` | 20:00 | Only if daily goal **not** reached |
| `summary` | 22:00 | Every day |

Custom reminders always fire at their configured time and show today's progress.

All reminder settings are persisted in `data/pushups.json` — survive restarts.

---

## Tech stack

| Layer | Choice | Why |
|---|---|---|
| Language | Python 3.11 | `zoneinfo` stdlib, match syntax |
| Bot framework | aiogram 3 | async, minimal overhead |
| Storage | JSON file | zero dependencies, human-readable |
| Scheduler | asyncio task | no cron, no celery — just one loop |
| Deploy | systemd | standard, auto-restart, logs via journalctl |

---

## License

GNU
