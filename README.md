# Blood Panel Rolodex

> _Track your blood panels like it's 1985_

An 80's themed blood panel data tracker.



## Features

- **Artisanal Rolodex Interface**: Stationary component list
  - Selected component: bright neon red (no arrow for space saving)
  - Nearby components: perspective-scaled (80% brightness)
  - j/k or arrow keys to navigate
  - Long titles displayed below boxes for detailed descriptions
- **Value Boxes**: Three boxes showing latest entries (oldest to newest, left to right)
  - Double-line borders (╔═╗║╚╝) for that retro thickness
  - Shortened YY-MM-DD dates above each box
  - Bold yellow numbers, centered and legible
- **Terminal Graphs**: Manual ASCII graph rendering with date-series support
  - Red dots (●) showing trend over time
  - Yellow Y-axis scale indicators
  - Auto-scaling based on your data
  - 25×12 compact format
- **CRUD Operations**: Create, Read, Update, Delete entries
  - Add entries with date validation
  - Edit existing entries (pre-filled forms)
  - Delete with navigable list
  - Export all data to CSV for backup
- **Neon Aesthetic**: Warm 80s blood-red theme
  - RGB(255, 0, 0) primary borders/text
  - RGB(255, 215, 0) accents and highlights
  - Full black background override (works even if your terminal is light mode)
- **Performance**: Event-driven rendering, no flicker
  - SQLite for instant local queries
  - No network, no frameworks fighting you
  - Renders only on input events
- **Terminal Calibration**: Won't let you run until your terminal is sized right

## Installation

### Prerequisites

- Python 3.10 or newer
- Terminal emulator with 256-color support (tested on Alacritty, iTerm2, Terminal.app)
- At least 80x24 terminal size
- cool-retro-term recommended for peak aesthetic

### Setup

```bash
# (Optional) Install cool-retro-term
brew install --cask cool-retro-term

# Clone/download this repo
cd health

# Create virtual environment and install dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run it
./run.sh
```

Or use the venv directly:
```bash
./venv/bin/python blood_panel.py
```

### First Run

1. Terminal will check size - resize to at least 80x24
2. Welcome screen prompts you to create your first component
3. Enter component details:
   - Name: e.g., "HbA1c", "Creatinine", "LDL Cholesterol"
   - Unit: e.g., "mmol/mol", "mg/dL", "µmol/L"
   - Normal range min/max (optional but recommended for graph indicators)
4. You're in the rolodex

## Controls

| Key | Action |
|-----|--------|
| `j` / `k` / `↑` / `↓` | Navigate between components (rolodex flipping) |
| `n` | Add new entry for current component |
| `e` | Edit existing entry (shows list, arrow keys to select) |
| `d` | Delete entry (shows list, arrow keys to select) |
| `c` | Create new component |
| `s` | Edit component settings (name, unit, long title, normal ranges) |
| `x` | Export all data to CSV (backup) |
| `q` | Quit |

## Architecture

### File Structure

```
health/
├── blood_panel.py      # Main application (~950 lines)
├── blood_panels.db     # SQLite database (created on first run)
├── requirements.txt    # blessed, plotext
├── run.sh             # Quick launcher
├── venv/              # Python virtual environment
└── README.md          # You are here
```

### Code Organization

**Data Layer** (`Database` class):
- SQLite with two tables: `components` and `entries`
- Simple CRUD operations, no ORM overhead
- Indexed on component_id and date for fast queries

**UI Layer** (`BloodPanelUI` class):
- Manual character-by-character rendering with `blessed`
- Event-driven main loop (blocking input, render on change)
- Modal system for forms (create, edit, delete)
- Custom input handling with cursor support

**Rendering Pipeline**:
1. Paint entire screen black (override terminal background)
2. Render scrolling component list with stationary arrow (perspective scaling)
3. Render three value boxes showing latest entries
4. Render ASCII graph with red dots and yellow scale
5. Show controls at bottom

### Technologies

- **blessed**: Terminal control library (better than raw curses)
  - RGB color support
  - Character positioning
  - Keyboard input handling
- **plotext**: Terminal plotting library
  - Date-series support
  - Configurable sizing
  - Color customization
- **SQLite**: Local database (via stdlib `sqlite3`)
  - Single file storage
  - ACID transactions
  - No server required

## Data Format

### Database Schema

**Components Table**:
```sql
CREATE TABLE components (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    unit TEXT NOT NULL,
    normal_min REAL,
    normal_max REAL,
    long_title TEXT DEFAULT ''
)
```

**Entries Table**:
```sql
CREATE TABLE entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    component_id INTEGER NOT NULL,
    value REAL NOT NULL,
    date TEXT NOT NULL,  -- ISO format YYYY-MM-DD
    notes TEXT,
    FOREIGN KEY (component_id) REFERENCES components(id)
)
```

### Date Format

**IMPORTANT**: All dates are stored in ISO format (`YYYY-MM-DD`). The app will reject other formats.

Examples:
- ✅ `2025-01-15`
- ✅ `2024-12-01`
- ❌ `01/15/2025`
- ❌ `15-01-2025`

## Troubleshooting

### Terminal Size Issues

**Problem**: "TERMINAL CALIBRATION REQUIRED" won't go away

**Solution**: Your terminal is too small. Minimum 80x24.
- macOS: Cmd+Plus to increase font size, or resize window
- Linux: Right-click title bar → Preferences → Initial terminal size

### Graphs Not Showing

**Problem**: Graph area shows "(need 2+ entries for graph)"

**Solution**: You need at least 2 data points to render a graph. Add another entry.

### Flickering/Visual Artifacts

**Problem**: Screen flickers or leaves artifacts

**Solution**:
- Update your terminal emulator
- Try a different terminal (Alacritty, iTerm2, kitty all work great)
- Check that your terminal supports 256 colors: `echo $TERM` should show something like `xterm-256color`

### Input Appearing in Wrong Place

**Problem**: Text shows up in corner instead of input boxes

**Solution**: Fixed in current version (we flush stdout after drawing modals). If you still see this, your terminal emulator may have rendering lag - try reducing terminal size or switching emulators.

### Date Format Errors

**Problem**: "Date Form should be: %d/%m/%Y" error

**Solution**: Fixed in current version (we configure plotext for ISO dates). Delete your `blood_panels.db` and start fresh if you have old bad data.

## License

Do whatever you want with this code. It's a single-file Python script for personal health tracking. If it helps you, great. If you improve it, cool. No warranty, no support, no corporate bullshit.

## Acknowledgments

Built with:
- Claude!
