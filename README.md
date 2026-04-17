# 💪 Pushup Tracker Bot

A lightweight Telegram bot to track your daily pushups, set goals, and stay consistent with smart reminders and a built-in todo list.

Built with **Python 3.11+**, **aiogram 3**, and a single **JSON file** — no database required.

---

## Features

**Pushups**
- Track pushups — send a number or `/add 30`
- Daily goal with progress bar — `/goal 100`
- Progress bar shows overachievement: `[██████████▓▓] 120% 🔥`
- 7-day history with visual bars + weekly summary (total, goal hit N/7, avg/day)
- Streak counter — consecutive days where the **daily goal was met**
- Personal record tracking
- Undo last entry — `/undo`

**Todo list**
- Add tasks with `/new` (FSM dialog) or `/todo add text`
- High priority with `!`: `/todo add ! Срочно` → 🔴
- Mark done, undo, delete with confirmation — all via inline buttons
- Edit text — `/todo edit <id> New text`
- Auto-archive completed tasks at midnight

**Reminders**
- 🌅 Morning — motivation + yesterday's result + today's task list
- 💪 Evening — fires only if daily goal not yet met + urgent tasks
- 📋 End-of-day summary — pushups + tasks done/remaining
- ➕ Custom reminders with your own label, time, and task list — via FSM dialog
- All reminders togglable and reschedulable from inline menu

**UX**
- Inline keyboard menu — all actions via buttons, no commands needed
- Quick-add buttons — +10, +20, +30, +50 in one tap
- FSM dialogs for adding tasks and reminders (step-by-step prompts)
- `/cancel` exits any active dialog
- Bot command hints registered in Telegram via `set_my_commands`
- Single-user mode via `ALLOWED_USER_ID`
- Timezone-aware via `TZ` env var

---

## Project structure

```
pushup_tracker/
├── main.py                      # entry point — DI, routers, scheduler
├── requirements.txt
├── pyproject.toml               # project manifest + ruff config
├── .env.example
├── pushup_tracker.service       # systemd unit
│
├── bot/
│   ├── config.py                # settings from env vars (singleton)
│   ├── storage.py               # pushup / goal / reminder persistence
│   ├── todo.py                  # todo list persistence + archive
│   ├── keyboards.py             # all InlineKeyboardMarkup builders
│   ├── formatters.py            # reusable message text builders
│   ├── scheduler.py             # background reminder loop (asyncio task)
│   └── handlers/
│       ├── commands.py          # slash-command handlers
│       ├── inline.py            # callback_query handlers (menu + quick-add)
│       ├── todo.py              # /todo command + todo inline callbacks
│       ├── reminders_cmd.py     # /remind with all subcommands
│       └── fsm.py               # FSM: add task dialog, add reminder dialog
│
└── data/
    └── pushups.json             # auto-created, gitignored
```

---

## Quick start

### 1. Clone & install

```bash
git clone https://github.com/Dukend/my_pushup_tracker.git
cd my_pushup_tracker

python3 -m venv venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements.txt
# or with uv: uv sync
```

### 2. Configure

```bash
cp .env.example .env
```

Edit `.env`:

```env
BOT_TOKEN=your_token_from_BotFather
ALLOWED_USER_ID=your_telegram_user_id   # get from @userinfobot
TZ=Europe/Moscow
DAILY_GOAL=100
```

The bot loads `.env` automatically via **python-dotenv** — no need to export variables manually.

### 3. Run

```bash
python main.py
# or with uv: uv run main.py
```

---

## Deploy on a server (systemd)

```bash
sudo cp -r . /opt/pushup_tracker
cd /opt/pushup_tracker

python3 -m venv venv
venv/bin/pip install -r requirements.txt

cp .env.example .env && nano .env   # fill in BOT_TOKEN and ALLOWED_USER_ID

sudo cp pushup_tracker.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now pushup_tracker

# Logs
sudo journalctl -u pushup_tracker -f
```

Resource usage: ~20 MB RAM, ~0% CPU.

---

## Commands

### Pushups

| Command | Description |
|---|---|
| `/start` | Show main menu |
| `/add 30` | Add 30 pushups |
| `30` | Same — just send a number |
| `/today` | Today's count |
| `/total` | All-time total |
| `/stats` | Full stats — today, total, streak, record |
| `/history` | Last 7 days with bars + weekly summary |
| `/record` | Personal best for one day |
| `/undo` | Remove last entry |
| `/goal` | View current goal |
| `/goal 150` | Set new daily goal |

### Todo list

| Command | Description |
|---|---|
| `/todo` | Show active tasks |
| `/new` | Add task via dialog (FSM) |
| `/todo add Купить хлеб` | Add normal task inline |
| `/todo add ! Срочно` | Add high-priority task |
| `/todo done <id>` | Mark done |
| `/todo del <id>` | Delete task |
| `/todo edit <id> New text` | Edit task text |
| `/todo all` | Show active + completed today |
| `/cancel` | Cancel active dialog |

### Reminders

| Command | Description |
|---|---|
| `/remind` | Show reminders menu |
| `/remind morning 07:30` | Change morning reminder time |
| `/remind on evening` | Enable reminder |
| `/remind off evening` | Disable reminder |
| `/remind add 13:00 Lunch` | Create custom reminder (inline) |
| `/remind del <key>` | Delete custom reminder |

Custom reminders can also be created via the `➕` button in the reminders menu — a step-by-step FSM dialog asks for time then label.

---

## Reminders

| Key | Default | Fires when |
|---|---|---|
| `morning` | 07:30 | Every day — shows task list |
| `evening` | 20:00 | Only if daily goal **not** reached — shows urgent tasks |
| `summary` | 22:00 | Every day — pushup result + tasks done/remaining |
| custom | your time | Every day — shows active task list |

Completed tasks are auto-archived at `00:01` into `todo_archive.YYYY-MM-DD` in the JSON file.

---

## Architecture notes

- **Dependency injection** — `Storage` and `TodoStorage` are created once in `main.py`, registered as `dp["storage"]` and `dp["todo"]`, and injected into handler functions by name via aiogram's DI system.
- **FSM** — `MemoryStorage` is used for FSM state. The `fsm` router is registered before all others so state-bound message handlers take priority.
- **Scheduler** — a plain `asyncio.create_task` loop that wakes every 30 s. No external scheduler dependency.
- **Storage** — single JSON file, read-modify-write on every operation. Safe for single-user use; no locking needed.
- **Streak logic** — counts consecutive days where `pushups >= goal`. Today is included only if the goal is already reached, so an in-progress day doesn't break a valid streak.

---

## Tech stack

| Layer | Choice | Why |
|---|---|---|
| Language | Python 3.11 | `zoneinfo` stdlib, union types |
| Bot framework | aiogram 3 | async, DI, FSM built-in |
| Storage | JSON file | zero dependencies, human-readable |
| FSM storage | MemoryStorage | single user, no persistence needed |
| Env config | python-dotenv | `.env` loaded automatically, no manual export |
| Scheduler | asyncio task | no cron, no celery |
| Deploy | systemd | standard, auto-restart, journalctl |

---

## License

GNU
