# Swiss Tournament Management System

A comprehensive tournament management application for Swiss-style tournaments with 12 tables and 2 players per table.

## Features

- Swiss pairing system with optimal table assignment
- Tiebreaker system using Buchholz (W-L) and head-to-head
- Automatic save/load functionality
- Undo system for round corrections
- Deck and map assignment for tournament play

## Quick Start

### Option 1: Using Python directly
```bash
python3 main.py
```

### Option 2: Using the run script
```bash
./run.sh
```

### Option 3: Run main.py directly (already executable)
```bash
./main.py
```

## File Structure

The application has been decomposed into logical modules for better maintainability:

### Core Modules

- **`config.py`** - Tournament configuration and constants
  - Number of tables, players, rounds
  - Default deck pool and maps
  - Save directory settings

- **`swiss_logic.py`** - Tournament algorithms
  - Swiss pairing logic
  - Table assignment algorithms
  - Deck/map dealing functions
  - Tiebreaker calculations

- **`tournament_state.py`** - State management
  - `TournamentState` class managing all data
  - Business logic methods
  - Validation and error checking
  - Undo/snapshot functionality

- **`file_operations.py`** - Save/load functionality
  - JSON serialization/deserialization
  - Autosave and manual export/import
  - File system utilities

- **`ui.py`** - User interface
  - `SwissApp` Tkinter class
  - UI components and event handlers
  - Display logic and user interactions

- **`main.py`** - Application entry point
  - Startup logic
  - Optional preloaded players

### Helper Files

- **`run.sh`** - Convenience script to launch the app
- **`README.md`** - This documentation

## Usage

1. Launch the application using one of the methods above
2. Add players (or use the pre-loaded ones)
3. Start the tournament
4. Use "Pair Next Round" to generate pairings
5. Select winners for each table
6. Submit results
7. Repeat until all rounds are complete

## Development

The modular structure makes it easy to:
- Test individual components
- Modify tournament rules (edit `config.py`)
- Change pairing algorithms (edit `swiss_logic.py`)
- Add new UI features (edit `ui.py`)
- Implement different interfaces (reuse `swiss_logic.py` and `tournament_state.py`)

## Requirements

- Python 3.6+ with tkinter support
- No additional dependencies required

### Important: Python and tkinter

This app requires tkinter for the GUI. If you get a `ModuleNotFoundError: No module named '_tkinter'` error:

- **On macOS with Homebrew**: Run `brew install python-tk` to add tkinter support
- **Alternative**: Use system Python at `/usr/bin/python3` or install Python from python.org
- **On Linux**: Install `python3-tk` package: `sudo apt install python3-tk` (Ubuntu/Debian)

## UI Improvements

The app now features a modern, dark-themed interface with:
- 🌙 Beautiful dark theme with professional color scheme
- 🎨 Card-based layout with subtle borders and shadows
- 🖱️ Hover effects and modern styled buttons
- 📱 Better spacing and visual hierarchy
- 🎯 Color-coded status messages (green/yellow/red/blue)
- 🏆 Emojis and icons for enhanced UX
- 📊 Dark-themed table displays with alternating row colors
- 💾 Dark input fields and properly styled components
- ⚔️ Enhanced pairings display with full-width grid layout and mouse wheel scrolling 