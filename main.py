#!/usr/bin/env python3
"""
Swiss Tournament Management System - Main Entry Point

A comprehensive tournament management application for Swiss-style tournaments
with 12 tables and 2 players per table.

Features:
- Swiss pairing system with optimal table assignment
- Tiebreaker system using Buchholz (W-L) and head-to-head
- Automatic save/load functionality
- Undo system for round corrections
- Deck and map assignment for tournament play

Usage: python3 main.py (or ./main.py)
"""

from ui import SwissApp


def main():
    """Main entry point for the Swiss Tournament application."""
    app = SwissApp()
    
    # Optional: preload players so you don't have to type them manually.
    # Comment out or modify this list as needed.
    initial_players = [
        "Alice", "Bob", "Charlie", "Diana",
        "Eve", "Frank", "Grace", "Heidi",
        "Ivan", "Judy", "Karl", "Laura",
        "Mallory", "Niaj", "Olivia", "Peggy",
        "Quentin", "Rupert", "Sybil", "Trent",
        "Uma", "Victor", "Wendy", "Xander"
    ]
    
    # Add initial players to the tournament
    for player in initial_players:
        app.tournament.add_player(player)
    app._update_players_list()
    
    # Start the GUI
    app.mainloop()


if __name__ == "__main__":
    main() 