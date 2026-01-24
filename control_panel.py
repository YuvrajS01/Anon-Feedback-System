#!/usr/bin/env python3
"""
GUI Control Panel for Anonymous Student Feedback System.

A Tkinter-based application that provides a control panel for:
- Starting/stopping the Flask server
- Managing teacher-subject combos
- Generating and exporting tokens
- Database management

Run with: python control_panel.py
"""

import os
import sys
import json
import socket
import signal
import random
import string
import threading
import subprocess
import webbrowser
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

from database import init_db, add_tokens, get_token_stats, reset_database
from config import CONFIG_FILE, load_combos, save_combos, DATABASE_PATH, load_semester_session, save_semester_session, AVAILABLE_BRANCHES, load_templates, save_template, delete_template, apply_template


class ModernStyle:
    """Modern dark theme colors and styles - Simple Edition."""
    # Slate Theme
    BG_DARK = "#0f172a"      # Slate 900
    BG_CARD = "#1e293b"      # Slate 800
    BG_INPUT = "#334155"     # Slate 700
    
    # Indigo Accents
    ACCENT = "#6366f1"       # Indigo 500
    ACCENT_HOVER = "#4f46e5" # Indigo 600
    
    # Functional
    SUCCESS = "#10b981"
    WARNING = "#f59e0b"
    ERROR = "#FF1744"        # Red
    
    # Typography
    TEXT_PRIMARY = "#FFFFFF"
    TEXT_SECONDARY = "#A0A0A0"
    TEXT_MUTED = "#555555"
    
    # Borders
    BORDER = "#333333"


