# AutoFiller — AI-Powered Keyboard Text Expander

**Stop retyping the same text. Let AutoFiller do it for you.**

AutoFiller is a lightweight, always-on keyboard text expander for macOS that runs silently in the background. Type a short trigger sequence anywhere — in any app, any text field — and AutoFiller instantly replaces it with your full text, an AI-generated response, or a saved clipboard value. No copy-pasting. No switching windows. Just type and go.

Whether you're a job seeker filling out applications, a developer writing boilerplate, a support agent answering tickets, or anyone who types the same things over and over — AutoFiller turns seconds of repetitive typing into milliseconds.

---

## Table of Contents

- [Why AutoFiller?](#why-autofiller)
- [Features](#features)
- [Use Cases](#use-cases)
- [Requirements](#requirements)
- [Installation](#installation)
- [Getting Started](#getting-started)
- [The Mapping Manager UI](#the-mapping-manager-ui)
- [Action Types Explained](#action-types-explained)
- [Profiles](#profiles)
- [Session Variables](#session-variables)
- [AI-Powered Responses (LLM Query)](#ai-powered-responses-llm-query)
- [Keyboard Shortcuts Reference](#keyboard-shortcuts-reference)
- [Configuration & Settings](#configuration--settings)
- [Data Storage](#data-storage)
- [Tips & Tricks](#tips--tricks)
- [Troubleshooting](#troubleshooting)

---

## Why AutoFiller?

The average knowledge worker types the same phrases, addresses, URLs, and boilerplate dozens of times per day. That's thousands of keystrokes wasted every week — time that adds up to hours every month.

AutoFiller eliminates that waste completely:

- **Instant expansion** — replacements happen in under 100ms, faster than you can blink
- **Works everywhere** — any app, any browser, any text field on your Mac
- **No cloud sync required** — everything is stored locally in a SQLite database
- **AI built-in** — ask GPT questions without leaving your keyboard flow
- **Profile switching** — maintain separate shortcut sets for work, personal, or different clients

---

## Features

- **Text Expansion** — replace short triggers with any text, no matter how long
- **Clipboard Storage** — save clipboard contents to named session variables with a trigger
- **AI Query** — send a prompt to GPT-4o-mini and type the response inline, anywhere
- **Session Variables** — store and reuse values (like a resume or job description) within a session
- **Profiles** — keep separate mapping sets per context; switch with a keyboard trigger
- **Visual UI** — manage all mappings from a clean desktop window
- **SQLite storage** — fast, local, zero-dependency database
- **`.env` support** — load API keys from a `.env` file automatically

---

## Use Cases

### Job Applications
This is where AutoFiller truly shines. Stop retyping your name, address, company, LinkedIn URL, and cover letter phrases on every application form.

| Trigger | Expands to |
|---------|-----------|
| `#name` | Your full name |
| `#email` | your@email.com |
| `#phone` | +1 (555) 123-4567 |
| `#addr` | 123 Main St, City, State 12345 |
| `#link` | https://linkedin.com/in/yourprofile |
| `#comp` | Your target company name |

Then go further with AI. Copy a job description, type `jjj` to save it. Copy your resume, type `rrr` to save it. Now type `qqq` anywhere and AutoFiller will ask GPT *"given this resume and this job description, answer this question: [your clipboard]"* — and type the answer directly.

### Customer Support & Sales
Speed up ticket replies with pre-written responses that take seconds to customize.

| Trigger | Expands to |
|---------|-----------|
| `#greet` | "Hi [Name], thank you for reaching out to us today!" |
| `#delay` | "We sincerely apologize for the delay. Our team is working on this as a priority..." |
| `#close` | "Please don't hesitate to reach out if you need anything else. Have a great day!" |
| `#refund` | Full refund policy paragraph |

### Software Development
Type less, code faster. Expand common boilerplate, URLs, and command snippets.

| Trigger | Expands to |
|---------|-----------|
| `#todo` | `// TODO(yourname): ` |
| `#log` | `console.log('DEBUG:', )` |
| `#env` | Your local dev server URL |
| `#gh` | Your GitHub profile URL |
| `#copy` | Standard copyright/license header |

### Writing & Content Creation
Eliminate the friction of repetitive phrases in articles, emails, and social posts.

| Trigger | Expands to |
|---------|-----------|
| `#sign` | Full email signature block |
| `#disc` | Standard disclaimer paragraph |
| `#cta` | Your go-to call-to-action sentence |
| `#bio` | Your author bio |

### Medical / Legal / Finance Professionals
Standardize repetitive language that must be exact every time.

| Trigger | Expands to |
|---------|-----------|
| `#hipaa` | HIPAA compliance disclaimer |
| `#terms` | Standard terms and conditions |
| `#disc2` | Financial disclaimer text |

### Multi-Language Support
Store greetings, sign-offs, or phrases in different languages under easy-to-remember triggers.

---

## Requirements

- macOS (10.15 Catalina or later recommended)
- Python 3.11+
- Accessibility permission (required for keyboard monitoring)

---

## Installation

**1. Clone or download the project**

```bash
git clone https://github.com/yourname/autofiller.git
cd autofiller
```

**2. Create a virtual environment (recommended)**

```bash
python3 -m venv venv
source venv/bin/activate
```

**3. Install dependencies**

```bash
pip install pynput pyperclip openai python-dotenv
```

**4. Install Tkinter** (if not already available)

```bash
brew install python-tk@3.13
```
> Replace `3.13` with your Python version (`python3 --version` to check).

**5. Grant Accessibility permission**

AutoFiller needs macOS Accessibility access to monitor keyboard input.

1. Open **System Settings → Privacy & Security → Accessibility**
2. Click the **+** button
3. Navigate to your Terminal app (or IDE) and add it
4. Make sure the toggle is **enabled**

> You only need to do this once. macOS may prompt you automatically on first run.

---

## Getting Started

**Run with the visual UI (recommended):**

```bash
python keyboard_expander.py --ui
```

**Run as a background daemon only (no window):**

```bash
python keyboard_expander.py
```

**Using a `.env` file for your OpenAI API key:**

Create a `.env` file in the project directory:

```
OPENAI_API_KEY=sk-your-key-here
```

AutoFiller loads this automatically on startup. You can also set the key from inside the Settings UI.

---

## The Mapping Manager UI

Launch with `--ui` to open the Mapping Manager window.

```
┌─────────────────────────────────────────────────────────────────┐
│ Profile: Default        [Manage Profiles]          [Settings]   │
├─────────────────────────────────────────────────────────────────┤
│ [+ Add]  [Edit]  [Delete]                                       │
├───────────┬──────────────────┬──────────────────────────────────┤
│ Shortcut  │ Action           │ Expansion / Variable / Prompt    │
├───────────┼──────────────────┼──────────────────────────────────┤
│ #addr     │ Expand           │ 123 Main St, City, State...      │
│ jjj       │ Store Clipboard  │ job_description                  │
│ qqq       │ LLM Query        │ Here is a resume: <<<{{resum...  │
│ ///       │ Switch Profile   │                                  │
│ uuu       │ Show UI          │                                  │
├───────────┴──────────────────┴──────────────────────────────────┤
│ Session Variables                                               │
│ ┌────────────────┐  ┌───────────────────────────────────────┐  │
│ │ job_description│  │ Software Engineer at Acme Corp...     │  │
│ │ resume         │  │ (full text, scrollable)               │  │
│ └────────────────┘  └───────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

**Adding a mapping:**
1. Click **+ Add**
2. Enter your trigger (e.g. `#email`)
3. Choose an action type
4. Enter the expansion text
5. Click **Save**

**Editing a mapping:** Double-click any row, or select it and click **Edit**.

**Deleting a mapping:** Select a row and click **Delete**, or press the Delete/Backspace key.

The window closes to the background when you press the X button — AutoFiller keeps running. Reopen it by typing `uuu` anywhere, or by rerunning the command.

---

## Action Types Explained

AutoFiller supports five action types, selectable per mapping:

### 1. Expand
The simplest action. Replaces your trigger with any text you define.

> **Example:** Type `#sig` → replaced with your full 5-line email signature

Great for: names, addresses, URLs, email templates, code snippets, legal boilerplate.

---

### 2. Store Clipboard
Silently saves the current clipboard contents into a named session variable. The trigger text is deleted — nothing is typed in its place.

> **Example:** Copy a job description, then type `jjj` → saves to `job_description`

Great for: capturing context (resumes, job descriptions, notes, reference text) that you want to reuse in AI queries later.

---

### 3. LLM Query
The most powerful action. Deletes the trigger, then sends a prompt to GPT-4o-mini (streaming), and types the AI's response character by character directly at your cursor.

Your prompt template can include:
- `{{clipboard}}` — current clipboard text
- `{{job_description}}` — stored session variable
- `{{resume}}` — stored session variable
- Any other named session variable you've created

> **Example:** Copy an interview question, type `qqq` → AutoFiller asks GPT *"given my resume and this job description, answer this question"* and types the answer

Great for: interview prep, cover letter drafting, email replies, content generation, summarization.

Typing speed and style are configurable in **Settings**. You can keep the default human-like typing emulation on, or disable it for faster direct typing.

---

### 4. Show UI
Opens the Mapping Manager window. No expansion — the trigger is silently deleted.

> **Default trigger:** `uuu`

Great for: quickly accessing your shortcut list without switching to a terminal.

---

### 5. Switch Profile
Opens the profile switcher popup. Choose a different profile from the list and all your mappings instantly switch.

> **Default trigger:** `///`

Great for: switching between work/personal/client contexts without touching the mouse.

---

## Profiles

Profiles let you maintain completely separate sets of shortcuts for different contexts. Everything is isolated per profile — mappings, session variables, and stored text.

**Creating a profile:**
1. Click **Manage Profiles** in the top bar
2. Click **+ New Profile**
3. Enter a name (e.g. "Work", "Personal", "Client A")

Each new profile is automatically seeded with the five system shortcuts (`jjj`, `rrr`, `qqq`, `uuu`, `///`) so they work immediately.

**Switching profiles:**
- From the UI: **Manage Profiles → Switch to Selected**
- From the keyboard: type `///` anywhere → select from the popup

**Deleting a profile:**
- Open **Manage Profiles**, select the profile, click **Delete**
- The last remaining profile cannot be deleted
- If you delete the active profile, AutoFiller automatically switches to another

**Example profile setup:**

| Profile | Purpose |
|---------|---------|
| `Job Search` | Resume snippets, company names, cover letter phrases, AI interview helper |
| `Work` | Internal URLs, team email templates, code snippets, client names |
| `Personal` | Home address, personal email signature, social media bios |

---

## Session Variables

Session variables are named text slots that persist within a session (and are saved to the database, so they survive restarts). They are **per-profile** — each profile has its own independent set.

**How they work:**

1. Copy some text to your clipboard
2. Type a `store_clipboard` trigger (e.g. `jjj`)
3. The text is silently saved to a named variable (e.g. `job_description`)
4. Later, use `{{job_description}}` in any LLM Query prompt template

**Viewing session variables:**

The bottom panel of the Mapping Manager shows all current session variables. Click a variable name on the left to see its full content in the scrollable text area on the right.

**Typical job-search workflow:**

```
1. Find a job posting you like
2. Select all → Copy
3. Type: jjj          ← saves job description to session
4. Open your resume document
5. Select all → Copy
6. Type: rrr          ← saves resume to session
7. See an application question like "Why do you want to work here?"
8. Copy that question
9. Type: qqq          ← GPT reads your resume + JD + question, types the answer
```

---

## AI-Powered Responses (LLM Query)

AutoFiller uses the OpenAI API (GPT-4o-mini by default) to generate responses inline at your cursor.

### Setup

Set your API key in one of two ways:

**Option A — Settings UI (recommended):**
1. Open AutoFiller with `--ui`
2. Click **Settings** (top right)
3. Paste your OpenAI API key
4. Click **Save**

**Option B — `.env` file:**
```
OPENAI_API_KEY=sk-proj-your-key-here
```

The DB setting takes priority over the `.env` file.

### Customizing the prompt

By default, the `qqq` trigger uses this prompt:

```
Here is a resume: <<<{{resume}}>>>, and here is a job description: <<<{{job_description}}>>>.
Respond with only the answer to this question in 1~2 sentence streamlined: <<<{{clipboard}}>>>
```

You can edit this to anything. Examples:

**Summarize clipboard:**
```
Summarize the following in 2 sentences: {{clipboard}}
```

**Translate to Spanish:**
```
Translate the following to Spanish: {{clipboard}}
```

**Fix grammar:**
```
Fix the grammar and make this professional: {{clipboard}}
```

**Custom interview helper:**
```
I am applying for a {{job_description}} role. My background: {{resume}}.
Answer this question concisely and compellingly: {{clipboard}}
```

### Response streaming

Responses stream character by character as they arrive from the API — you can watch the answer appear in real time, just like typing. This means you get the first words of a long answer almost instantly.

---

## Keyboard Shortcuts Reference

These are the five built-in system shortcuts seeded in every profile. You can change them to any trigger you prefer.

| Default Trigger | Action | What it does |
|----------------|--------|--------------|
| `jjj` | Store Clipboard | Saves clipboard → `job_description` |
| `rrr` | Store Clipboard | Saves clipboard → `resume` |
| `qqq` | LLM Query | Sends prompt to GPT, types response |
| `uuu` | Show UI | Opens the Mapping Manager window |
| `///` | Switch Profile | Opens the profile switcher popup |

---

## Configuration & Settings

**Settings** (click Settings button in the UI):
- **OpenAI API Key** — stored securely in the local SQLite database

**`.env` file** (project root):
```
OPENAI_API_KEY=sk-your-key-here
```

**Database location:**
```
~/.config/autofiller/mappings.db
```

---

## Data Storage

All data is stored locally in a SQLite database at `~/.config/autofiller/mappings.db`. Nothing is sent to any server except OpenAI API calls when you use an LLM Query trigger.

The database contains four tables:

| Table | Contents |
|-------|---------|
| `profiles` | Profile names |
| `mappings` | Shortcuts, expansions, actions — per profile |
| `session_vars` | Stored clipboard values — per profile |
| `settings` | Global settings (current profile, API key) |

---

## Tips & Tricks

**Use a prefix character** to avoid accidental triggers. Common choices:
- `#word` — hash prefix (e.g. `#email`, `#addr`, `#sig`)
- `;word` — semicolon prefix (e.g. `;email`, `;addr`)
- Triple letters for actions (e.g. `jjj`, `qqq`) — fast to type and very unlikely to appear normally

**Keep triggers short but memorable.** Two to four characters is the sweet spot. `#em` for email, `#ph` for phone number.

**Create a "job search" profile** with all your application snippets, and a separate "work" profile for your daily workflow. Switch between them with `///`.

**Chain store + query.** Copy your notes from a meeting, type `nnn` to store them as `notes`, then ask `qqq` (with `{{notes}}` in the prompt) to summarize action items.

**The UI window is non-destructive.** Closing the X just hides it. AutoFiller keeps running in the background. Type `uuu` to bring it back.

---

## Troubleshooting

**Triggers aren't firing**
- Confirm Accessibility permission is granted: System Settings → Privacy & Security → Accessibility
- Make sure the terminal or app running AutoFiller is in the Accessibility list
- Try restarting AutoFiller after granting permission

**`ModuleNotFoundError: No module named '_tkinter'`**
```bash
brew install python-tk@3.13   # replace 3.13 with your Python version
```

**`[ERROR: OPENAI_API_KEY not set]` appears when typing `qqq`**
- Open Settings (top right of the UI) and enter your OpenAI API key
- Or create a `.env` file in the project folder with `OPENAI_API_KEY=sk-...`

**Expansion types the wrong characters / garbled output**
- This can happen if the delay between keystrokes is too short on a slow system
- Try toggling typing emulation in Settings
- Backspace timing is set in `_do_expand` in `keyboard_expander.py`

**The app crashes on startup**
- Run `python keyboard_expander.py --ui` from the terminal to see the full error
- Most common cause: missing dependencies (`pip install pynput pyperclip openai python-dotenv`)

---

## License

MIT License — free to use, modify, and distribute.

---

*Built with Python, pynput, SQLite, Tkinter, and the OpenAI API.*
