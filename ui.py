import tkinter as tk
from tkinter import messagebox, ttk, filedialog, font
import os
from typing import Dict

from config import NUM_TABLES, SEATS_PER_TABLE, ROUNDS, SAVE_DIR
from tournament_state import TournamentState
from file_operations import autosave, export_to_file, import_from_file, ensure_save_dir, timestamp

THEMES = {
    "Dark": {"PRIMARY": "#1E1E2E", "SECONDARY": "#313244", "ACCENT": "#89B4FA", "SUCCESS": "#A6E3A1", "WARNING": "#F9E2AF", "ERROR": "#F38BA8", "BACKGROUND": "#181825", "SURFACE": "#1E1E2E", "TEXT": "#CDD6F4", "TEXT_SECONDARY": "#9399B2", "HOVER": "#74C7EC", "BORDER": "#45475A"},
    "Light": {"PRIMARY": "#FFFFFF", "SECONDARY": "#E9ECEF", "ACCENT": "#007BFF", "SUCCESS": "#28A745", "WARNING": "#FFC107", "ERROR": "#DC3545", "BACKGROUND": "#F8F9FA", "SURFACE": "#FFFFFF", "TEXT": "#212529", "TEXT_SECONDARY": "#6C757D", "HOVER": "#0056b3", "BORDER": "#DEE2E6"},
    "Brown": {"PRIMARY": "#282828", "SECONDARY": "#504945", "ACCENT": "#83A598", "SUCCESS": "#B8BB26", "WARNING": "#FABD2F", "ERROR": "#FB4934", "BACKGROUND": "#282828", "SURFACE": "#3C3836", "TEXT": "#EBDBB2", "TEXT_SECONDARY": "#A89984", "HOVER": "#8EC07C", "BORDER": "#665C54"},
    "Sand": {"PRIMARY": "#FFFFFF", "SECONDARY": "#EAE6DA", "ACCENT": "#0062A3", "SUCCESS": "#2E8B57", "WARNING": "#D95B00", "ERROR": "#B81D1D", "BACKGROUND": "#F5F1E6", "SURFACE": "#FFFFFF", "TEXT": "#0A3D62", "TEXT_SECONDARY": "#5A7A97", "HOVER": "#0078C1", "BORDER": "#D1CABC"},
    "Marine": {"PRIMARY": "#FFFFFF", "SECONDARY": "#1A425F", "ACCENT": "#20C997", "SUCCESS": "#28A745", "WARNING": "#FFC107", "ERROR": "#E55353", "BACKGROUND": "#0B1B2A", "SURFACE": "#112D42", "TEXT": "#B0D4D9", "TEXT_SECONDARY": "#6A8B92", "HOVER": "#25E0A7", "BORDER": "#2A5A7A"}
}

class SwissApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Swiss Tournament Manager")
        self.geometry("1400x1000")
        
        self.tournament = TournamentState()
        self.theme_name = "Dark"
        self.theme_colors = THEMES[self.theme_name]
        self.theme_var = tk.StringVar(value=self.theme_name)
        self.decks_window, self.standings_window, self.standings_tree_toplevel, self.standings_tree_embedded = None, None, None, None
        self.result_vars: Dict[int, tk.StringVar] = {}

        self._setup_fonts()
        self.rebuild_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close_autosave_then_exit)

    def change_theme(self):
        new_theme = self.theme_var.get()
        if new_theme == self.theme_name: return
        self.theme_name, self.theme_colors = new_theme, THEMES[new_theme]
        self.rebuild_ui()

    def rebuild_ui(self):
        for widget in self.winfo_children(): widget.destroy()
        
        self.configure(bg=self.theme_colors['BACKGROUND'])
        self._build_menu()
        self._setup_styles()
        
        self._build_left_panel()
        self._build_right_panel()
        
        self._update_players_list()
        self._update_status(self.status_label.cget("text") if hasattr(self, "status_label") else "Add players, then Start Tournament.")
        self.round_label.config(text=f"Round: {self.tournament.round_no if self.tournament.round_no > 0 else '—'}/{ROUNDS}")

        self._restore_ui_state()

    def _restore_ui_state(self):
        """Відновлює стан інтерфейсу після перебудови."""
        if self.tournament.current_table_pairs:
            self._show_decks_as_button()
            self._show_standings_as_button()
            self._render_pairings()
        elif self.tournament.round_no > 0:
            self._show_decks_as_button()
            self._show_standings_as_embedded()
            self._render_empty_pairings()
        elif self.tournament.players and self.tournament.scores: # Started but no rounds
            self._show_decks_as_embedded()
            self._show_standings_as_button()
            self._render_empty_pairings()
        else: # Initial state
            self._show_decks_as_button()
            self._show_standings_as_button()
            self._render_empty_pairings()
        
        self._update_button_states()
        self._refresh_standings()

    def _update_button_states(self):
        """Оновлює стан (активний/неактивний) кнопок керування."""
        is_started = self.tournament.round_no > 0 or self.tournament.scores
        is_round_active = bool(self.tournament.current_table_pairs)

        self.start_btn.config(state=tk.DISABLED if is_started else tk.NORMAL)
        self.pair_btn.config(state=tk.NORMAL if is_started and not is_round_active and self.tournament.round_no < ROUNDS else tk.DISABLED)
        self.submit_btn.config(state=tk.NORMAL if is_round_active else tk.DISABLED)
        self.undo_btn.config(state=tk.NORMAL if self.tournament.can_undo() else tk.DISABLED)

    def _setup_fonts(self):
        self.font_title = font.Font(family="Arial", size=14, weight="bold"); self.font_heading = font.Font(family="Arial", size=12, weight="bold"); self.font_body = font.Font(family="Arial", size=10); self.font_small = font.Font(family="Arial", size=9)

    def _setup_styles(self):
        style = ttk.Style(); style.theme_use('clam'); colors = self.theme_colors
        style.configure("Custom.Treeview", background=colors['SURFACE'], foreground=colors['TEXT'], rowheight=25, fieldbackground=colors['SURFACE'], borderwidth=0, relief="flat")
        style.map("Custom.Treeview", background=[('selected', colors['ACCENT'])], foreground=[('selected', colors['PRIMARY'])])
        style.configure("Custom.Treeview.Heading", background=colors['SECONDARY'], foreground=colors['TEXT'], font=self.font_heading, borderwidth=1, relief="solid")
        style.configure("TLabelframe", background=colors['SURFACE'], bordercolor=colors['BORDER']); style.configure("TLabelframe.Label", background=colors['SURFACE'], foreground=colors['TEXT'], font=self.font_heading)
        style.configure("TFrame", background=colors['SURFACE']); style.configure("TRadiobutton", background=colors['SURFACE'], foreground=colors['TEXT']); style.map("TRadiobutton", background=[('active', colors['SECONDARY'])])

    def _build_menu(self):
        menubar = tk.Menu(self); self.config(menu=menubar); theme_menu = tk.Menu(menubar, tearoff=0); menubar.add_cascade(label="Theme", menu=theme_menu)
        for theme_name in THEMES: theme_menu.add_radiobutton(label=theme_name, variable=self.theme_var, value=theme_name, command=self.change_theme)

    def _create_styled_button(self, parent, text, command, style_type="primary", **kwargs):
        colors = self.theme_colors; theme_map = {"primary": (colors['ACCENT'], colors['PRIMARY'], colors['HOVER']), "success": (colors['SUCCESS'], colors['PRIMARY'], colors['HOVER']), "warning": (colors['WARNING'], colors['PRIMARY'], colors['HOVER']), "error": (colors['ERROR'], colors['PRIMARY'], colors['HOVER']), "secondary": (colors['SECONDARY'], colors['TEXT'], colors['BORDER'])}
        bg, fg, active_bg = theme_map.get(style_type, theme_map["secondary"])
        btn = tk.Button(parent, text=text, command=command, bg=bg, fg=fg, activebackground=active_bg, activeforeground=fg, font=self.font_body, relief="flat", bd=0, padx=10, pady=5, cursor="hand2", **kwargs)
        btn.bind("<Enter>", lambda e, c=active_bg: e.widget.config(bg=c)); btn.bind("<Leave>", lambda e, c=bg: e.widget.config(bg=c)); return btn

    def _build_left_panel(self):
        left = tk.Frame(self, bg=self.theme_colors['BACKGROUND'], padx=15, pady=15); left.pack(side=tk.LEFT, fill=tk.Y, anchor='n')
        tk.Label(left, text="Tournament Control", font=self.font_title, bg=self.theme_colors['BACKGROUND'], fg=self.theme_colors['TEXT']).pack(anchor="w", pady=(0, 15))
        players_frame = ttk.LabelFrame(left, text="Players"); players_frame.pack(fill="x", pady=(0, 15))
        players_inner = tk.Frame(players_frame, bg=self.theme_colors['SURFACE'], padx=15, pady=10); players_inner.pack(fill="both", expand=True)
        self.players_list = tk.Listbox(players_inner, height=12, width=28, exportselection=False, font=self.font_body, bg=self.theme_colors['SECONDARY'], fg=self.theme_colors['TEXT'], selectbackground=self.theme_colors['ACCENT'], selectforeground=self.theme_colors['PRIMARY'], relief="solid", bd=1, highlightthickness=0, borderwidth=1); self.players_list.pack(anchor="w", pady=(0, 8))
        self.player_count_var = tk.StringVar(); tk.Label(players_inner, textvariable=self.player_count_var, font=self.font_small, bg=self.theme_colors['SURFACE'], fg=self.theme_colors['TEXT_SECONDARY']).pack(anchor="w", pady=(0, 10))
        form = tk.Frame(players_inner, bg=self.theme_colors['SURFACE']); form.pack(anchor="w", fill="x", pady=(0, 8)); tk.Label(form, text="Add player:", font=self.font_body, bg=self.theme_colors['SURFACE'], fg=self.theme_colors['TEXT']).grid(row=0, column=0, sticky="w")
        self.player_name_var = tk.StringVar(); tk.Entry(form, textvariable=self.player_name_var, width=18, font=self.font_body, relief="solid", bd=1, bg=self.theme_colors['SECONDARY'], fg=self.theme_colors['TEXT'], insertbackground=self.theme_colors['TEXT'], highlightthickness=0).grid(row=0, column=1, padx=(8, 5))
        self._create_styled_button(form, "Add", self.add_player, "success").grid(row=0, column=2); self._create_styled_button(players_inner, "Remove Selected", self.remove_selected, "error").pack(anchor="w", pady=(0, 5))
        status_frame = ttk.LabelFrame(left, text="Status"); status_frame.pack(fill="x", pady=(0, 15)); status_inner = tk.Frame(status_frame, bg=self.theme_colors['SURFACE'], padx=15, pady=10); status_inner.pack(fill="both", expand=True)
        self.status_var = tk.StringVar(); self.status_label = tk.Label(status_inner, textvariable=self.status_var, font=self.font_body, bg=self.theme_colors['SURFACE'], fg=self.theme_colors['TEXT'], wraplength=280, justify="left"); self.status_label.pack(anchor="w", pady=(0, 10))
        tk.Label(status_inner, text="Random seed (optional):", font=self.font_body, bg=self.theme_colors['SURFACE'], fg=self.theme_colors['TEXT']).pack(anchor="w")
        self.seed_var = tk.StringVar(value=""); tk.Entry(status_inner, textvariable=self.seed_var, width=20, font=self.font_body, relief="solid", bd=1, bg=self.theme_colors['SECONDARY'], fg=self.theme_colors['TEXT'], insertbackground=self.theme_colors['TEXT'], highlightthickness=0).pack(anchor="w", pady=(5, 0))
        control_frame = ttk.LabelFrame(left, text="Controls"); control_frame.pack(fill="x", pady=(0, 15)); control_inner = tk.Frame(control_frame, bg=self.theme_colors['SURFACE'], padx=15, pady=10); control_inner.pack(fill="both", expand=True)
        self.start_btn = self._create_styled_button(control_inner, "Start Tournament", self.start_tournament, "success"); self.pair_btn = self._create_styled_button(control_inner, "Pair Next", self.pair_next_round, "primary", state=tk.DISABLED); self.submit_btn = self._create_styled_button(control_inner, "Submit", self.submit_results, "success", state=tk.DISABLED); self.undo_btn = self._create_styled_button(control_inner, "Undo Round", self.undo_last_round, "warning", state=tk.DISABLED); self.export_btn = self._create_styled_button(control_inner, "Export", self.export_now, "secondary"); self.import_btn = self._create_styled_button(control_inner, "Import", self.import_state, "secondary"); self.reset_btn = self._create_styled_button(control_inner, "Reset", self.reset_tournament, "error")
        control_inner.grid_columnconfigure((0, 1, 2), weight=1)
        self.start_btn.grid(row=0, column=0, columnspan=3, sticky="ew", pady=4, padx=1); self.pair_btn.grid(row=1, column=0, sticky="ew", pady=2, padx=1); self.submit_btn.grid(row=1, column=1, sticky="ew", pady=2, padx=1); self.undo_btn.grid(row=1, column=2, sticky="ew", pady=2, padx=1); self.import_btn.grid(row=2, column=0, sticky="ew", pady=2, padx=1); self.export_btn.grid(row=2, column=1, sticky="ew", pady=2, padx=1); self.reset_btn.grid(row=2, column=2, sticky="ew", pady=2, padx=1)
    
    def _build_right_panel(self):
        right = tk.Frame(self, bg=self.theme_colors['BACKGROUND'], padx=15, pady=15); right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        head = tk.Frame(right, bg=self.theme_colors['BACKGROUND']); head.pack(fill=tk.X, pady=(0, 15))
        self.round_label = tk.Label(head, text="Round: —", font=self.font_title, bg=self.theme_colors['BACKGROUND'], fg=self.theme_colors['TEXT']); self.round_label.pack(side=tk.LEFT)
        self.decks_container = tk.Frame(right, bg=self.theme_colors['BACKGROUND']); self.decks_container.pack(fill=tk.X, pady=(0, 10))
        self.pairings_frame = ttk.LabelFrame(right, text="Current Round Pairings"); self.pairings_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        self.standings_container = tk.Frame(right, bg=self.theme_colors['BACKGROUND']); self.standings_container.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

    def _clear_container(self, container): [w.destroy() for w in container.winfo_children()]
    def _show_decks_as_button(self): self._clear_container(self.decks_container); self._create_styled_button(self.decks_container, "View Decks & Maps", self._show_decks_window, "secondary").pack(expand=True, fill=tk.X)
    def _show_decks_as_embedded(self):
        self._clear_container(self.decks_container); frame = ttk.LabelFrame(self.decks_container, text="Tables, Decks & Maps"); frame.pack(fill=tk.X); inner = tk.Frame(frame, bg=self.theme_colors['SURFACE'], padx=10, pady=10); inner.pack(fill="both", expand=True)
        tree = ttk.Treeview(inner, columns=("Table", "Map", "Deck 1", "Deck 2", "Deck 3", "Deck 4"), show="headings", height=12, style="Custom.Treeview")
        for col, w in [("Table", 60), ("Map", 180), ("Deck 1", 160), ("Deck 2", 160), ("Deck 3", 160), ("Deck 4", 160)]: tree.heading(col, text=col); tree.column(col, width=w, anchor="w")
        tree.pack(fill=tk.X, expand=False)
        for t, decks in sorted(self.tournament.tables_to_decks.items()): tree.insert("", tk.END, values=(t, self.tournament.tables_to_maps.get(t, ""), *decks))

    def _show_standings_as_button(self): self._clear_container(self.standings_container); self.standings_tree_embedded = None; self._create_styled_button(self.standings_container, "View Standings", self._show_standings_window, "secondary").pack(expand=True, fill=tk.X)
    def _show_standings_as_embedded(self):
        self._clear_container(self.standings_container); frame = ttk.LabelFrame(self.standings_container, text="Tournament Standings"); frame.pack(fill=tk.BOTH, expand=True); inner = tk.Frame(frame, bg=self.theme_colors['SURFACE'], padx=10, pady=10); inner.pack(fill="both", expand=True)
        self.standings_tree_embedded = ttk.Treeview(inner, columns=("Place", "Player", "Score", "Buchholz (W-L)"), show="headings", height=24, style="Custom.Treeview")
        for col, w in [("Place", 60), ("Player", 220), ("Score", 70), ("Buchholz (W-L)", 120)]: self.standings_tree_embedded.heading(col, text=col); self.standings_tree_embedded.column(col, width=w, anchor="center" if col != "Player" else "w")
        self.standings_tree_embedded.pack(fill=tk.BOTH, expand=True); self._refresh_standings()

    def _show_decks_window(self):
        if self.decks_window and self.decks_window.winfo_exists(): return self.decks_window.lift()
        self.decks_window = tk.Toplevel(self); self.decks_window.title("Tables, Decks & Maps"); self.decks_window.configure(bg=self.theme_colors['SURFACE']); self.decks_window.geometry("950x420")
        tree = ttk.Treeview(self.decks_window, columns=("Table", "Map", "Deck 1", "Deck 2", "Deck 3", "Deck 4"), show="headings", height=12, style="Custom.Treeview")
        for col, w in [("Table", 60), ("Map", 180), ("Deck 1", 160), ("Deck 2", 160), ("Deck 3", 160), ("Deck 4", 160)]: tree.heading(col, text=col); tree.column(col, width=w, anchor="w")
        tree.pack(expand=True, fill='both', padx=10, pady=10)
        for t, decks in sorted(self.tournament.tables_to_decks.items()): tree.insert("", tk.END, values=(t, self.tournament.tables_to_maps.get(t, ""), *decks))

    def _show_standings_window(self):
        if self.standings_window and self.standings_window.winfo_exists(): return self.standings_window.lift()
        self.standings_window = tk.Toplevel(self); self.standings_window.title("Tournament Standings"); self.standings_window.configure(bg=self.theme_colors['SURFACE']); self.standings_window.geometry("520x720")
        self.standings_tree_toplevel = ttk.Treeview(self.standings_window, columns=("Place", "Player", "Score", "Buchholz (W-L)"), show="headings", height=24, style="Custom.Treeview")
        for col, w in [("Place", 60), ("Player", 220), ("Score", 70), ("Buchholz (W-L)", 120)]: self.standings_tree_toplevel.heading(col, text=col); self.standings_tree_toplevel.column(col, width=w, anchor="center" if col != "Player" else "w")
        self.standings_tree_toplevel.pack(expand=True, fill='both', padx=10, pady=10); self._refresh_standings()

    def _populate_standings_tree(self, tree_widget):
        if not tree_widget: return
        for i in tree_widget.get_children(): tree_widget.delete(i)
        for place, name, sc, buch in self.tournament.get_standings_with_places(): tree_widget.insert("", tk.END, values=(place, name, sc, buch))
    
    def _refresh_standings(self):
        if self.standings_tree_embedded and self.standings_tree_embedded.winfo_exists(): self._populate_standings_tree(self.standings_tree_embedded)
        if self.standings_tree_toplevel and self.standings_tree_toplevel.winfo_exists(): self._populate_standings_tree(self.standings_tree_toplevel)

    def _render_pairings(self):
        for w in self.pairings_frame.winfo_children(): w.destroy()
        self.result_vars.clear(); main_frame = tk.Frame(self.pairings_frame, bg=self.theme_colors['SURFACE'], padx=10, pady=10); main_frame.pack(fill="both", expand=True)
        rows = sorted(self.tournament.current_table_pairs.items()); num_columns = 2
        for i in range(num_columns): main_frame.grid_columnconfigure(i, weight=1, uniform="group1")
        for i, (t, (p1, p2)) in enumerate(rows):
            r, c = divmod(i, num_columns); card = tk.Frame(main_frame, bg=self.theme_colors['SECONDARY'], relief="solid", bd=1); card.grid(row=r, column=c, sticky="ew", padx=5, pady=5); card.grid_columnconfigure(1, weight=1)
            tk.Label(card, text=f"#{t}", bg=self.theme_colors['ACCENT'], fg=self.theme_colors['PRIMARY'], font=self.font_heading, width=4).grid(row=0, column=0, rowspan=2, sticky="ns", padx=5, pady=5)
            tk.Label(card, text=f"{p1} vs {p2}", bg=self.theme_colors['SECONDARY'], fg=self.theme_colors['TEXT'], font=self.font_body, anchor='w').grid(row=0, column=1, sticky='ew', padx=5, pady=(5,0))
            tk.Label(card, text=f"Map: {self.tournament.tables_to_maps.get(t, '')}", bg=self.theme_colors['SECONDARY'], fg=self.theme_colors['TEXT_SECONDARY'], font=self.font_small, anchor='w').grid(row=1, column=1, sticky='ew', padx=5, pady=(0,5))
            var = tk.StringVar(); self.result_vars[t] = var; wf = tk.Frame(card, bg=self.theme_colors['SECONDARY']); wf.grid(row=0, column=2, rowspan=2, sticky="ns", padx=5)
            tk.Radiobutton(wf, text=p1, variable=var, value=p1, bg=self.theme_colors['SECONDARY'], fg=self.theme_colors['TEXT'], selectcolor=self.theme_colors['SURFACE'], activebackground=self.theme_colors['SECONDARY'], relief="flat", highlightthickness=0).pack(anchor="w")
            tk.Radiobutton(wf, text=p2, variable=var, value=p2, bg=self.theme_colors['SECONDARY'], fg=self.theme_colors['TEXT'], selectcolor=self.theme_colors['SURFACE'], activebackground=self.theme_colors['SECONDARY'], relief="flat", highlightthickness=0).pack(anchor="w")

    def _render_empty_pairings(self):
        for w in self.pairings_frame.winfo_children(): w.destroy()
        inner = tk.Frame(self.pairings_frame, bg=self.theme_colors['SURFACE']); inner.pack(fill="both", expand=True)
        tk.Label(inner, text="No active round pairings", font=self.font_body, bg=self.theme_colors['SURFACE'], fg=self.theme_colors['TEXT_SECONDARY']).pack(expand=True)
        tk.Label(inner, text="Click 'Pair Next' to generate matchups", font=self.font_small, bg=self.theme_colors['SURFACE'], fg=self.theme_colors['TEXT_SECONDARY']).pack()

    def _update_status(self, message, status_type="info"): self.status_var.set(message); self.status_label.config(fg={"success": self.theme_colors['SUCCESS'], "warning": self.theme_colors['WARNING'], "error": self.theme_colors['ERROR']}.get(status_type, self.theme_colors['TEXT']))
    def _update_players_list(self):
        self.players_list.delete(0, tk.END)
        for p in self.tournament.players: self.players_list.insert(tk.END, p)
        self.player_count_var.set(f"Players: {len(self.tournament.players)} / {NUM_TABLES * SEATS_PER_TABLE}")

    def add_player(self): name = self.player_name_var.get().strip();_ = name and self.tournament.add_player(name) and (self.player_name_var.set(""), self._update_players_list())
    def remove_selected(self):
        if self.tournament.round_no > 0: return
        for i in reversed(self.players_list.curselection()): self.tournament.remove_player(self.tournament.players[i])
        self._update_players_list()

    def start_tournament(self):
        can_start, error = self.tournament.can_start_tournament();
        if not can_start: return messagebox.showerror("Error", error)
        self.tournament.set_seed(self.seed_var.get().strip()); self.tournament.start_tournament()
        self._update_status("Tournament started. Click 'Pair Next'.", "success"); self.round_label.config(text=f"Round: {self.tournament.round_no}/{ROUNDS}")
        self._show_decks_as_embedded(); self._update_button_states()
        try: autosave(self.tournament, reason="start")
        except Exception as e: messagebox.showwarning("Autosave failed", str(e))

    def pair_next_round(self):
        can_pair, error = self.tournament.can_pair_next_round();
        if not can_pair: return messagebox.showinfo("Info", error)
        self.tournament.pair_next_round(); self.round_label.config(text=f"Round: {self.tournament.round_no}/{ROUNDS}")
        self._render_pairings(); self._update_status("Select winners and click 'Submit'.", "warning")
        if self.tournament.round_no == 1: self._show_decks_as_button()
        self._show_standings_as_button(); self._update_button_states()

    def submit_results(self):
        winners, missing_tables = {}, []
        for t, (p1, p2) in self.tournament.current_table_pairs.items():
            sel = self.result_vars[t].get()
            if sel in (p1, p2): winners[t] = sel
            else: missing_tables.append(t)
        if missing_tables:
            missing_tables.sort(); messagebox.showerror("Missing Winners", f"Please select a winner for all tables.\nMissing tables: {', '.join(map(str, missing_tables))}")
            return
        self.tournament.snapshot_before_submit(); self.tournament.submit_results(winners)
        self._render_empty_pairings(); self._show_standings_as_embedded()
        self._update_button_states()
        if self.tournament.round_no >= ROUNDS: self._update_status("Tournament finished!", "success")
        else: self._update_status("Round saved. Click 'Pair Next'.", "success")
        try: autosave(self.tournament, reason="between_rounds")
        except Exception as e: messagebox.showwarning("Autosave failed", str(e))

    def undo_last_round(self):
        if not self.tournament.can_undo(): return
        self.tournament.undo_last_round(); self.round_label.config(text=f"Round: {self.tournament.round_no}/{ROUNDS}")
        self._render_pairings(); self._update_players_list()
        self._update_status("Undone last round. Re-select winners.", "warning")
        self._show_decks_as_button(); self._show_standings_as_embedded(); self._update_button_states()

    def reset_tournament(self):
        if messagebox.askyesno("Reset", "Reset the tournament to an empty state?"):
            self.tournament.reset(); self._update_status("Add players, then Start Tournament.", "info")
            self._update_players_list(); self._render_empty_pairings()
            self.round_label.config(text="Round: —")
            self._show_decks_as_button(); self._show_standings_as_button()
            self._refresh_standings(); self._update_button_states()

    def export_now(self):
        ensure_save_dir(); path = filedialog.asksaveasfilename(initialdir=SAVE_DIR, defaultextension=".json", filetypes=[("JSON files", "*.json")])
        if path:
            try: export_to_file(self.tournament, path)
            except Exception as e: messagebox.showerror("Save failed", str(e))

    def import_state(self):
        path = filedialog.askopenfilename(initialdir=SAVE_DIR, filetypes=[("JSON files", "*.json")])
        if not path: return
        try: import_from_file(path, self.tournament)
        except Exception as e: return messagebox.showerror("Load failed", str(e))
        self.rebuild_ui()

    def _on_close_autosave_then_exit(self):
        try: autosave(self.tournament, reason="on_exit")
        finally: self.destroy()