class ControlPanel:
    """Main control panel application."""
    
    def __init__(self, root):
        self.root = root
        self.root.title("📊 Feedback System Control Panel")
        self.root.geometry("700x800")
        self.root.configure(bg=ModernStyle.BG_DARK)
        self.root.resizable(True, True)
        self.root.minsize(600, 700)
        
        # Server process
        self.server_process = None
        self.server_running = False
        
        # Initialize database
        init_db()
        
        # Create UI
        self.create_styles()
        self.create_ui()
        
        # Load initial data
        self.refresh_combos()
        self.update_token_stats()
        self.update_server_status()
        
        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # Start auto-refresh timer (every 5 seconds)
        self.start_auto_refresh()
    
    def create_styles(self):
        """Configure ttk styles."""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure frame style
        style.configure("Dark.TFrame", background=ModernStyle.BG_DARK)
        style.configure("Card.TFrame", background=ModernStyle.BG_CARD)
        
        # Configure label style
        style.configure("Dark.TLabel", 
                       background=ModernStyle.BG_DARK, 
                       foreground=ModernStyle.TEXT_PRIMARY,
                       font=('Segoe UI', 10))
        
        style.configure("Card.TLabel", 
                       background=ModernStyle.BG_CARD, 
                       foreground=ModernStyle.TEXT_PRIMARY,
                       font=('Segoe UI', 10))
        
        style.configure("Title.TLabel",
                       background=ModernStyle.BG_DARK,
                       foreground=ModernStyle.ACCENT,
                       font=('Segoe UI', 16, 'bold'))
        
        style.configure("Section.TLabel",
                       background=ModernStyle.BG_CARD,
                       foreground=ModernStyle.TEXT_PRIMARY,
                       font=('Segoe UI', 12, 'bold'))
        
        style.configure("Muted.TLabel",
                       background=ModernStyle.BG_CARD,
                       foreground=ModernStyle.TEXT_MUTED,
                       font=('Segoe UI', 9))
        
        # Configure button style
        style.configure("Accent.TButton",
                       background=ModernStyle.ACCENT,
                       foreground=ModernStyle.TEXT_PRIMARY,  # White text on Indigo
                       font=('Segoe UI', 10, 'bold'),
                       padding=(15, 8))
        
        style.map("Accent.TButton",
                 background=[('active', ModernStyle.ACCENT_HOVER)])
        
        style.configure("Secondary.TButton",
                       background=ModernStyle.BG_INPUT,
                       foreground=ModernStyle.TEXT_PRIMARY,
                       font=('Segoe UI', 10),
                       padding=(12, 6))
        
        style.configure("Danger.TButton",
                       background=ModernStyle.ERROR,
                       foreground=ModernStyle.TEXT_PRIMARY,
                       font=('Segoe UI', 10),
                       padding=(12, 6))
        
        # Configure entry style
        style.configure("Dark.TEntry",
                       fieldbackground=ModernStyle.BG_INPUT,
                       foreground=ModernStyle.TEXT_PRIMARY,
                       insertcolor=ModernStyle.TEXT_PRIMARY,
                       borderwidth=0,
                       relief="flat")
        
        # Configure spinbox style
        style.configure("Dark.TSpinbox",
                       fieldbackground=ModernStyle.BG_INPUT,
                       foreground=ModernStyle.TEXT_PRIMARY,
                       arrowcolor=ModernStyle.TEXT_PRIMARY)
    
    def create_ui(self):
        """Create the main UI layout."""
        # Main container with padding
        main_frame = ttk.Frame(self.root, style="Dark.TFrame", padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Scrollable canvas
        canvas = tk.Canvas(main_frame, bg=ModernStyle.BG_DARK, highlightthickness=0)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas, style="Dark.TFrame")
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Pack scrollbar and canvas
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        
        # Bind mousewheel
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        # Title
        title_frame = ttk.Frame(scrollable_frame, style="Dark.TFrame")
        title_frame.pack(fill=tk.X, pady=(0, 20))
        
        ttk.Label(title_frame, text="📊 Feedback System Control Panel", 
                 style="Title.TLabel").pack(side=tk.LEFT)
        
        # === Server Status Section ===
        self.create_server_section(scrollable_frame)
        
        # === Academic Period Section ===
        self.create_academic_period_section(scrollable_frame)
        
        # === Template Management Section ===
        self.create_template_section(scrollable_frame)
        
        # === Teacher-Subject Combos Section ===
        self.create_combos_section(scrollable_frame)
        
        # === Token Management Section ===
        self.create_tokens_section(scrollable_frame)
        
        # === Database Section ===
        self.create_database_section(scrollable_frame)
    
    def create_card(self, parent, title):
        """Create a card-style frame with title."""
        card = ttk.Frame(parent, style="Card.TFrame", padding=15)
        card.pack(fill=tk.X, pady=(0, 15))
        
        # Configure card appearance
        card.configure(relief="flat")
        
        # Title
        ttk.Label(card, text=title, style="Section.TLabel").pack(anchor=tk.W, pady=(0, 10))
        
        return card
    
    def create_server_section(self, parent):
        """Create server control section."""
        card = self.create_card(parent, "🖥️ Server Control")
        
        # Status row
        status_frame = ttk.Frame(card, style="Card.TFrame")
        status_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(status_frame, text="Status:", style="Card.TLabel").pack(side=tk.LEFT)
        self.status_label = ttk.Label(status_frame, text="● Stopped", 
                                      style="Card.TLabel", foreground=ModernStyle.ERROR)
        self.status_label.pack(side=tk.LEFT, padx=(10, 0))
        
        # URL row
        url_frame = ttk.Frame(card, style="Card.TFrame")
        url_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.local_ip = self.get_local_ip()
        
        ttk.Label(url_frame, text="Local URL:", style="Muted.TLabel").pack(side=tk.LEFT)
        self.url_label = ttk.Label(url_frame, text=f"http://{self.local_ip}:5000", 
                                   style="Card.TLabel", foreground=ModernStyle.ACCENT)
        self.url_label.pack(side=tk.LEFT, padx=(10, 0))
        
        # Buttons row
        btn_frame = ttk.Frame(card, style="Card.TFrame")
        btn_frame.pack(fill=tk.X, pady=(5, 0))
        
        self.start_btn = tk.Button(btn_frame, text="▶ Start Server", 
                                   command=self.start_server,
                                   bg=ModernStyle.SUCCESS, fg="white",
                                   font=('Segoe UI', 10, 'bold'),
                                   relief="flat", padx=15, pady=8, cursor="hand2")
        self.start_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.stop_btn = tk.Button(btn_frame, text="■ Stop Server",
                                  command=self.stop_server,
                                  bg=ModernStyle.ERROR, fg="white",
                                  font=('Segoe UI', 10, 'bold'),
                                  relief="flat", padx=15, pady=8, cursor="hand2",
                                  state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        open_btn = tk.Button(btn_frame, text="🌐 Open in Browser",
                            command=self.open_browser,
                            bg=ModernStyle.BG_INPUT, fg="white",
                            font=('Segoe UI', 10),
                            relief="flat", padx=15, pady=8, cursor="hand2")
        open_btn.pack(side=tk.LEFT)
        
        admin_btn = tk.Button(btn_frame, text="🔐 Admin Panel",
                             command=self.open_admin,
                             bg=ModernStyle.BG_INPUT, fg="white",
                             font=('Segoe UI', 10),
                             relief="flat", padx=15, pady=8, cursor="hand2")
        admin_btn.pack(side=tk.LEFT, padx=(10, 0))
    
    def create_academic_period_section(self, parent):
        """Create academic period (semester/session/branch) section."""
        card = self.create_card(parent, "🎓 Academic Period")
        
        # Load current values
        current = load_semester_session()
        
        # Row 1: Semester and Session
        sem_frame = ttk.Frame(card, style="Card.TFrame")
        sem_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(sem_frame, text="Semester:", style="Card.TLabel").pack(side=tk.LEFT)
        
        self.semester_var = tk.StringVar(value=str(current['semester']))
        semester_dropdown = ttk.Combobox(
            sem_frame, 
            textvariable=self.semester_var,
            values=["1", "2", "3", "4", "5", "6", "7", "8"],
            state="readonly",
            width=5
        )
        semester_dropdown.pack(side=tk.LEFT, padx=(10, 20))
        
        ttk.Label(sem_frame, text="Session:", style="Card.TLabel").pack(side=tk.LEFT)
        
        self.session_entry = tk.Entry(sem_frame, width=12,
                                      bg=ModernStyle.BG_INPUT,
                                      fg=ModernStyle.TEXT_PRIMARY,
                                      font=('Segoe UI', 10),
                                      relief="flat",
                                      insertbackground=ModernStyle.TEXT_PRIMARY)
        self.session_entry.pack(side=tk.LEFT, padx=(10, 0))
        self.session_entry.insert(0, current['session'])
        
        # Row 2: Branch
        branch_frame = ttk.Frame(card, style="Card.TFrame")
        branch_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(branch_frame, text="Branch:", style="Card.TLabel").pack(side=tk.LEFT)
        
        self.branch_var = tk.StringVar(value=current.get('branch', 'CSE'))
        branch_dropdown = ttk.Combobox(
            branch_frame, 
            textvariable=self.branch_var,
            values=AVAILABLE_BRANCHES,
            state="readonly",
            width=10
        )
        branch_dropdown.pack(side=tk.LEFT, padx=(10, 20))
        
        ttk.Label(branch_frame, text="(CSE, EEE, ME, CE, B.Arch, M.Tech)", style="Muted.TLabel").pack(side=tk.LEFT)
        
        # Current display
        display_frame = ttk.Frame(card, style="Card.TFrame")
        display_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.period_display_label = ttk.Label(
            display_frame, 
            text=f"Current: Semester {current['semester']} • {current['session']} • {current.get('branch', 'CSE')}",
            style="Card.TLabel",
            foreground=ModernStyle.ACCENT
        )
        self.period_display_label.pack(side=tk.LEFT)
        
        # Save button
        btn_frame = ttk.Frame(card, style="Card.TFrame")
        btn_frame.pack(fill=tk.X)
        
        save_btn = tk.Button(btn_frame, text="💾 Save Academic Period",
                            command=self.save_academic_period,
                            bg=ModernStyle.SUCCESS, fg="white",
                            font=('Segoe UI', 10, 'bold'),
                            relief="flat", padx=15, pady=8, cursor="hand2")
        save_btn.pack(side=tk.LEFT)
    
    def create_template_section(self, parent):
        """Create template management section."""
        card = self.create_card(parent, "📋 Templates")
        
        # Template selection row
        select_frame = ttk.Frame(card, style="Card.TFrame")
        select_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(select_frame, text="Template:", style="Card.TLabel").pack(side=tk.LEFT)
        
        self.template_var = tk.StringVar()
        self.template_dropdown = ttk.Combobox(
            select_frame, 
            textvariable=self.template_var,
            values=list(load_templates().keys()),
            state="readonly",
            width=30
        )
        self.template_dropdown.pack(side=tk.LEFT, padx=(10, 0))
        
        # Load/Delete buttons row
        action_frame = ttk.Frame(card, style="Card.TFrame")
        action_frame.pack(fill=tk.X, pady=(0, 15))
        
        load_btn = tk.Button(action_frame, text="🔄 Load Template",
                            command=self.load_template,
                            bg=ModernStyle.ACCENT, fg="white",
                            font=('Segoe UI', 10, 'bold'),
                            relief="flat", padx=15, pady=8, cursor="hand2")
        load_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        delete_btn = tk.Button(action_frame, text="🗑 Delete",
                              command=self.delete_template,
                              bg=ModernStyle.ERROR, fg="white",
                              font=('Segoe UI', 10),
                              relief="flat", padx=12, pady=6, cursor="hand2")
        delete_btn.pack(side=tk.LEFT)
        
        # Separator
        separator = ttk.Frame(card, style="Card.TFrame", height=1)
        separator.pack(fill=tk.X, pady=(5, 15))
        
        # Save template row
        save_label_frame = ttk.Frame(card, style="Card.TFrame")
        save_label_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(save_label_frame, text="Save current configuration as template:", 
                  style="Muted.TLabel").pack(side=tk.LEFT)
        
        save_entry_frame = ttk.Frame(card, style="Card.TFrame")
        save_entry_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(save_entry_frame, text="Name:", style="Card.TLabel").pack(side=tk.LEFT)
        
        self.template_name_entry = tk.Entry(save_entry_frame, width=25,
                                           bg=ModernStyle.BG_INPUT,
                                           fg=ModernStyle.TEXT_PRIMARY,
                                           font=('Segoe UI', 10),
                                           relief="flat",
                                           insertbackground=ModernStyle.TEXT_PRIMARY)
        self.template_name_entry.pack(side=tk.LEFT, padx=(10, 0))
        
        # Save button row
        save_btn_frame = ttk.Frame(card, style="Card.TFrame")
        save_btn_frame.pack(fill=tk.X)
        
        save_template_btn = tk.Button(save_btn_frame, text="💾 Save Current as Template",
                                     command=self.save_current_as_template,
                                     bg=ModernStyle.SUCCESS, fg="white",
                                     font=('Segoe UI', 10, 'bold'),
                                     relief="flat", padx=15, pady=8, cursor="hand2")
        save_template_btn.pack(side=tk.LEFT)
    
    def create_combos_section(self, parent):
        """Create teacher-subject combos management section."""
        card = self.create_card(parent, "👥 Teacher-Subject Combos")
        
        # Combos list
        list_frame = ttk.Frame(card, style="Card.TFrame")
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Listbox with scrollbar
        self.combo_listbox = tk.Listbox(list_frame, height=6,
                                        bg=ModernStyle.BG_INPUT,
                                        fg=ModernStyle.TEXT_PRIMARY,
                                        font=('Segoe UI', 10),
                                        selectbackground=ModernStyle.ACCENT,
                                        selectforeground="white",
                                        relief="flat",
                                        highlightthickness=1,
                                        highlightbackground=ModernStyle.BORDER)
        self.combo_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        combo_scroll = ttk.Scrollbar(list_frame, orient="vertical", 
                                     command=self.combo_listbox.yview)
        combo_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.combo_listbox.config(yscrollcommand=combo_scroll.set)
        
        # Add new combo
        add_frame = ttk.Frame(card, style="Card.TFrame")
        add_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(add_frame, text="Teacher:", style="Muted.TLabel").pack(side=tk.LEFT)
        self.teacher_entry = tk.Entry(add_frame, width=20,
                                      bg=ModernStyle.BG_INPUT,
                                      fg=ModernStyle.TEXT_PRIMARY,
                                      font=('Segoe UI', 10),
                                      relief="flat",
                                      insertbackground=ModernStyle.TEXT_PRIMARY)
        self.teacher_entry.pack(side=tk.LEFT, padx=(5, 15))
        
        ttk.Label(add_frame, text="Subject:", style="Muted.TLabel").pack(side=tk.LEFT)
        self.subject_entry = tk.Entry(add_frame, width=20,
                                      bg=ModernStyle.BG_INPUT,
                                      fg=ModernStyle.TEXT_PRIMARY,
                                      font=('Segoe UI', 10),
                                      relief="flat",
                                      insertbackground=ModernStyle.TEXT_PRIMARY)
        self.subject_entry.pack(side=tk.LEFT, padx=(5, 0))
        
        # Combo buttons
        combo_btn_frame = ttk.Frame(card, style="Card.TFrame")
        combo_btn_frame.pack(fill=tk.X)
        
        add_btn = tk.Button(combo_btn_frame, text="+ Add Combo",
                           command=self.add_combo,
                           bg=ModernStyle.SUCCESS, fg="white",
                           font=('Segoe UI', 10),
                           relief="flat", padx=12, pady=6, cursor="hand2")
        add_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        remove_btn = tk.Button(combo_btn_frame, text="🗑 Remove Selected",
                              command=self.remove_combo,
                              bg=ModernStyle.ERROR, fg="white",
                              font=('Segoe UI', 10),
                              relief="flat", padx=12, pady=6, cursor="hand2")
        remove_btn.pack(side=tk.LEFT)
    
    def create_tokens_section(self, parent):
        """Create token management section."""
        card = self.create_card(parent, "🎫 Token Management")
        
        # Stats row
        stats_frame = ttk.Frame(card, style="Card.TFrame")
        stats_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.tokens_total_label = ttk.Label(stats_frame, text="Total: 0", style="Card.TLabel")
        self.tokens_total_label.pack(side=tk.LEFT)
        
        self.tokens_used_label = ttk.Label(stats_frame, text="Used: 0", 
                                           style="Card.TLabel", foreground=ModernStyle.SUCCESS)
        self.tokens_used_label.pack(side=tk.LEFT, padx=(20, 0))
        
        self.tokens_unused_label = ttk.Label(stats_frame, text="Unused: 0",
                                             style="Card.TLabel", foreground=ModernStyle.WARNING)
        self.tokens_unused_label.pack(side=tk.LEFT, padx=(20, 0))
        
        # Generate row
        gen_frame = ttk.Frame(card, style="Card.TFrame")
        gen_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(gen_frame, text="Generate:", style="Muted.TLabel").pack(side=tk.LEFT)
        
        self.token_count_var = tk.StringVar(value="50")
        token_spinbox = tk.Spinbox(gen_frame, from_=1, to=1000, width=8,
                                   textvariable=self.token_count_var,
                                   bg=ModernStyle.BG_INPUT,
                                   fg=ModernStyle.TEXT_PRIMARY,
                                   font=('Segoe UI', 10),
                                   relief="flat",
                                   buttonbackground=ModernStyle.BG_INPUT)
        token_spinbox.pack(side=tk.LEFT, padx=(10, 15))
        
        ttk.Label(gen_frame, text="tokens", style="Muted.TLabel").pack(side=tk.LEFT)
        
        # Token buttons
        token_btn_frame = ttk.Frame(card, style="Card.TFrame")
        token_btn_frame.pack(fill=tk.X)
        
        gen_btn = tk.Button(token_btn_frame, text="🎲 Generate Tokens",
                           command=self.generate_tokens,
                           bg=ModernStyle.ACCENT, fg="white",
                           font=('Segoe UI', 10, 'bold'),
                           relief="flat", padx=15, pady=8, cursor="hand2")
        gen_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        export_btn = tk.Button(token_btn_frame, text="📄 Export to File",
                              command=self.export_tokens,
                              bg=ModernStyle.BG_INPUT, fg="white",
                              font=('Segoe UI', 10),
                              relief="flat", padx=12, pady=6, cursor="hand2")
        export_btn.pack(side=tk.LEFT)
    
    def create_database_section(self, parent):
        """Create database management section."""
        card = self.create_card(parent, "💾 Database")
        
        # Info row
        info_frame = ttk.Frame(card, style="Card.TFrame")
        info_frame.pack(fill=tk.X, pady=(0, 10))
        
        db_path = os.path.basename(DATABASE_PATH)
        ttk.Label(info_frame, text=f"Database: {db_path}", style="Muted.TLabel").pack(side=tk.LEFT)
        
        # Buttons row
        btn_frame = ttk.Frame(card, style="Card.TFrame")
        btn_frame.pack(fill=tk.X)
        
        refresh_btn = tk.Button(btn_frame, text="🔄 Refresh Stats",
                               command=self.refresh_all,
                               bg=ModernStyle.BG_INPUT, fg="white",
                               font=('Segoe UI', 10),
                               relief="flat", padx=12, pady=6, cursor="hand2")
        refresh_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        reset_btn = tk.Button(btn_frame, text="🗑 Reset Database",
                             command=self.reset_db,
                             bg=ModernStyle.ERROR, fg="white",
                             font=('Segoe UI', 10),
                             relief="flat", padx=12, pady=6, cursor="hand2")
        reset_btn.pack(side=tk.LEFT)
    
    # === Helper Methods ===
    
    def get_local_ip(self):
        """Get local IP address."""
        try:
            hostname = socket.gethostname()
            return socket.gethostbyname(hostname)
        except:
            return "127.0.0.1"
    
    def update_server_status(self):
        """Update server status indicator."""
        if self.server_running and self.server_process:
            if self.server_process.poll() is None:
                self.status_label.config(text="● Running", foreground=ModernStyle.SUCCESS)
                self.start_btn.config(state=tk.DISABLED)
                self.stop_btn.config(state=tk.NORMAL)
            else:
                self.server_running = False
                self.status_label.config(text="● Stopped", foreground=ModernStyle.ERROR)
                self.start_btn.config(state=tk.NORMAL)
                self.stop_btn.config(state=tk.DISABLED)
        else:
            self.status_label.config(text="● Stopped", foreground=ModernStyle.ERROR)
            self.start_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)
    
    def start_server(self):
        """Start the Flask server."""
        if self.server_running:
            return
        
        try:
            # Start server in subprocess
            app_path = os.path.join(PROJECT_ROOT, "app.py")
            self.server_process = subprocess.Popen(
                [sys.executable, app_path],
                cwd=PROJECT_ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
            )
            self.server_running = True
            self.update_server_status()
            
            # Show success message
            messagebox.showinfo("Server Started", 
                              f"Server is now running at:\nhttp://{self.local_ip}:5000")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start server:\n{str(e)}")
    
    def stop_server(self):
        """Stop the Flask server."""
        if not self.server_running or not self.server_process:
            return
        
        try:
            if os.name == 'nt':
                # Windows
                self.server_process.send_signal(signal.CTRL_BREAK_EVENT)
            else:
                # Unix
                self.server_process.terminate()
            
            self.server_process.wait(timeout=5)
            self.server_running = False
            self.server_process = None
            self.update_server_status()
        except Exception as e:
            # Force kill
            try:
                self.server_process.kill()
                self.server_running = False
                self.server_process = None
                self.update_server_status()
            except:
                messagebox.showerror("Error", f"Failed to stop server:\n{str(e)}")
    
    def open_browser(self):
        """Open feedback form in browser."""
        webbrowser.open(f"http://{self.local_ip}:5000")
    
    def open_admin(self):
        """Open admin panel in browser."""
        webbrowser.open(f"http://{self.local_ip}:5000/admin")
    
    def save_academic_period(self):
        """Save semester and session settings."""
        try:
            semester = int(self.semester_var.get())
            if semester < 1 or semester > 8:
                raise ValueError("Invalid semester")
        except ValueError:
            messagebox.showerror("Invalid Input", "Please select a valid semester (1-8).")
            return
        
        session = self.session_entry.get().strip()
        if not session:
            messagebox.showerror("Invalid Input", "Please enter a session (e.g., 2022-26).")
            return
        
        branch = self.branch_var.get()
        if not branch:
            messagebox.showerror("Invalid Input", "Please select a branch.")
            return
        
        # Save to config
        save_semester_session(semester, session, branch)
        
        # Update display
        self.period_display_label.config(
            text=f"Current: Semester {semester} • {session} • {branch}"
        )
        
        messagebox.showinfo("Saved", f"Academic period updated:\nSemester {semester} • {session} • {branch}")
    
    def refresh_templates(self):
        """Refresh template dropdown from config."""
        templates = load_templates()
        self.template_dropdown['values'] = list(templates.keys())
        if templates and not self.template_var.get():
            self.template_dropdown.current(0)
    
    def load_template(self):
        """Load and apply the selected template."""
        template_name = self.template_var.get()
        if not template_name:
            messagebox.showwarning("Select Template", "Please select a template to load.")
            return
        
        if apply_template(template_name):
            # Reload the current values
            current = load_semester_session()
            
            # Update semester dropdown
            self.semester_var.set(str(current['semester']))
            
            # Update session entry
            self.session_entry.delete(0, tk.END)
            self.session_entry.insert(0, current['session'])
            
            # Update branch dropdown
            self.branch_var.set(current.get('branch', 'CSE'))
            
            # Update period display
            self.period_display_label.config(
                text=f"Current: Semester {current['semester']} • {current['session']} • {current.get('branch', 'CSE')}"
            )
            
            # Refresh combos list
            self.refresh_combos()
            
            messagebox.showinfo("Template Loaded", f"Template '{template_name}' has been applied successfully.")
        else:
            messagebox.showerror("Error", f"Failed to load template '{template_name}'.")
    
    def delete_template(self):
        """Delete the selected template."""
        template_name = self.template_var.get()
        if not template_name:
            messagebox.showwarning("Select Template", "Please select a template to delete.")
            return
        
        result = messagebox.askyesno(
            "Confirm Delete",
            f"Are you sure you want to delete the template '{template_name}'?",
            icon='warning'
        )
        
        if result:
            if delete_template(template_name):
                self.template_var.set('')
                self.refresh_templates()
                messagebox.showinfo("Deleted", f"Template '{template_name}' has been deleted.")
            else:
                messagebox.showerror("Error", f"Failed to delete template '{template_name}'.")
    
    def save_current_as_template(self):
        """Save the current configuration as a new template."""
        template_name = self.template_name_entry.get().strip()
        if not template_name:
            messagebox.showwarning("Name Required", "Please enter a name for the template.")
            return
        
        # Check if template already exists
        templates = load_templates()
        if template_name in templates:
            result = messagebox.askyesno(
                "Template Exists",
                f"A template named '{template_name}' already exists. Overwrite?",
                icon='warning'
            )
            if not result:
                return
        
        try:
            semester = int(self.semester_var.get())
        except ValueError:
            messagebox.showerror("Invalid Input", "Please select a valid semester.")
            return
        
        session = self.session_entry.get().strip()
        if not session:
            messagebox.showerror("Invalid Input", "Please enter a session.")
            return
        
        branch = self.branch_var.get()
        if not branch:
            messagebox.showerror("Invalid Input", "Please select a branch.")
            return
        
        combos = load_combos()
        
        # Save the template
        save_template(template_name, semester, session, branch, combos)
        
        # Clear the name entry and refresh dropdown
        self.template_name_entry.delete(0, tk.END)
        self.refresh_templates()
        self.template_var.set(template_name)
        
        messagebox.showinfo("Saved", f"Template '{template_name}' has been saved successfully.")
    
    def refresh_combos(self):
        """Refresh combo list from config."""
        self.combo_listbox.delete(0, tk.END)
        combos = load_combos()
        for i, combo in enumerate(combos, 1):
            self.combo_listbox.insert(tk.END, f"{i}. {combo['teacher']} — {combo['subject']}")
    
    def add_combo(self):
        """Add a new teacher-subject combo."""
        teacher = self.teacher_entry.get().strip()
        subject = self.subject_entry.get().strip()
        
        if not teacher or not subject:
            messagebox.showwarning("Input Required", "Please enter both teacher and subject.")
            return
        
        combos = load_combos()
        combos.append({"teacher": teacher, "subject": subject})
        save_combos(combos)
        
        self.teacher_entry.delete(0, tk.END)
        self.subject_entry.delete(0, tk.END)
        self.refresh_combos()
    
    def remove_combo(self):
        """Remove selected combo."""
        selection = self.combo_listbox.curselection()
        if not selection:
            messagebox.showwarning("Select Item", "Please select a combo to remove.")
            return
        
        idx = selection[0]
        combos = load_combos()
        
        if idx < len(combos):
            removed = combos.pop(idx)
            save_combos(combos)
            self.refresh_combos()
            messagebox.showinfo("Removed", f"Removed: {removed['teacher']} — {removed['subject']}")
    
    def update_token_stats(self):
        """Update token statistics display."""
        stats = get_token_stats()
        self.tokens_total_label.config(text=f"Total: {stats['total']}")
        self.tokens_used_label.config(text=f"Used: {stats['used']}")
        self.tokens_unused_label.config(text=f"Unused: {stats['unused']}")
    
    def generate_tokens(self):
        """Generate new tokens."""
        try:
            count = int(self.token_count_var.get())
            if count < 1 or count > 1000:
                raise ValueError()
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter a number between 1 and 1000.")
            return
        
        # Generate tokens
        tokens = self.generate_unique_tokens(count)
        added = add_tokens(tokens)
        
        self.update_token_stats()
        self.last_generated_tokens = tokens
        
        messagebox.showinfo("Tokens Generated", 
                          f"Generated {len(tokens)} tokens.\n{added} new tokens added to database.")
    
    def generate_unique_tokens(self, count, length=6):
        """Generate unique random tokens."""
        chars = string.ascii_uppercase + string.digits
        chars = chars.replace('0', '').replace('O', '').replace('I', '').replace('1', '').replace('L', '')
        
        tokens = set()
        while len(tokens) < count:
            token = ''.join(random.choices(chars, k=length))
            tokens.add(token)
        return list(tokens)
    
    def export_tokens(self):
        """Export last generated tokens to file."""
        if not hasattr(self, 'last_generated_tokens') or not self.last_generated_tokens:
            messagebox.showwarning("No Tokens", "Please generate tokens first before exporting.")
            return
        
        filepath = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialfile=f"tokens_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )
        
        if filepath:
            with open(filepath, 'w') as f:
                for token in self.last_generated_tokens:
                    f.write(token + '\n')
            messagebox.showinfo("Exported", f"Tokens exported to:\n{filepath}")
    
    def reset_db(self):
        """Reset the database."""
        result = messagebox.askyesno(
            "Confirm Reset",
            "⚠️ This will DELETE all:\n• Tokens\n• Feedback data\n• Sessions\n\nAre you sure?",
            icon='warning'
        )
        
        if result:
            reset_database()
            self.update_token_stats()
            if hasattr(self, 'last_generated_tokens'):
                self.last_generated_tokens = []
            messagebox.showinfo("Reset Complete", "Database has been reset.")
    
    def refresh_all(self):
        """Refresh all data displays."""
        self.refresh_combos()
        self.refresh_templates()
        self.update_token_stats()
        self.update_server_status()
    
    def start_auto_refresh(self):
        """Start periodic auto-refresh of stats."""
        self.auto_refresh()
    
    def auto_refresh(self):
        """Auto-refresh token stats every 5 seconds."""
        try:
            self.update_token_stats()
            self.update_server_status()
        except:
            pass  # Ignore errors during auto-refresh
        
        # Schedule next refresh in 5 seconds
        self.root.after(5000, self.auto_refresh)
    
    def on_close(self):
        """Handle window close event."""
        if self.server_running:
            result = messagebox.askyesno(
                "Server Running",
                "The server is still running. Stop it before closing?",
                icon='warning'
            )
            if result:
                self.stop_server()
        
        self.root.destroy()


def main():
    """Main entry point."""
    root = tk.Tk()
    
    # Set icon (optional)
    try:
        root.iconbitmap(os.path.join(PROJECT_ROOT, "icon.ico"))
    except:
        pass
    
    app = ControlPanel(root)
    root.mainloop()


if __name__ == "__main__":
    main()
