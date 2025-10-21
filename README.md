# Blood Panel Rolodex

> _Track your blood panels like it's 1985, but with proper graphs._

An 80s-themed terminal user interface for tracking blood panel data. Hand-rendered rolodex cards, neon red/yellow aesthetic, instant SQLite backend, terminal graphs. No framework bloat, no cloud nonsense.

```
╔══════════════════════════════════════════════════════════════════════════════════════════════╗
║                                    HbA1c (mmol/mol)                                          ║
╟──────────────────────────────────────────────────────────────────────────────────────────────╢
║  2025-01-15  →  38.50 mmol/mol                                                               ║
║  2024-10-20  →  41.20 mmol/mol                                                               ║
║  2024-07-18  →  39.80 mmol/mol                                                               ║
╟──────────────────────────────────────────────────────────────────────────────────────────────╢
║                                                                                              ║
║    45 ┤                    ●                                                                 ║
║    40 ┤        ●       ●       ●                                                             ║
║    35 ┼────────────────────────────────────────                                             ║
║         2024-07    2024-10    2025-01                                                        ║
║                                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════════════════════╝
```

## Features

- **Artisanal Rolodex Interface**: 3-card perspective layout with proper scaling
  - Center card: full-size, bright neon red
  - Previous/next cards: 65% scale, dimmed
  - j/k or arrow keys to flip through
- **Terminal Graphs**: Plotext integration with date-series support
  - Red data line, yellow normal range indicators
  - Auto-scaling based on your data
  - Only renders on center card (no wasted cycles)
- **CRUD Operations**: Create, Read, Update, Delete entries
  - Add entries with date validation
  - Edit existing entries (pre-filled forms)
  - Delete with navigable list
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
- At least 120x40 terminal size

### Setup

```bash
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

1. Terminal will check size - resize to at least 120x40
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
| `q` | Quit |

## Typical Workflow

```bash
# 1. Launch
./run.sh

# 2. Navigate to component you just got blood work for
#    (press j/k until you see the right card)

# 3. Add new entry
#    Press 'n'
#    Enter value: 38.5
#    Enter date: [just hit Enter for today, or type YYYY-MM-DD]
#    Notes: (optional)

# 4. Graph updates instantly

# 5. Made a typo? Press 'e', select the entry, fix it

# 6. Done? Press 'q'
```

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
2. Render prev/next cards if >1 component (dimmed, scaled)
3. Render current card (full brightness, full scale)
4. Embed plotext graph in current card
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
    normal_max REAL
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

**Solution**: Your terminal is too small. Minimum 120x40.
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

## Development Notes

### Why blessed instead of Textual/Rich?

Textual wants to give you layouts and widgets. We're hand-drawing a rolodex with perspective scaling. That requires manual character positioning. blessed gives us low-level terminal control without the curses pain.

### Why SQLite instead of JSON/CSV?

Because querying. "Give me last 10 entries for component X ordered by date" is one line of SQL. In JSON you're parsing, filtering, sorting in Python. SQLite is instant even with thousands of entries.

### Why not use a web interface?

Because terminal is faster. No browser, no server, no webpack, no JavaScript. Just pure data entry at typing speed.

### Performance Characteristics

- **Startup time**: ~50ms (SQLite connection + component load)
- **Render time**: <10ms for full screen redraw
- **Input latency**: <5ms (blocking inkey, event-driven)
- **Database queries**: <1ms for typical operations

Tested with 100 components and 10,000 entries - still instant.

## Future Ideas (You'll Never Build These)

- Export to CSV/JSON
- Import from lab results PDF
- Plotting multiple components on same graph
- Trend analysis / moving averages
- Notifications when values go out of range
- Sync to cloud (encrypted)
- Mobile companion app
- AI health insights
- Integration with Apple Health
- Multi-user support
- Backup/restore functionality

But honestly, you probably just need to track HbA1c, creatinine, and LDL. The current feature set is fine.

## License

Do whatever you want with this code. It's a single-file Python script for personal health tracking. If it helps you, great. If you improve it, cool. No warranty, no support, no corporate bullshit.

## Acknowledgments

Built with:
- A terminal emulator
- Too much caffeine
- A proper understanding that "shipped" beats "perfect"

Inspired by every over-engineered health tracking app that requires an account, subscription, and privacy policy to track a single number.
