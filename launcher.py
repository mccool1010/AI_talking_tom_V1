"""
AI Talking Tom - Launcher
A GUI launcher that starts the Python backend and Godot frontend.
Compile with: pyinstaller --onefile --windowed --icon=icon.ico launcher.py
"""

import subprocess
import sys
import os
import threading
import tkinter as tk
from tkinter import ttk, messagebox
import time
import signal


class TomLauncher:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("AI Talking Tom")
        self.root.geometry("480x400")
        self.root.resizable(False, False)
        self.root.configure(bg="#1a1a2e")

        self.backend_proc = None
        self.godot_proc = None
        self.running = False

        self._find_paths()
        self._build_ui()

    def _find_paths(self):
        """Find project paths relative to the launcher."""
        if getattr(sys, 'frozen', False):
            # Running as compiled .exe
            self.base_dir = os.path.dirname(sys.executable)
        else:
            # Running as script
            self.base_dir = os.path.dirname(os.path.abspath(__file__))

        self.backend_script = os.path.join(self.base_dir, "backend", "main.py")
        self.godot_project = os.path.join(self.base_dir, "godot")

        # Find Python
        self.python_exe = os.path.join(self.base_dir, "venv", "Scripts", "python.exe")
        if not os.path.exists(self.python_exe):
            self.python_exe = sys.executable

        # Find Godot
        self.godot_exe = None
        for f in os.listdir(self.base_dir):
            if f.startswith("Godot") and f.endswith(".exe") and "console" not in f:
                self.godot_exe = os.path.join(self.base_dir, f)
                break

    def _build_ui(self):
        """Build the launcher GUI."""
        # Title
        title_frame = tk.Frame(self.root, bg="#1a1a2e")
        title_frame.pack(pady=20)

        tk.Label(title_frame, text="🐱", font=("Segoe UI Emoji", 40),
                 bg="#1a1a2e", fg="white").pack()
        tk.Label(title_frame, text="AI Talking Tom",
                 font=("Segoe UI", 22, "bold"),
                 bg="#1a1a2e", fg="#e94560").pack()
        tk.Label(title_frame, text="Virtual AI Companion",
                 font=("Segoe UI", 10),
                 bg="#1a1a2e", fg="#888").pack()

        # Status indicators
        status_frame = tk.Frame(self.root, bg="#16213e", padx=20, pady=15)
        status_frame.pack(fill="x", padx=20, pady=10)

        self.backend_status = tk.Label(status_frame,
            text="● Backend: Stopped", font=("Segoe UI", 10),
            bg="#16213e", fg="#666", anchor="w")
        self.backend_status.pack(fill="x")

        self.godot_status = tk.Label(status_frame,
            text="● Godot: Stopped", font=("Segoe UI", 10),
            bg="#16213e", fg="#666", anchor="w")
        self.godot_status.pack(fill="x")

        self.dash_status = tk.Label(status_frame,
            text="● Dashboard: Available at localhost:8000", font=("Segoe UI", 10),
            bg="#16213e", fg="#666", anchor="w")
        self.dash_status.pack(fill="x")

        # Buttons
        btn_frame = tk.Frame(self.root, bg="#1a1a2e")
        btn_frame.pack(pady=20)

        self.launch_btn = tk.Button(btn_frame, text="▶  LAUNCH",
            font=("Segoe UI", 14, "bold"),
            bg="#e94560", fg="white", activebackground="#c73750",
            width=18, height=1, bd=0, cursor="hand2",
            command=self._launch)
        self.launch_btn.pack(pady=5)

        self.stop_btn = tk.Button(btn_frame, text="■  STOP",
            font=("Segoe UI", 11),
            bg="#333", fg="white", activebackground="#555",
            width=18, height=1, bd=0, cursor="hand2",
            command=self._stop, state="disabled")
        self.stop_btn.pack(pady=5)

        # Footer
        tk.Label(self.root, text="v1.0 — Press Launch to start all services",
                 font=("Segoe UI", 8), bg="#1a1a2e", fg="#555").pack(side="bottom", pady=5)

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _update_status(self, component, status, color):
        """Update a status label."""
        label = getattr(self, f"{component}_status")
        label.config(text=f"● {component.title()}: {status}", fg=color)

    def _launch(self):
        """Start backend and Godot."""
        if self.running:
            return

        self.running = True
        self.launch_btn.config(state="disabled", bg="#666")
        self.stop_btn.config(state="normal", bg="#e94560")

        # Start backend
        threading.Thread(target=self._start_backend, daemon=True).start()

        # Start Godot after a short delay
        self.root.after(2000, lambda: threading.Thread(
            target=self._start_godot, daemon=True).start())

    def _start_backend(self):
        """Start the Python backend."""
        if not os.path.exists(self.backend_script):
            self.root.after(0, lambda: messagebox.showerror(
                "Error", f"Backend not found:\n{self.backend_script}"))
            return

        self.root.after(0, lambda: self._update_status("backend", "Starting...", "#ffaa00"))

        try:
            # Output goes to a file: an unread PIPE fills up and freezes the backend.
            log_dir = os.path.join(self.base_dir, "runtime", "logs")
            os.makedirs(log_dir, exist_ok=True)
            self.backend_log = open(os.path.join(log_dir, "backend_console.log"), "w", encoding="utf-8")
            self.backend_proc = subprocess.Popen(
                [self.python_exe, self.backend_script],
                cwd=os.path.join(self.base_dir, "backend"),
                stdout=self.backend_log,
                stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            self.root.after(0, lambda: self._update_status("backend", "Running", "#00ff88"))
            self.root.after(0, lambda: self._update_status("dash", "Live at localhost:8000", "#00ff88"))
            self.backend_proc.wait()
        except Exception as e:
            self.root.after(0, lambda: self._update_status("backend", f"Error: {e}", "#ff4444"))

        self.root.after(0, lambda: self._update_status("backend", "Stopped", "#666"))

    def _start_godot(self):
        """Start Godot with the project."""
        if not self.godot_exe or not os.path.exists(self.godot_exe):
            self.root.after(0, lambda: self._update_status("godot", "Godot exe not found", "#ff4444"))
            return

        self.root.after(0, lambda: self._update_status("godot", "Starting...", "#ffaa00"))

        try:
            self.godot_proc = subprocess.Popen(
                [self.godot_exe, "--path", self.godot_project],
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            self.root.after(0, lambda: self._update_status("godot", "Running", "#00ff88"))
            self.godot_proc.wait()
        except Exception as e:
            self.root.after(0, lambda: self._update_status("godot", f"Error: {e}", "#ff4444"))

        self.root.after(0, lambda: self._update_status("godot", "Stopped", "#666"))

    def _stop(self):
        """Stop all processes."""
        self.running = False
        for proc in [self.godot_proc, self.backend_proc]:
            if proc and proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
        if getattr(self, "backend_log", None):
            self.backend_log.close()
            self.backend_log = None

        self._update_status("backend", "Stopped", "#666")
        self._update_status("godot", "Stopped", "#666")
        self._update_status("dash", "Available at localhost:8000", "#666")
        self.launch_btn.config(state="normal", bg="#e94560")
        self.stop_btn.config(state="disabled", bg="#333")

    def _on_close(self):
        """Clean up on window close."""
        self._stop()
        self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = TomLauncher()
    app.run()
