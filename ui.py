import tkinter as tk
from tkinter import messagebox, ttk, filedialog, font
import os
from typing import Dict

from config import NUM_TABLES, SEATS_PER_TABLE, ROUNDS, SAVE_DIR
from tournament_state import TournamentState
from file_operations import autosave, export_to_file, import_from_file, ensure_save_dir, timestamp

# Modern Dark UI Color Scheme
class Colors:
    PRIMARY = "#1E1E2E"      # Very dark blue
    SECONDARY = "#313244"    # Dark gray-blue
    ACCENT = "#89B4FA"       # Bright blue accent
    SUCCESS = "#A6E3A1"      # Bright green
    WARNING = "#F9E2AF"      # Bright yellow
    ERROR = "#F38BA8"        # Bright red/pink
    BACKGROUND = "#181825"   # Very dark background
    SURFACE = "#1E1E2E"      # Dark surface
    TEXT = "#CDD6F4"         # Light text
    TEXT_SECONDARY = "#9399B2"  # Gray text
    HOVER = "#74C7EC"        # Light cyan
    BORDER = "#45475A"       # Dark border


class SwissApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("🌙 Swiss Tournament Manager - Dark Edition")
        self.geometry("1400x950")
        self.configure(bg=Colors.BACKGROUND)
        
        # Set up fonts
        self._setup_fonts()
        
        # Configure ttk styles
        self._setup_styles()

        # Tournament state
        self.tournament = TournamentState()
        
        # UI state
        self.result_vars: Dict[int, tk.StringVar] = {}  # table -> winner strvar

        # UI
        self._build_left_panel()
        self._build_right_panel()
        self._update_players_list()
        self._refresh_standings()
        self._render_empty_pairings()
        self._render_tables_decks([])

        # autosave on close
        self.protocol("WM_DELETE_WINDOW", self._on_close_autosave_then_exit)

    def _setup_fonts(self):
        """Set up custom fonts for the application."""
        self.font_title = font.Font(family="Arial", size=14, weight="bold")
        self.font_heading = font.Font(family="Arial", size=12, weight="bold")
        self.font_body = font.Font(family="Arial", size=10)
        self.font_small = font.Font(family="Arial", size=9)
        self.font_mono = font.Font(family="Courier", size=10)

    def _setup_styles(self):
        """Configure ttk styles for dark theme appearance."""
        style = ttk.Style()
        
        # Configure Treeview for dark theme
        style.configure("Custom.Treeview",
                       background=Colors.SURFACE,
                       foreground=Colors.TEXT,
                       rowheight=25,
                       fieldbackground=Colors.SURFACE,
                       borderwidth=1,
                       relief="solid")
        style.configure("Custom.Treeview.Heading",
                       background=Colors.SECONDARY,
                       foreground=Colors.TEXT,
                       font=self.font_heading,
                       borderwidth=1,
                       relief="solid")
        
        # Configure selection colors
        style.map("Custom.Treeview",
                 background=[('selected', Colors.ACCENT)],
                 foreground=[('selected', Colors.SURFACE)])
        
        # Configure Frame
        style.configure("Card.TFrame",
                       background=Colors.SURFACE,
                       relief="solid",
                       borderwidth=1,
                       bordercolor=Colors.BORDER)
        
        # Configure LabelFrame for dark theme
        style.configure("Card.TLabelframe",
                       background=Colors.SURFACE,
                       foreground=Colors.TEXT,
                       font=self.font_heading,
                       borderwidth=1,
                       relief="solid")
        style.configure("Card.TLabelframe.Label",
                       background=Colors.SURFACE,
                       foreground=Colors.TEXT,
                       font=self.font_heading)

    def _create_styled_button(self, parent, text, command, style_type="primary", **kwargs):
        """Create a styled button with dark theme appearance."""
        if style_type == "primary":
            bg_color = Colors.ACCENT
            fg_color = Colors.PRIMARY
            active_bg = Colors.HOVER
        elif style_type == "success":
            bg_color = Colors.SUCCESS
            fg_color = Colors.PRIMARY
            active_bg = "#94D890"
        elif style_type == "warning":
            bg_color = Colors.WARNING
            fg_color = Colors.PRIMARY
            active_bg = "#F5D76E"
        elif style_type == "error":
            bg_color = Colors.ERROR
            fg_color = Colors.PRIMARY
            active_bg = "#F07A9A"
        else:  # secondary
            bg_color = Colors.SECONDARY
            fg_color = Colors.TEXT
            active_bg = Colors.BORDER
        
        btn = tk.Button(
            parent,
            text=text,
            command=command,
            bg=bg_color,
            fg=fg_color,
            activebackground=active_bg,
            activeforeground=fg_color,
            font=self.font_body,
            relief="flat",
            bd=0,
            padx=20,
            pady=8,
            cursor="hand2",
            **kwargs
        )
        
        # Add hover effects
        def on_enter(e):
            btn.configure(bg=active_bg)
        
        def on_leave(e):
            btn.configure(bg=bg_color)
        
        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)
        
        return btn

    def _update_status(self, message, status_type="info"):
        """Update status with colored message based on type."""
        self.status_var.set(message)
        
        if status_type == "success":
            color = Colors.SUCCESS
        elif status_type == "warning":
            color = Colors.WARNING
        elif status_type == "error":
            color = Colors.ERROR
        else:  # info
            color = Colors.TEXT
        
        self.status_label.configure(fg=color)

    # --------- UI LAYOUT ---------
    def _build_left_panel(self):
        left = tk.Frame(self, bg=Colors.BACKGROUND, padx=15, pady=15)
        left.pack(side=tk.LEFT, fill=tk.Y)

        # Title
        title_label = tk.Label(left, text="🎯 Tournament Control", 
                              font=self.font_title, bg=Colors.BACKGROUND, fg=Colors.TEXT)
        title_label.pack(anchor="w", pady=(0, 15))

        # Player management card
        players_frame = tk.LabelFrame(left, text="👥 Players", 
                                     bg=Colors.SURFACE, fg=Colors.TEXT, 
                                     font=self.font_heading, relief="solid", bd=1,
                                     highlightbackground=Colors.BORDER)
        players_frame.pack(fill="x", pady=(0, 15))

        players_inner = tk.Frame(players_frame, bg=Colors.SURFACE, padx=15, pady=10)
        players_inner.pack(fill="both", expand=True)

        self.players_list = tk.Listbox(players_inner, height=14, width=28, 
                                      exportselection=False, font=self.font_body,
                                      bg=Colors.SECONDARY, fg=Colors.TEXT,
                                      selectbackground=Colors.ACCENT,
                                      selectforeground=Colors.SURFACE,
                                      relief="solid", bd=1,
                                      highlightthickness=0,
                                      borderwidth=1)
        self.players_list.pack(anchor="w", pady=(0, 8))

        # Player count label
        self.player_count_var = tk.StringVar(value="Players: 0 / 24")
        count_label = tk.Label(players_inner, textvariable=self.player_count_var, 
                              font=self.font_small, bg=Colors.SURFACE, fg=Colors.TEXT_SECONDARY)
        count_label.pack(anchor="w", pady=(0, 10))

        # Add player form
        form = tk.Frame(players_inner, bg=Colors.SURFACE)
        form.pack(anchor="w", fill="x", pady=(0, 8))
        
        tk.Label(form, text="Add player:", font=self.font_body, 
                bg=Colors.SURFACE, fg=Colors.TEXT).grid(row=0, column=0, sticky="w")
        
        self.player_name_var = tk.StringVar()
        entry = tk.Entry(form, textvariable=self.player_name_var, width=18, 
                        font=self.font_body, relief="solid", bd=1,
                        bg=Colors.SECONDARY, fg=Colors.TEXT,
                        insertbackground=Colors.TEXT, highlightthickness=0)
        entry.grid(row=0, column=1, padx=(8, 5))
        
        add_btn = self._create_styled_button(form, "Add", self.add_player, "success")
        add_btn.grid(row=0, column=2)

        # Remove button
        remove_btn = self._create_styled_button(players_inner, "Remove Selected", 
                                               self.remove_selected, "error")
        remove_btn.pack(anchor="w", pady=(0, 5))

        # Status card
        status_frame = tk.LabelFrame(left, text="📊 Status", 
                                    bg=Colors.SURFACE, fg=Colors.TEXT, 
                                    font=self.font_heading, relief="solid", bd=1,
                                    highlightbackground=Colors.BORDER)
        status_frame.pack(fill="x", pady=(0, 15))

        status_inner = tk.Frame(status_frame, bg=Colors.SURFACE, padx=15, pady=10)
        status_inner.pack(fill="both", expand=True)

        self.status_var = tk.StringVar(value="Add players, then Start Tournament.")
        self.status_label = tk.Label(status_inner, textvariable=self.status_var, 
                                    font=self.font_body, bg=Colors.SURFACE, fg=Colors.TEXT,
                                    wraplength=280, justify="left")
        self.status_label.pack(anchor="w", pady=(0, 10))

        # Seed input
        seed_label = tk.Label(status_inner, text="🎲 Random seed (optional):", 
                             font=self.font_body, bg=Colors.SURFACE, fg=Colors.TEXT)
        seed_label.pack(anchor="w")
        
        self.seed_var = tk.StringVar(value="")
        seed_entry = tk.Entry(status_inner, textvariable=self.seed_var, width=20, 
                             font=self.font_body, relief="solid", bd=1,
                             bg=Colors.SECONDARY, fg=Colors.TEXT,
                             insertbackground=Colors.TEXT, highlightthickness=0)
        seed_entry.pack(anchor="w", pady=(5, 0))

        # Control buttons card
        control_frame = tk.LabelFrame(left, text="🎮 Tournament Controls", 
                                     bg=Colors.SURFACE, fg=Colors.TEXT, 
                                     font=self.font_heading, relief="solid", bd=1,
                                     highlightbackground=Colors.BORDER)
        control_frame.pack(fill="x", pady=(0, 15))

        control_inner = tk.Frame(control_frame, bg=Colors.SURFACE, padx=15, pady=10)
        control_inner.pack(fill="both", expand=True)

        # Control buttons
        self.start_btn = self._create_styled_button(control_inner, "🚀 Start Tournament", 
                                                   self.start_tournament, "success")
        self.pair_btn = self._create_styled_button(control_inner, "🔄 Pair Next Round", 
                                                  self.pair_next_round, "primary", state=tk.DISABLED)
        self.submit_btn = self._create_styled_button(control_inner, "✅ Submit Results", 
                                                    self.submit_results, "success", state=tk.DISABLED)
        self.undo_btn = self._create_styled_button(control_inner, "↶ Undo Last Round", 
                                                  self.undo_last_round, "warning", state=tk.DISABLED)

        # File operations card
        file_frame = tk.LabelFrame(left, text="💾 File Operations", 
                                  bg=Colors.SURFACE, fg=Colors.TEXT, 
                                  font=self.font_heading, relief="solid", bd=1,
                                  highlightbackground=Colors.BORDER)
        file_frame.pack(fill="x", pady=(0, 15))

        file_inner = tk.Frame(file_frame, bg=Colors.SURFACE, padx=15, pady=10)
        file_inner.pack(fill="both", expand=True)

        self.export_btn = self._create_styled_button(file_inner, "📤 Export Now", 
                                                    self.export_now, "secondary")
        self.import_btn = self._create_styled_button(file_inner, "📥 Import State", 
                                                    self.import_state, "secondary")
        self.reset_btn = self._create_styled_button(file_inner, "🔄 Reset", 
                                                   self.reset_tournament, "error")

        # Pack all buttons
        for btn in [self.start_btn, self.pair_btn, self.submit_btn, self.undo_btn]:
            btn.pack(fill=tk.X, pady=3)
        
        for btn in [self.export_btn, self.import_btn, self.reset_btn]:
            btn.pack(fill=tk.X, pady=3)

    def _build_right_panel(self):
        right = tk.Frame(self, bg=Colors.BACKGROUND, padx=15, pady=15)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Round header
        head = tk.Frame(right, bg=Colors.BACKGROUND)
        head.pack(fill=tk.X, pady=(0, 15))
        self.round_label = tk.Label(head, text="🏁 Round: —", 
                                   font=self.font_title, bg=Colors.BACKGROUND, fg=Colors.TEXT)
        self.round_label.pack(side=tk.LEFT)

        # Tables & Decks/Maps (always visible)
        self.decks_frame = tk.LabelFrame(right, text="🃏 Tables, Decks & Maps (Fixed Setup)",
                                        bg=Colors.SURFACE, fg=Colors.TEXT, 
                                        font=self.font_heading, relief="solid", bd=1,
                                        highlightbackground=Colors.BORDER)
        self.decks_frame.pack(fill=tk.X, pady=(0, 15))
        
        decks_inner = tk.Frame(self.decks_frame, bg=Colors.SURFACE, padx=10, pady=10)
        decks_inner.pack(fill="both", expand=True)
        
        self.decks_tree = ttk.Treeview(
            decks_inner,
            columns=("Table", "Map", "Deck 1", "Deck 2", "Deck 3", "Deck 4"),
            show="headings",
            height=7,
            style="Custom.Treeview"
        )
        
        # Configure columns with better spacing
        columns = [("Table", 60), ("Map", 180), ("Deck 1", 160), ("Deck 2", 160), ("Deck 3", 160), ("Deck 4", 160)]
        for col, w in columns:
            self.decks_tree.heading(col, text=col)
            self.decks_tree.column(col, width=w, anchor="w")
        
        self.decks_tree.pack(fill=tk.X, expand=False)

        # Pairings area
        self.pairings_frame = tk.LabelFrame(right, text="⚔️ Current Round Pairings",
                                           bg=Colors.SURFACE, fg=Colors.TEXT, 
                                           font=self.font_heading, relief="solid", bd=1,
                                           highlightbackground=Colors.BORDER)
        self.pairings_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

        # Standings
        self.standings_frame = tk.LabelFrame(right, text="🏆 Tournament Standings",
                                            bg=Colors.SURFACE, fg=Colors.TEXT, 
                                            font=self.font_heading, relief="solid", bd=1,
                                            highlightbackground=Colors.BORDER)
        self.standings_frame.pack(fill=tk.BOTH)
        
        standings_inner = tk.Frame(self.standings_frame, bg=Colors.SURFACE, padx=10, pady=10)
        standings_inner.pack(fill="both", expand=True)
        
        self.tree = ttk.Treeview(
            standings_inner,
            columns=("Place", "Player", "Score", "Buchholz (W-L)"),
            show="headings",
            height=12,
            style="Custom.Treeview"
        )
        
        # Configure standings columns
        standings_columns = [("Place", 60), ("Player", 220), ("Score", 70), ("Buchholz (W-L)", 120)]
        for col, w in standings_columns:
            self.tree.heading(col, text=col)
            if col == "Place" or col == "Score" or col == "Buchholz (W-L)":
                self.tree.column(col, width=w, anchor="center")
            else:
                self.tree.column(col, width=w, anchor="w")
        
        self.tree.pack(fill=tk.BOTH, expand=True)

    # --------- Player management ---------
    def _update_player_count_label(self):
        self.player_count_var.set(f"Players: {len(self.tournament.players)} / {NUM_TABLES * SEATS_PER_TABLE}")

    def add_player(self):
        name = self.player_name_var.get().strip()
        if not name:
            return
        
        if not self.tournament.add_player(name):
            if name in self.tournament.players:
                messagebox.showerror("Error", "Player already exists.")
            else:
                messagebox.showerror("Error", f"Max {NUM_TABLES * SEATS_PER_TABLE} players.")
            return
        
        self.player_name_var.set("")
        self._update_players_list()

    def remove_selected(self):
        if self.tournament.round_no > 0:
            messagebox.showerror("Error", "Cannot remove players after start.")
            return
        sel = list(self.players_list.curselection())
        sel.reverse()
        for idx in sel:
            player_name = self.tournament.players[idx]
            self.tournament.remove_player(player_name)
        self._update_players_list()

    def _update_players_list(self):
        self.players_list.delete(0, tk.END)
        for p in self.tournament.players:
            self.players_list.insert(tk.END, p)
        self._update_player_count_label()

    # --------- Tournament flow ---------
    def start_tournament(self):
        can_start, error = self.tournament.can_start_tournament()
        if not can_start:
            messagebox.showerror("Error", error)
            return

        seed = self.seed_var.get().strip()
        self.tournament.set_seed(seed)

        try:
            self.tournament.start_tournament()
        except Exception as e:
            messagebox.showerror("Setup failed", str(e))
            return
        
        self._render_tables_decks(sorted(self.tournament.tables_to_decks.items(), key=lambda x: x[0]))

        # Lock player edits
        self.start_btn.config(state=tk.DISABLED)
        self.pair_btn.config(state=tk.NORMAL)
        self.submit_btn.config(state=tk.DISABLED)

        self._update_status("🎯 Tournament started. Click 'Pair Next Round'.", "success")
        self._refresh_standings()
        self._render_empty_pairings()
        self.round_label.config(text=f"Round: {self.tournament.round_no}/{ROUNDS}")

        # Autosave initial state (round 0)
        try:
            autosave(self.tournament, reason="start")
        except Exception as e:
            messagebox.showwarning("Autosave failed", str(e))

    def pair_next_round(self):
        can_pair, error = self.tournament.can_pair_next_round()
        if not can_pair:
            messagebox.showinfo("Info", error)
            return

        try:
            forced, success = self.tournament.pair_next_round()
        except Exception as e:
            messagebox.showerror("Pairing failed", str(e))
            return

        self.round_label.config(text=f"Round: {self.tournament.round_no}/{ROUNDS}")

        if forced:
            txt = "\n".join(f"{p} @ Table {t}" for p, t in forced)
            messagebox.showwarning("Table repeats unavoidable", f"Some players revisited a table:\n{txt}")

        self._render_pairings()
        self.submit_btn.config(state=tk.NORMAL)
        self.pair_btn.config(state=tk.DISABLED)
        self.undo_btn.config(state=tk.NORMAL)
        self._update_status("⚔️ Select winners and click 'Submit Results'.", "warning")

    def submit_results(self):
        winners = {}
        for t, (a, b) in self.tournament.current_table_pairs.items():
            sel = self.result_vars[t].get()
            if sel not in (a, b):
                messagebox.showerror("Missing winner", f"Select winner for Table {t}.")
                return
            winners[t] = sel

        # Snapshot BEFORE changes (for Undo)
        self.tournament.snapshot_before_submit()

        try:
            self.tournament.submit_results(winners)
        except Exception as e:
            messagebox.showerror("Submit failed", str(e))
            return

        self._render_empty_pairings()
        self._refresh_standings()

        if self.tournament.round_no < ROUNDS:
            self.pair_btn.config(state=tk.NORMAL)
            self.submit_btn.config(state=tk.DISABLED)
            self._update_status("✅ Round saved. Click 'Pair Next Round' for the next round.", "success")
        else:
            self.pair_btn.config(state=tk.DISABLED)
            self.submit_btn.config(state=tk.DISABLED)
            self._update_status("🏆 Tournament finished! Check final standings.", "success")

        # Autosave BETWEEN rounds
        try:
            autosave(self.tournament, reason="between_rounds")
        except Exception as e:
            messagebox.showwarning("Autosave failed", str(e))

    def undo_last_round(self):
        """Revert to the state BEFORE the last submitted round."""
        if not self.tournament.can_undo():
            messagebox.showinfo("Info", "Nothing to undo.")
            return

        try:
            self.tournament.undo_last_round()
        except Exception as e:
            messagebox.showerror("Undo failed", str(e))
            return

        self._render_tables_decks(sorted(self.tournament.tables_to_decks.items(), key=lambda x: x[0]))
        self.round_label.config(text=f"Round: {self.tournament.round_no}/{ROUNDS}")
        self._render_pairings()
        self._refresh_standings()
        self._update_players_list()

        self.submit_btn.config(state=tk.NORMAL)
        self.pair_btn.config(state=tk.DISABLED)
        self.start_btn.config(state=tk.DISABLED)
        self._update_status("↶ Undone last round. Re-select winners and Submit Results.", "warning")

        if not self.tournament.can_undo():
            self.undo_btn.config(state=tk.DISABLED)

    def reset_tournament(self):
        if messagebox.askyesno("Reset", "Reset the tournament to an empty state?"):
            self.tournament.reset()
            self.start_btn.config(state=tk.NORMAL)
            self.pair_btn.config(state=tk.DISABLED)
            self.submit_btn.config(state=tk.DISABLED)
            self.undo_btn.config(state=tk.DISABLED)
            self._update_status("➕ Add players, then Start Tournament.", "info")
            self._update_players_list()
            self._refresh_standings()
            self._render_empty_pairings()
            self._render_tables_decks([])
            self.round_label.config(text="Round: —")

    # --------- Save / Load ---------
    def export_now(self):
        """Manual save via file dialog."""
        ensure_save_dir()
        default_name = f"manual_r{self.tournament.round_no:02d}_{timestamp()}.json"
        path = filedialog.asksaveasfilename(
            initialdir=SAVE_DIR,
            defaultextension=".json",
            initialfile=default_name,
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if not path:
            return
        try:
            export_to_file(self.tournament, path)
            messagebox.showinfo("Saved", f"Saved to:\n{path}")
        except Exception as e:
            messagebox.showerror("Save failed", str(e))

    def import_state(self):
        """Load state from a JSON file and resume."""
        path = filedialog.askopenfilename(
            initialdir=SAVE_DIR if os.path.isdir(SAVE_DIR) else ".",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if not path:
            return

        try:
            import_from_file(path, self.tournament)
        except Exception as e:
            messagebox.showerror("Load failed", str(e))
            return

        self.start_btn.config(state=tk.DISABLED)
        self.undo_btn.config(state=tk.NORMAL if self.tournament.can_undo() else tk.DISABLED)

        if self.tournament.current_table_pairs:
            self.submit_btn.config(state=tk.NORMAL)
            self.pair_btn.config(state=tk.DISABLED)
            self.status_var.set("State loaded. Re-select winners and Submit Results.")
        else:
            self.submit_btn.config(state=tk.DISABLED)
            self.pair_btn.config(state=tk.NORMAL)
            self.status_var.set("State loaded. Click 'Pair Next Round'.")

        self._update_players_list()
        self._refresh_standings()
        self._render_tables_decks(sorted(self.tournament.tables_to_decks.items(), key=lambda x: x[0]))
        if self.tournament.current_table_pairs:
            self._render_pairings()
        else:
            self._render_empty_pairings()
        self.round_label.config(text=f"Round: {self.tournament.round_no}/{ROUNDS}")

        messagebox.showinfo("Loaded", f"Loaded:\n{os.path.basename(path)}")

    def _on_close_autosave_then_exit(self):
        """Autosave on exit and close the app."""
        try:
            autosave(self.tournament, reason="on_exit")
        except:
            pass  # Don't prevent closing on autosave failure
        finally:
            self.destroy()

    # --------- Rendering helpers ---------
    def _render_tables_decks(self, rows):
        # rows: list of (table_id, [d1,d2,d3,d4])
        for i in self.decks_tree.get_children():
            self.decks_tree.delete(i)
        for t, decks in rows:
            d = (decks + ["", "", "", ""])[:4]
            m = self.tournament.tables_to_maps.get(t, "")
            self.decks_tree.insert("", tk.END, values=(t, m, d[0], d[1], d[2], d[3]))

    def _render_empty_pairings(self):
        for w in self.pairings_frame.winfo_children():
            w.destroy()
        
        # Create inner frame with styling
        inner = tk.Frame(self.pairings_frame, bg=Colors.SURFACE, padx=20, pady=20)
        inner.pack(fill="both", expand=True)
        
        # Empty state message
        empty_label = tk.Label(inner, text="⏳ No active round pairings", 
                              font=self.font_body, bg=Colors.SURFACE, fg=Colors.TEXT_SECONDARY,
                              justify="center")
        empty_label.pack(expand=True)
        
        info_label = tk.Label(inner, text="Click 'Pair Next Round' to generate matchups", 
                             font=self.font_small, bg=Colors.SURFACE, fg=Colors.TEXT_SECONDARY,
                             justify="center")
        info_label.pack(pady=(5, 0))

    def _render_pairings(self):
        for w in self.pairings_frame.winfo_children():
            w.destroy()
        self.result_vars.clear()

        # Create main container
        main_frame = tk.Frame(self.pairings_frame, bg=Colors.SURFACE)
        main_frame.pack(fill="both", expand=True, padx=15, pady=15)

        # Instructions
        instruction_label = tk.Label(main_frame, text="Select the winner for each match", 
                                    font=self.font_body, bg=Colors.SURFACE, fg=Colors.TEXT_SECONDARY)
        instruction_label.pack(pady=(0, 15))

        rows = sorted(self.tournament.current_table_pairs.items(), key=lambda x: x[0])

        # Create header
        header_frame = tk.Frame(main_frame, bg=Colors.SECONDARY, relief="solid", bd=1)
        header_frame.pack(fill="x", pady=(0, 5))
        
        # Configure header grid
        header_frame.grid_columnconfigure(0, weight=0, minsize=80)
        header_frame.grid_columnconfigure(1, weight=1, minsize=350)
        header_frame.grid_columnconfigure(2, weight=0, minsize=200)
        
        tk.Label(header_frame, text="Table", bg=Colors.SECONDARY, fg=Colors.TEXT,
                font=self.font_heading, pady=8).grid(row=0, column=0, sticky="ew")
        tk.Label(header_frame, text="Matchup & Map", bg=Colors.SECONDARY, fg=Colors.TEXT,
                font=self.font_heading, pady=8).grid(row=0, column=1, sticky="ew")
        tk.Label(header_frame, text="Select Winner", bg=Colors.SECONDARY, fg=Colors.TEXT,
                font=self.font_heading, pady=8).grid(row=0, column=2, sticky="ew")

        # Create scrollable content area
        canvas = tk.Canvas(main_frame, bg=Colors.SURFACE, highlightthickness=0)
        scrollbar = tk.Scrollbar(main_frame, orient="vertical", command=canvas.yview,
                               bg=Colors.SECONDARY, troughcolor=Colors.SURFACE)
        scrollable_frame = tk.Frame(canvas, bg=Colors.SURFACE)

        # Mouse wheel scrolling
        def _on_mousewheel(event):
            try:
                if hasattr(event, 'delta') and event.delta:
                    canvas.yview_scroll(int(-1*(event.delta/120)), "units")
                elif hasattr(event, 'num'):
                    if event.num == 4:
                        canvas.yview_scroll(-1, "units")
                    elif event.num == 5:
                        canvas.yview_scroll(1, "units")
            except:
                pass

        def _bind_mousewheel(event):
            canvas.bind_all("<MouseWheel>", _on_mousewheel)
            canvas.bind_all("<Button-4>", _on_mousewheel)
            canvas.bind_all("<Button-5>", _on_mousewheel)

        def _unbind_mousewheel(event):
            canvas.unbind_all("<MouseWheel>")
            canvas.unbind_all("<Button-4>")
            canvas.unbind_all("<Button-5>")

        scrollable_frame.bind("<Configure>", 
                             lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Enter>", _bind_mousewheel)
        canvas.bind("<Leave>", _unbind_mousewheel)

        # Create canvas window and configure width
        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        def _configure_canvas_width(event):
            canvas.itemconfig(canvas_window, width=canvas.winfo_width())
        canvas.bind('<Configure>', _configure_canvas_width)

        # Create match rows with actual grid layout
        for i, (t, (a, b)) in enumerate(rows):
            row_bg = Colors.SURFACE if i % 2 == 0 else Colors.SECONDARY
            
            # Create row frame
            row_frame = tk.Frame(scrollable_frame, bg=row_bg, relief="solid", bd=1)
            row_frame.pack(fill="x", pady=1)
            
            # Configure the same grid as header
            row_frame.grid_columnconfigure(0, weight=0, minsize=80)
            row_frame.grid_columnconfigure(1, weight=1, minsize=350)
            row_frame.grid_columnconfigure(2, weight=0, minsize=200)
            
            # Table number
            table_label = tk.Label(row_frame, text=f"#{t}", bg=Colors.ACCENT, fg=Colors.PRIMARY,
                                  font=self.font_heading, pady=15)
            table_label.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
            
            # Match info
            map_name = self.tournament.tables_to_maps.get(t, "")
            match_info = tk.Frame(row_frame, bg=row_bg)
            match_info.grid(row=0, column=1, sticky="ew", padx=10, pady=10)
            
            players_label = tk.Label(match_info, text=f"{a}  🆚  {b}", 
                                   bg=row_bg, fg=Colors.TEXT, font=self.font_heading,
                                   anchor="w")
            players_label.pack(anchor="w")
            
            map_label = tk.Label(match_info, text=f"📍 Map: {map_name}", 
                               bg=row_bg, fg=Colors.TEXT_SECONDARY, font=self.font_body,
                               anchor="w")
            map_label.pack(anchor="w", pady=(2, 0))
            
            # Winner selection
            var = tk.StringVar(value="")
            self.result_vars[t] = var
            
            winner_frame = tk.Frame(row_frame, bg=row_bg)
            winner_frame.grid(row=0, column=2, sticky="ew", padx=10, pady=10)
            
            rb1 = tk.Radiobutton(winner_frame, text=f"🏆 {a}", variable=var, value=a,
                               bg=row_bg, fg=Colors.TEXT, font=self.font_body,
                               selectcolor=Colors.SUCCESS, activebackground=row_bg,
                               relief="flat", highlightthickness=0)
            rb1.pack(anchor="w", pady=2)
            
            rb2 = tk.Radiobutton(winner_frame, text=f"🏆 {b}", variable=var, value=b,
                               bg=row_bg, fg=Colors.TEXT, font=self.font_body,
                               selectcolor=Colors.SUCCESS, activebackground=row_bg,
                               relief="flat", highlightthickness=0)
            rb2.pack(anchor="w", pady=2)

        # Pack scrollbar and canvas
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

    def _refresh_standings(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        placed_rows = self.tournament.get_standings_with_places()
        for place, name, sc, buch in placed_rows:
            self.tree.insert("", tk.END, values=(place, name, sc, buch)) 