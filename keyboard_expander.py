#!/usr/bin/env python3
"""
Keyboard text expander with LLM integration and profile support.
Requires: pip install pynput pyperclip openai python-dotenv fpdf2

Usage:
  python keyboard_expander.py         # daemon only
  python keyboard_expander.py --ui    # daemon + mappings manager window
"""

import os
import sys
import time
import threading
import subprocess
from datetime import datetime
from pathlib import Path
import pyperclip
from dotenv import load_dotenv
from pynput import keyboard
from pynput.keyboard import Key, Controller

load_dotenv()

import db

MAX_BUFFER = 50

_buffer = ""
_controller = Controller()
_lock = threading.Lock()
_triggers: dict[str, dict] = {}
_triggers_lock = threading.Lock()
_session: dict[str, str] = {}
_show_ui_callback = None
_switch_profile_callback = None
_llm_busy = False
_llm_busy_lock = threading.Lock()


def reload_triggers() -> None:
    global _triggers
    with _triggers_lock:
        _triggers = db.get_all()


def reload_session() -> None:
    global _session
    _session.clear()
    _session.update(db.get_session_vars())


def on_profile_changed() -> None:
    """Call after any profile switch to resync triggers and session."""
    reload_triggers()
    reload_session()


# ── action handlers ──────────────────────────────────────────────────────────

def _human_type(text: str) -> None:
    """Type text character by character at human-like speed."""
    import random
    for char in text:
        _controller.type(char)
        time.sleep(random.uniform(0.04, 0.09))


def _type_output(text: str) -> None:
    """Type output using either human-like emulation or direct typing."""
    if db.get_setting("TYPING_EMULATION_ENABLED", "1") == "1":
        _human_type(text)
    else:
        _controller.type(text)


def _notify_macos(title: str, message: str) -> None:
    """Show a blocking alert (for errors)."""
    safe_title = title.replace('"', '\\"')
    safe_msg = message.replace('"', '\\"')
    subprocess.run(
        ["osascript", "-e", f'display alert "{safe_title}" message "{safe_msg}"'],
        check=False,
    )


def _notify_macos_banner(title: str, message: str) -> None:
    """Show a system notification banner that auto-dismisses."""
    safe_title = title.replace('"', '\\"')
    safe_msg = message.replace('"', '\\"')
    subprocess.run(
        ["osascript", "-e", f'display notification "{safe_msg}" with title "{safe_title}"'],
        check=False,
    )


_PDF_CHAR_MAP = {
    "\u2014": "-",    # em dash
    "\u2013": "-",    # en dash
    "\u2012": "-",    # figure dash
    "\u2010": "-",    # hyphen
    "\u2011": "-",    # non-breaking hyphen
    "\u2018": "'",    # left single quote
    "\u2019": "'",    # right single quote
    "\u201a": ",",    # single low quote
    "\u201c": '"',    # left double quote
    "\u201d": '"',    # right double quote
    "\u2026": "...",  # ellipsis
    "\u00a0": " ",    # non-breaking space
    "\u2022": "*",    # bullet
}


def _save_pdf(text: str, filepath: str) -> None:
    for char, replacement in _PDF_CHAR_MAP.items():
        text = text.replace(char, replacement)
    text = text.encode("latin-1", errors="replace").decode("latin-1")

    from fpdf import FPDF
    pdf = FPDF()
    pdf.set_margins(25, 25, 25)
    pdf.set_auto_page_break(auto=True, margin=25)
    pdf.add_page()
    pdf.set_font("Helvetica", size=11)
    pdf.multi_cell(0, 6, text)
    pdf.output(filepath)


def _do_expand(trigger: str, expansion: str) -> None:
    time.sleep(0.05)
    for _ in range(len(trigger)):
        _controller.tap(Key.backspace)
        time.sleep(0.02)
    _type_output(expansion)


def _do_store_clipboard(trigger: str, var_name: str) -> None:
    text = pyperclip.paste()
    _session[var_name] = text
    db.set_session_var(var_name, text)
    time.sleep(0.05)
    for _ in range(len(trigger)):
        _controller.tap(Key.backspace)
        time.sleep(0.02)
    _notify_macos_banner(f"Stored: {var_name}", f"{len(text)} chars saved to session")
    print(f"[autofiller] stored {len(text)} chars → session['{var_name}']")


def _do_llm_query(trigger: str, prompt_template: str) -> None:
    global _llm_busy
    with _llm_busy_lock:
        if _llm_busy:
            return
        _llm_busy = True
    try:
        _do_llm_query_inner(trigger, prompt_template)
    finally:
        with _llm_busy_lock:
            _llm_busy = False


