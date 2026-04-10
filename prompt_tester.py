#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import json
import os
from openai import OpenAI

# File name for persistent configuration
CONFIG_FILE = "prompt_tester_config.json"

# Default models
DEFAULT_MODELS = ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo"]

class PromptTitleDialog(tk.Toplevel):
    """Dialog to ask for a title when saving a prompt."""
    def __init__(self, parent, title="Save Prompt", prompt="Enter title for this configuration:"):
        super().__init__(parent)
        self.title(title)
        self.geometry("300x150")
        self.resizable(False, False)
        self.grab_set()
        self.result = None

        ttk.Label(self, text=prompt, padding=10).pack()
        self.entry = ttk.Entry(self, width=30)
        self.entry.pack(pady=5)
        self.entry.focus_set()

        btn_frame = ttk.Frame(self, padding=10)
        btn_frame.pack()
        ttk.Button(btn_frame, text="Save", command=self._on_save).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self.destroy).pack(side="left", padx=5)

        self.bind("<Return>", lambda e: self._on_save())
        self.bind("<Escape>", lambda e: self.destroy())

    def _on_save(self):
        val = self.entry.get().strip()
        if val:
            self.result = val
            self.destroy()
        else:
            messagebox.showwarning("Warning", "Title cannot be empty.")

class PromptTesterApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("OpenAI Prompt Tester")
        self.geometry("800x700")
        self.minsize(600, 500)
        
        # Determine the full path to the config file (same directory as the script)
        self.config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), CONFIG_FILE)
        
        # Load existing configuration
        self.config = self._load_config()
        
        self.style = ttk.Style(self)
        self.style.configure("TLabel", font=("Inter", 11))
        self.style.configure("TButton", font=("Inter", 11, "bold"))
        self.style.configure("Header.TLabel", font=("Inter", 14, "bold"))
        self.style.configure("Status.TLabel", font=("Inter", 9), foreground="gray")

        self._build_ui()
        self._add_traces()

    def _add_traces(self):
        # Trace for API key change
        self.api_key_var.trace_add("write", self._on_api_key_change)
        # Trace for Model selection change
        self.model_var.trace_add("write", self._on_model_change)
        self._fetch_models_timer = None

    def _load_config(self):
        """Loads the configuration from a JSON file."""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"api_key": "", "model": DEFAULT_MODELS[0], "saved_prompts": {}}

    def _save_config(self):
        """Saves current API key, model and saved prompts to the JSON file."""
        config = {
            "api_key": self.api_key_var.get().strip(),
            "model": self.model_var.get(),
            "saved_prompts": self.config.get("saved_prompts", {})
        }
        try:
            with open(self.config_path, "w") as f:
                json.dump(config, f, indent=4)
        except Exception:
            pass
        
    def _build_ui(self):
        main_container = ttk.Frame(self, padding="20")
        main_container.pack(fill="both", expand=True)

        # Title
        header = ttk.Label(main_container, text="OpenAI Prompt Tester", style="Header.TLabel")
        header.pack(pady=(0, 20), anchor="w")

        # API Key Section
        key_frame = ttk.Frame(main_container)
        key_frame.pack(fill="x", pady=(0, 15))
        
        ttk.Label(key_frame, text="OpenAI API Key:").pack(side="left", padx=(0, 10))
        self.api_key_var = tk.StringVar(value=self.config.get("api_key", ""))
        self.api_key_entry = ttk.Entry(key_frame, textvariable=self.api_key_var, show="*", width=50)
        self.api_key_entry.pack(side="left", fill="x", expand=True)
        
        self.show_key_var = tk.BooleanVar(value=False)
        self.show_key_btn = ttk.Checkbutton(key_frame, text="Show", variable=self.show_key_var, command=self._toggle_key_visibility)
        self.show_key_btn.pack(side="left", padx=(10, 0))

        # Model Selection
        model_frame = ttk.Frame(main_container)
        model_frame.pack(fill="x", pady=(0, 15))
        
        ttk.Label(model_frame, text="Model:").pack(side="left", padx=(0, 10))
        saved_model = self.config.get("model", DEFAULT_MODELS[0])
        self.model_var = tk.StringVar(value=saved_model)
        self.model_cb = ttk.Combobox(model_frame, textvariable=self.model_var, values=DEFAULT_MODELS, state="readonly", width=20)
        self.model_cb.pack(side="left")
        
        self.model_status_var = tk.StringVar()
        self.model_status_label = ttk.Label(model_frame, textvariable=self.model_status_var, style="Status.TLabel")
        self.model_status_label.pack(side="left", padx=(10, 0))

        # --- Saved Prompts Section ---
        history_frame = ttk.Frame(main_container)
        history_frame.pack(fill="x", pady=(10, 15))
        
        ttk.Label(history_frame, text="Saved Prompts:").pack(side="left", padx=(0, 10))
        self.saved_prompt_var = tk.StringVar()
        self.saved_prompt_cb = ttk.Combobox(
            history_frame, textvariable=self.saved_prompt_var, 
            values=sorted(self.config.get("saved_prompts", {}).keys()), 
            state="readonly", width=30
        )
        self.saved_prompt_cb.pack(side="left")
        self.saved_prompt_cb.bind("<<ComboboxSelected>>", self._on_history_select)
        
        ttk.Button(history_frame, text="Save Current", width=12, command=self._on_save_preset).pack(side="left", padx=(10, 0))
        ttk.Button(history_frame, text="Delete", width=8, command=self._on_delete_preset).pack(side="left", padx=(5, 0))
        
        # --- Prompts UI ---
        ttk.Separator(main_container, orient="horizontal").pack(fill="x", pady=(0, 15))

        # System Prompt
        ttk.Label(main_container, text="System Prompt:").pack(anchor="w", pady=(10, 5))
        self.system_prompt_text = tk.Text(main_container, height=4, font=("Inter", 11), padx=10, pady=10, undo=True)
        self.system_prompt_text.pack(fill="x", pady=(0, 10))
        self.system_prompt_text.insert("1.0", "You are a helpful and concise assistant.")

        # User Prompt
        ttk.Label(main_container, text="User Prompt:").pack(anchor="w", pady=(10, 5))
        self.user_prompt_text = tk.Text(main_container, height=6, font=("Inter", 11), padx=10, pady=10, undo=True)
        self.user_prompt_text.pack(fill="x", pady=(0, 15))

        # Actions
        action_frame = ttk.Frame(main_container)
        action_frame.pack(fill="x", pady=(0, 20))
        
        self.run_btn = ttk.Button(action_frame, text="Run Prompt", command=self._on_run_click)
        self.run_btn.pack(side="right")
        
        self.status_var = tk.StringVar(value="Ready")
        self.status_label = ttk.Label(action_frame, textvariable=self.status_var, foreground="gray")
        self.status_label.pack(side="left")

        # Results Label
        ttk.Label(main_container, text="Response:").pack(anchor="w", pady=(10, 5))
        
        # Result Display (Scrollable)
        result_container = ttk.Frame(main_container)
        result_container.pack(fill="both", expand=True)
        
        self.result_text = tk.Text(result_container, font=("Inter", 11), padx=10, pady=10, state="disabled", wrap="word")
        scrollbar = ttk.Scrollbar(result_container, orient="vertical", command=self.result_text.yview)
        self.result_text.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side="right", fill="y")
        self.result_text.pack(side="left", fill="both", expand=True)

    def _toggle_key_visibility(self):
        if self.show_key_var.get():
            self.api_key_entry.config(show="")
        else:
            self.api_key_entry.config(show="*")

    def _on_api_key_change(self, *args):
        """Called when the API key text field changes."""
        key = self.api_key_var.get().strip()
        
        # Debounce the API call to avoid spamming while typing
        if self._fetch_models_timer:
            self.after_cancel(self._fetch_models_timer)
            
        if len(key) > 20: # Only fetch if it looks like a real key (e.g., sk-...)
            self._fetch_models_timer = self.after(800, lambda: self._start_model_fetch(key))
        else:
            self.model_status_var.set("")
            
        self._save_config()

    def _on_model_change(self, *args):
        """Called when the model selection changes."""
        self._save_config()

    def _on_history_select(self, *args):
        """Called when a saved prompt is selected from the dropdown."""
        title = self.saved_prompt_var.get()
        presets = self.config.get("saved_prompts", {})
        if title in presets:
            data = presets[title]
            if "model" in data:
                self.model_var.set(data["model"])
            if "system" in data:
                self.system_prompt_text.delete("1.0", "end")
                self.system_prompt_text.insert("1.0", data["system"])
            if "user" in data:
                self.user_prompt_text.delete("1.0", "end")
                self.user_prompt_text.insert("1.0", data["user"])
            self.status_var.set(f"Loaded preset: {title}")

    def _on_save_preset(self):
        """Asks for a title and saves the current prompt configuration."""
        dialog = PromptTitleDialog(self)
        self.wait_window(dialog)
        
        if dialog.result:
            title = dialog.result
            presets = self.config.get("saved_prompts", {})
            presets[title] = {
                "model": self.model_var.get(),
                "system": self.system_prompt_text.get("1.0", "end-1c").strip(),
                "user": self.user_prompt_text.get("1.0", "end-1c").strip()
            }
            self.config["saved_prompts"] = presets
            self._save_config()
            
            # Update dropdown values
            titles = sorted(presets.keys())
            self.saved_prompt_cb.config(values=titles)
            self.saved_prompt_var.set(title)
            self.status_var.set(f"Saved preset: {title}")

    def _on_delete_preset(self):
        """Deletes the currently selected preset."""
        title = self.saved_prompt_var.get()
        if not title:
            return
            
        if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete '{title}'?"):
            presets = self.config.get("saved_prompts", {})
            if title in presets:
                del presets[title]
                self.config["saved_prompts"] = presets
                self._save_config()
                
                # Update dropdown values
                titles = sorted(presets.keys())
                self.saved_prompt_cb.config(values=titles)
                self.saved_prompt_var.set("")
                self.status_var.set(f"Deleted preset: {title}")

    def _start_model_fetch(self, api_key):
        self.model_status_var.set("Fetching models...")
        thread = threading.Thread(target=self._async_fetch_models, args=(api_key,), daemon=True)
        thread.start()

    def _async_fetch_models(self, api_key):
        try:
            client = OpenAI(api_key=api_key)
            # Fetch all models from OpenAI
            all_models = client.models.list()
            
            # Filter for GPT models only, as those are the chat ones
            gpt_models = sorted([
                m.id for m in all_models 
                if m.id.startswith("gpt-") or "gpt-3.5" in m.id or "gpt-4" in m.id
            ], reverse=True)
            
            if not gpt_models:
                # Fallback to some defaults if filtering returned nothing for some reason
                gpt_models = DEFAULT_MODELS
                
            self.after(0, lambda: self._update_model_list(gpt_models))
        except Exception as e:
            # We don't want to show a popup error here as it's just background fetching
            self.after(0, lambda: self.model_status_var.set("Invalid Key"))

    def _update_model_list(self, model_ids):
        current_model = self.model_var.get()
        self.model_cb.config(values=model_ids)
        
        if current_model not in model_ids:
            # If current model is not in the list, pick the first one from the new list
            # which is likely the most recent gpt-4o or equivalent
            if model_ids:
                self.model_var.set(model_ids[0])
        
        self.model_status_var.set(f"{len(model_ids)} models available")

    def _on_run_click(self):
        api_key = self.api_key_var.get().strip()
        system_prompt = self.system_prompt_text.get("1.0", "end-1c").strip()
        user_prompt = self.user_prompt_text.get("1.0", "end-1c").strip()
        model = self.model_var.get()
        
        if not api_key:
            messagebox.showerror("Error", "Please provide an OpenAI API Key.")
            return
        if not user_prompt:
            messagebox.showwarning("Warning", "User prompt is empty.")
            return
            
        self._set_loading(True)
        
        # Run API call in a separate thread
        thread = threading.Thread(target=self._run_openai_query, args=(api_key, model, system_prompt, user_prompt))
        thread.daemon = True
        thread.start()

    def _set_loading(self, loading):
        if loading:
            self.run_btn.config(state="disabled")
            self.status_var.set("Running...")
            self.result_text.config(state="normal")
            self.result_text.delete("1.0", "end")
            self.result_text.insert("end", "Generating response...")
            self.result_text.config(state="disabled")
        else:
            self.run_btn.config(state="normal")
            self.status_var.set("Ready")

    def _run_openai_query(self, api_key, model, system_prompt, user_prompt):
        try:
            client = OpenAI(api_key=api_key)
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": user_prompt})
            
            response = client.chat.completions.create(
                model=model,
                messages=messages
            )
            content = response.choices[0].message.content
            self.after(0, lambda: self._update_result(content))
        except Exception as e:
            self.after(0, lambda: self._handle_error(str(e)))
        finally:
            self.after(0, lambda: self._set_loading(False))

    def _update_result(self, content):
        self.result_text.config(state="normal")
        self.result_text.delete("1.0", "end")
        self.result_text.insert("end", content)
        self.result_text.config(state="disabled")

    def _handle_error(self, error_msg):
        self.result_text.config(state="normal")
        self.result_text.delete("1.0", "end")
        self.result_text.insert("end", f"ERROR:\n{error_msg}")
        self.result_text.config(state="disabled")
        messagebox.showerror("API Error", f"An error occurred while calling the OpenAI API:\n\n{error_msg}")

if __name__ == "__main__":
    app = PromptTesterApp()
    app.mainloop()