def _do_llm_query_inner(trigger: str, prompt_template: str) -> None:
    clipboard_text = pyperclip.paste()
    prompt = prompt_template.replace("{{clipboard}}", clipboard_text)
    for var_name, value in _session.items():
        prompt = prompt.replace(f"{{{{{var_name}}}}}", value)

    time.sleep(0.05)
    for _ in range(len(trigger)):
        _controller.tap(Key.backspace)
        time.sleep(0.02)

    api_key = db.get_setting("OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        _type_output("[ERROR: OPENAI_API_KEY not set]")
        return

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        stream = client.chat.completions.create(
            model=db.get_setting("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[{"role": "user", "content": prompt}],
            stream=True,
        )
        # Collect full response before pasting — avoids dropped spaces from
        # rapid pynput Controller.type() calls on macOS.
        response = "".join(
            chunk.choices[0].delta.content or "" for chunk in stream
        )
        if response:
            _type_output(response)
    except Exception as e:
        _type_output(f"[LLM ERROR: {e}]")


def _do_gen_cover_letter(trigger: str, prompt_template: str) -> None:
    global _llm_busy
    with _llm_busy_lock:
        if _llm_busy:
            return
        _llm_busy = True
    try:
        _do_gen_cover_letter_inner(trigger, prompt_template)
    finally:
        with _llm_busy_lock:
            _llm_busy = False


def _do_gen_cover_letter_inner(trigger: str, prompt_template: str) -> None:
    today = datetime.now().strftime("%B %d, %Y")
    prompt = prompt_template.replace("{{date}}", today)
    for var_name, value in _session.items():
        prompt = prompt.replace(f"{{{{{var_name}}}}}", value)

    time.sleep(0.05)
    for _ in range(len(trigger)):
        _controller.tap(Key.backspace)
        time.sleep(0.02)

    api_key = db.get_setting("OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        _notify_macos("AutoFiller Error", "OPENAI_API_KEY not set")
        return

    _notify_macos_banner("Cover Letter", "Generating...")

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=db.get_setting("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.choices[0].message.content or ""

        filename = "coverletter.pdf"
        filepath = Path.home() / "Downloads" / filename
        filepath.unlink(missing_ok=True)
        _save_pdf(text, str(filepath))
        pyperclip.copy(text)

        _notify_macos_banner("Cover Letter Generated", f"Saved as {filename} · Copied to clipboard")
        if db.get_setting("COVERLETTER_OPEN_FINDER", "1") == "1":
            subprocess.run(["open", str(Path.home() / "Downloads")], check=False)
    except Exception as e:
        _notify_macos("AutoFiller Error", str(e))


def _do_gen_resume(trigger: str, prompt_template: str) -> None:
    global _llm_busy
    with _llm_busy_lock:
        if _llm_busy:
            return
        _llm_busy = True
    try:
        _do_gen_resume_inner(trigger, prompt_template)
    finally:
        with _llm_busy_lock:
            _llm_busy = False


def _do_gen_resume_inner(trigger: str, prompt_template: str) -> None:
    prompt = prompt_template
    for var_name, value in _session.items():
        prompt = prompt.replace(f"{{{{{var_name}}}}}", value)

    time.sleep(0.05)
    for _ in range(len(trigger)):
        _controller.tap(Key.backspace)
        time.sleep(0.02)

    api_key = db.get_setting("OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        _notify_macos("AutoFiller Error", "OPENAI_API_KEY not set")
        return

    _notify_macos_banner("Resume", "Generating...")

    try:
        import json
        from openai import OpenAI
        from generate_resume import generate_resume_pdf

        client = OpenAI(api_key=api_key)

        system_prompt = (
            "You are a professional resume generator. "
            "Output your response strictly as a JSON object matching the following structure. "
            "DO NOT include markdown block characters like ```json or ```. Just the raw JSON.\n\n"
            "{\n"
            '  "name": "Applicant Name",\n'
            '  "contact": ["City, State", "Phone", "Email"],\n'
            '  "links": ["LinkedIn", "GitHub", "Portfolio"],\n'
            '  "summary": "Brief professional summary.",\n'
            '  "experience": [\n'
            '    {"title": "Job Title", "company": "Company Name", "date": "Date Range", "description": ["Bullet point 1", "Bullet point 2"]}\n'
            '  ],\n'
            '  "education": [\n'
            '    {"degree": "Degree", "institution": "University Name", "date": "Date Range", "details": ["Detail 1"]}\n'
            '  ],\n'
            '  "skills": [\n'
            '    {"category": "Skill Category:", "items": "Skill 1, Skill 2"}\n'
            '  ]\n'
            "}"
        )

        response = client.chat.completions.create(
            model=db.get_setting("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        text = response.choices[0].message.content or ""

        try:
            resume_data = json.loads(text)
        except json.JSONDecodeError as e:
            _notify_macos("AutoFiller Error", f"Failed to parse resume JSON: {e}")
            return

        filename = "resume_generated.pdf"
        filepath = Path.home() / "Downloads" / filename
        filepath.unlink(missing_ok=True)

        generate_resume_pdf(resume_data, str(filepath))
        pyperclip.copy(text)

        _notify_macos_banner("Resume Generated", f"Saved as {filename} · JSON Copied to clipboard")
        if db.get_setting("RESUME_OPEN_FINDER", "1") == "1":
            subprocess.run(["open", str(Path.home() / "Downloads")], check=False)
    except Exception as e:
        _notify_macos("AutoFiller Error", str(e))


def _do_show_ui(trigger: str) -> None:
    time.sleep(0.05)
    for _ in range(len(trigger)):
        _controller.tap(Key.backspace)
        time.sleep(0.02)
    if _show_ui_callback:
        _show_ui_callback()


def _do_switch_profile(trigger: str) -> None:
    time.sleep(0.05)
    for _ in range(len(trigger)):
        _controller.tap(Key.backspace)
        time.sleep(0.02)
    if _switch_profile_callback:
        _switch_profile_callback()


# ── keyboard listener ─────────────────────────────────────────────────────────

def _on_press(key):
    global _buffer

    try:
        char = key.char
    except AttributeError:
        char = None

    with _lock:
        if key in (Key.enter, Key.tab, Key.esc,
                   Key.left, Key.right, Key.up, Key.down,
                   Key.home, Key.end, Key.page_up, Key.page_down):
            _buffer = ""
            return

        if key == Key.backspace:
            _buffer = _buffer[:-1]
            return

        if char is None:
            return

        _buffer = (_buffer + char)[-MAX_BUFFER:]

        with _triggers_lock:
            current = dict(_triggers)

        match = None
        for shortcut in sorted(current, key=len, reverse=True):
            if _buffer.endswith(shortcut):
                match = shortcut
                break

        if not match:
            return

        entry = current[match]
        action = entry["action"]
        expansion = entry["expansion"]
        _buffer = ""

        if action == "expand":
            t = threading.Thread(target=_do_expand, args=(match, expansion), daemon=True)
        elif action == "store_clipboard":
            t = threading.Thread(target=_do_store_clipboard, args=(match, expansion), daemon=True)
        elif action == "llm_query":
            t = threading.Thread(target=_do_llm_query, args=(match, expansion), daemon=True)
        elif action == "gen_cover_letter":
            t = threading.Thread(target=_do_gen_cover_letter, args=(match, expansion), daemon=True)
        elif action == "gen_resume":
            t = threading.Thread(target=_do_gen_resume, args=(match, expansion), daemon=True)
        elif action == "show_ui":
            t = threading.Thread(target=_do_show_ui, args=(match,), daemon=True)
        elif action == "switch_profile":
            t = threading.Thread(target=_do_switch_profile, args=(match,), daemon=True)
        else:
            return

        t.start()


def run_listener():
    with keyboard.Listener(on_press=_on_press) as listener:
        listener.join()


# ── entry point ───────────────────────────────────────────────────────────────

def main():
    global _show_ui_callback, _switch_profile_callback

    db.init_db()
    reload_session()
    reload_triggers()

    if "--ui" in sys.argv:
        listener_thread = threading.Thread(target=run_listener, daemon=True)
        listener_thread.start()

        from ui import ManagerWindow
        app = ManagerWindow(
            on_profile_changed=on_profile_changed,
            get_session=db.get_session_vars,
        )
        _show_ui_callback = app.show_window
        _switch_profile_callback = app.show_profile_switcher
        print("AutoFiller running with UI. Close the window to quit.")
        app.mainloop()
    else:
        print("Keyboard expander running. Press Ctrl+C to quit.")
        print(f"Profile: {db.get_current_profile_name()}")
        print("Shortcuts:", list(_triggers.keys()))
        print("Run with --ui to open the mappings manager.")
        try:
            run_listener()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
