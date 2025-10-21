#!/usr/bin/env python3
"""
Blood Panel Rolodex - 80s Neon TUI Interface
Track your blood panel data with style.
"""

import sqlite3
import sys
from datetime import datetime, date
from typing import List, Optional, Tuple
from dataclasses import dataclass
import plotext as plt
from blessed import Terminal


# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class Component:
    """A blood panel component (e.g., HbA1c, Creatinine)"""
    id: Optional[int]
    name: str
    unit: str
    normal_min: Optional[float]
    normal_max: Optional[float]


@dataclass
class Entry:
    """A single measurement entry for a component"""
    id: Optional[int]
    component_id: int
    value: float
    date: str  # ISO format YYYY-MM-DD
    notes: str = ""


# ============================================================================
# DATABASE
# ============================================================================

class Database:
    """SQLite database manager for blood panel data"""

    def __init__(self, db_path: str = "blood_panels.db"):
        self.db_path = db_path
        self.conn = None
        self._init_db()

    def _init_db(self):
        """Initialize database connection and create tables if needed"""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row

        cursor = self.conn.cursor()

        # Components table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS components (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                unit TEXT NOT NULL,
                normal_min REAL,
                normal_max REAL
            )
        """)

        # Entries table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                component_id INTEGER NOT NULL,
                value REAL NOT NULL,
                date TEXT NOT NULL,
                notes TEXT,
                FOREIGN KEY (component_id) REFERENCES components(id)
            )
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_entries_component ON entries(component_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_entries_date ON entries(date)")

        self.conn.commit()

    def get_all_components(self) -> List[Component]:
        """Get all components ordered by name"""
        cursor = self.conn.cursor()
        rows = cursor.execute(
            "SELECT id, name, unit, normal_min, normal_max FROM components ORDER BY name"
        ).fetchall()

        return [Component(
            id=row['id'],
            name=row['name'],
            unit=row['unit'],
            normal_min=row['normal_min'],
            normal_max=row['normal_max']
        ) for row in rows]

    def create_component(self, component: Component) -> int:
        """Create a new component, returns the new ID"""
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO components (name, unit, normal_min, normal_max) VALUES (?, ?, ?, ?)",
            (component.name, component.unit, component.normal_min, component.normal_max)
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_entries_for_component(self, component_id: int, limit: Optional[int] = None) -> List[Entry]:
        """Get entries for a component, ordered by date descending"""
        cursor = self.conn.cursor()
        query = """
            SELECT id, component_id, value, date, notes
            FROM entries
            WHERE component_id = ?
            ORDER BY date DESC
        """
        if limit:
            query += f" LIMIT {limit}"

        rows = cursor.execute(query, (component_id,)).fetchall()

        return [Entry(
            id=row['id'],
            component_id=row['component_id'],
            value=row['value'],
            date=row['date'],
            notes=row['notes'] or ""
        ) for row in rows]

    def add_entry(self, entry: Entry) -> int:
        """Add a new entry, returns the new ID"""
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO entries (component_id, value, date, notes) VALUES (?, ?, ?, ?)",
            (entry.component_id, entry.value, entry.date, entry.notes)
        )
        self.conn.commit()
        return cursor.lastrowid

    def update_entry(self, entry: Entry):
        """Update an existing entry"""
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE entries SET value = ?, date = ?, notes = ? WHERE id = ?",
            (entry.value, entry.date, entry.notes, entry.id)
        )
        self.conn.commit()

    def delete_entry(self, entry_id: int):
        """Delete an entry by ID"""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM entries WHERE id = ?", (entry_id,))
        self.conn.commit()

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()


# ============================================================================
# TERMINAL RENDERING
# ============================================================================

class BloodPanelUI:
    """Main UI controller for the blood panel rolodex"""

    # Minimum terminal dimensions
    MIN_WIDTH = 120
    MIN_HEIGHT = 40

    # ASCII art digits (3 lines tall, 3 chars wide)
    ASCII_DIGITS = {
        '0': [
            "▄█▄",
            "█ █",
            "▀█▀"
        ],
        '1': [
            " █ ",
            "▄█ ",
            "▀█▀"
        ],
        '2': [
            "▄█▄",
            " ▄▀",
            "█▄▄"
        ],
        '3': [
            "▄█▄",
            " ▄█",
            "▄█▀"
        ],
        '4': [
            "█ █",
            "▀▀█",
            "  █"
        ],
        '5': [
            "█▄▄",
            "▀▄█",
            "▄█▀"
        ],
        '6': [
            "▄█▄",
            "█▄▄",
            "▀█▀"
        ],
        '7': [
            "▄▄█",
            "  █",
            " █ "
        ],
        '8': [
            "▄█▄",
            "▄█▄",
            "▀█▀"
        ],
        '9': [
            "▄█▄",
            "▀▀█",
            "▄█▀"
        ],
        '.': [
            "   ",
            "   ",
            " ▄ "
        ],
        '-': [
            "   ",
            "───",
            "   "
        ],
        ' ': [
            "   ",
            "   ",
            "   "
        ]
    }

    def __init__(self, db: Database):
        self.db = db
        self.term = Terminal()
        self.current_index = 0
        self.components = []
        self.running = True

    def run(self):
        """Main entry point"""
        # Calibration screen
        if not self._calibrate_terminal():
            return

        # Load components
        self.components = self.db.get_all_components()
        if not self.components:
            self._first_time_setup()
            self.components = self.db.get_all_components()

        # Main loop
        with self.term.hidden_cursor(), self.term.cbreak(), self.term.fullscreen():
            self._main_loop()

    def _calibrate_terminal(self) -> bool:
        """Show calibration screen until terminal is sized correctly"""
        print(self.term.clear())

        while True:
            width, height = self.term.width, self.term.height

            if width >= self.MIN_WIDTH and height >= self.MIN_HEIGHT:
                # Terminal is good size
                x = self.term.width // 2 - 15
                y = self.term.height // 2

                with self.term.location(x, y):
                    print(self.term.bold_yellow("TERMINAL SIZE OK"))
                with self.term.location(x, y + 1):
                    print(self.term.red("Press any key to continue..."))

                # Wait for keypress
                with self.term.cbreak():
                    key = self.term.inkey(timeout=0.5)
                    if key:
                        return True
            else:
                # Show calibration message
                print(self.term.home() + self.term.clear())

                lines = [
                    "╔════════════════════════════════════════╗",
                    "║   TERMINAL CALIBRATION REQUIRED        ║",
                    "╚════════════════════════════════════════╝",
                    "",
                    f"Current size: {width}x{height}",
                    f"Required:     {self.MIN_WIDTH}x{self.MIN_HEIGHT}",
                    "",
                    "Please resize your terminal window",
                ]

                start_y = max(0, (height - len(lines)) // 2)
                for i, line in enumerate(lines):
                    x = max(0, (width - len(line)) // 2)
                    with self.term.location(x, start_y + i):
                        if "╔" in line or "║" in line or "╚" in line:
                            print(self.term.bold_red(line))
                        elif "Current" in line or "Required" in line:
                            print(self.term.yellow(line))
                        else:
                            print(self.term.red(line))

                # Check for quit
                with self.term.cbreak():
                    key = self.term.inkey(timeout=0.5)
                    if key and key.lower() == 'q':
                        return False

    def _render_big_number(self, value_str: str) -> str:
        """Render a number as single bold text"""
        # Limit to reasonable length
        value_str = str(value_str)[:8]
        return value_str

    def _first_time_setup(self):
        """Show welcome screen and create first component"""
        print(self.term.home() + self.term.clear())

        lines = [
            "╔════════════════════════════════════════════════════════════╗",
            "║          WELCOME TO BLOOD PANEL ROLODEX                    ║",
            "╚════════════════════════════════════════════════════════════╝",
            "",
            "  No components found. Let's create your first one!",
            "",
            "  Examples: HbA1c, Creatinine, LDL Cholesterol, Glucose",
            "",
            "  Press any key to continue...",
        ]

        start_y = self.term.height // 2 - len(lines) // 2
        for i, line in enumerate(lines):
            x = (self.term.width - len(line)) // 2
            with self.term.location(x, start_y + i):
                if "╔" in line or "║" in line or "╚" in line:
                    print(self.term.bold(self.term.color_rgb(255, 0, 0)(line)))
                elif "WELCOME" in line:
                    print(self.term.bold(self.term.color_rgb(255, 215, 0)(line)))
                else:
                    print(self.term.color_rgb(255, 80, 80)(line))

        with self.term.cbreak():
            self.term.inkey()

        # Actually create a real component via the modal
        self._show_create_component_modal()

    def _main_loop(self):
        """Main rendering and input loop"""
        # Initial render
        self._render()

        while self.running:
            # Wait for input (blocking, no constant redraw)
            with self.term.cbreak():
                key = self.term.inkey()
                if key:
                    self._handle_input(key)
                    # Only redraw after handling input
                    if self.running:  # Don't render if we're quitting
                        self._render()

    def _render(self):
        """Render the dashboard with rolodex component list, value boxes, and graph"""
        # Clear screen and paint black background
        print(self.term.home() + self.term.clear())

        # Paint entire screen black to override terminal background
        for y in range(self.term.height):
            with self.term.location(0, y):
                print(self.term.on_black(" " * self.term.width))

        if not self.components:
            self._render_empty_state()
            return

        # Get current component
        component = self.components[self.current_index]
        entries = self.db.get_entries_for_component(component.id)

        # Layout positions (vertically centered)
        center_y = self.term.height // 2
        arrow_y = center_y

        left_x = 2
        arrow_x = 6
        name_x = 10
        box1_x = 35
        box2_x = 48
        box3_x = 61
        graph_x = 80

        # === LEFT: Scrolling component list with stationary arrow ===
        # Show 2 components above and 2 below the selected one
        num_components = len(self.components)

        for offset in [-2, -1, 0, 1, 2]:
            idx = (self.current_index + offset) % num_components
            comp = self.components[idx]
            y = arrow_y + (offset * 2)  # 2 lines spacing between components

            # Perspective scaling
            if offset == 0:
                # Selected component - bright and bold
                name_display = f"{comp.name} ({comp.unit})"
                # Truncate long names
                if len(name_display) > 20:
                    name_display = name_display[:17] + "..."

                # Arrow
                with self.term.location(arrow_x, y):
                    print(self.term.bold(self.term.color_rgb(255, 215, 0)("──>")))

                # Name
                with self.term.location(name_x, y):
                    print(self.term.bold(self.term.color_rgb(255, 0, 0)(name_display)))
            elif abs(offset) == 1:
                # ±1 position - 80% brightness, smaller
                name_display = comp.name[:15]
                with self.term.location(name_x + 2, y):
                    print(self.term.color_rgb(180, 0, 0)(name_display))
            else:
                # ±2 position - 60% brightness, even smaller
                name_display = comp.name[:12]
                with self.term.location(name_x + 4, y):
                    print(self.term.color_rgb(120, 0, 0)(name_display))

        # === CENTER: Three value boxes ===
        latest_3 = entries[:3] if len(entries) >= 3 else entries + [None] * (3 - len(entries))
        latest_3.reverse()  # Oldest to newest (left to right)

        box_positions = [box1_x, box2_x, box3_x]
        for i, (box_x, entry) in enumerate(zip(box_positions, latest_3)):
            self._render_value_box(box_x, center_y - 3, entry, component.unit)

        # === RIGHT: Fixed square graph ===
        if len(entries) >= 2:
            self._render_small_graph(graph_x, center_y - 10, component, entries)
        else:
            # Not enough data for graph
            with self.term.location(graph_x + 5, center_y):
                print(self.term.yellow("Need 2+"))
            with self.term.location(graph_x + 5, center_y + 1):
                print(self.term.yellow("entries"))

        # Show controls at bottom
        controls = "j/k/↑↓: nav  │  n: new  │  e: edit  │  d: delete  │  c: component  │  q: quit"
        with self.term.location((self.term.width - len(controls)) // 2, self.term.height - 2):
            print(self.term.on_black(self.term.red(controls)))

    def _render_value_box(self, x: int, y: int, entry: Optional[Entry], unit: str):
        """Render a single value box with date above and large text number"""
        box_width = 11
        box_height = 5

        # Date above box (if entry exists)
        if entry:
            # Full date YYYY-MM-DD above the box
            with self.term.location(x, y - 1):
                print(self.term.yellow(entry.date))

        # Draw box border with double-line characters
        top = "╔" + "═" * (box_width - 2) + "╗"
        bottom = "╚" + "═" * (box_width - 2) + "╝"

        with self.term.location(x, y):
            print(self.term.color_rgb(255, 0, 0)(top))

        for i in range(1, box_height - 1):
            with self.term.location(x, y + i):
                print(self.term.color_rgb(255, 0, 0)("║" + " " * (box_width - 2) + "║"))

        with self.term.location(x, y + box_height - 1):
            print(self.term.color_rgb(255, 0, 0)(bottom))

        # Draw content
        if entry:
            # Single bold number, centered
            value_str = f"{entry.value:.1f}"
            display_str = self._render_big_number(value_str)

            # Center horizontally
            padding = (box_width - 2 - len(display_str)) // 2
            centered = " " * padding + display_str

            # Vertically center in box (box is 5 tall, so put at line 2)
            with self.term.location(x + 1, y + 2):
                print(self.term.bold(self.term.color_rgb(255, 215, 0)(centered)))
        else:
            # Empty box - show placeholder, centered
            with self.term.location(x + 3, y + 2):
                print(self.term.color_rgb(100, 100, 100)("---"))

    def _render_small_graph(self, x: int, y: int, component: Component, entries: List[Entry]):
        """Render a wide graph with just dots showing trend"""
        graph_width = 35
        graph_height = 18

        # Draw graph border with double-line characters
        top = "╔" + "═" * (graph_width - 2) + "╗"
        bottom = "╚" + "═" * (graph_width - 2) + "╝"

        with self.term.location(x, y):
            print(self.term.color_rgb(255, 0, 0)(top))

        for i in range(1, graph_height - 1):
            with self.term.location(x, y + i):
                print(self.term.color_rgb(255, 0, 0)("║" + " " * (graph_width - 2) + "║"))

        with self.term.location(x, y + graph_height - 1):
            print(self.term.color_rgb(255, 0, 0)(bottom))

        # Manual graph rendering - just dots, no lines
        sorted_entries = sorted(entries, key=lambda e: e.date)
        values = [e.value for e in sorted_entries]

        if len(values) < 2:
            with self.term.location(x + 10, y + 8):
                print(self.term.yellow("Need 2+"))
            return

        # Calculate graph area
        graph_w = graph_width - 4
        graph_h = graph_height - 4

        # Find min/max for scaling
        min_val = min(values)
        max_val = max(values)

        # Add some padding to range
        val_range = max_val - min_val
        if val_range == 0:
            val_range = 1
        min_val -= val_range * 0.1
        max_val += val_range * 0.1
        val_range = max_val - min_val

        # Draw dots only
        for i, val in enumerate(values):
            # Calculate position
            x_pos = int((i / (len(values) - 1)) * (graph_w - 1))
            y_pos = int((1 - (val - min_val) / val_range) * (graph_h - 1))

            # Draw dot
            with self.term.location(x + 2 + x_pos, y + 2 + y_pos):
                print(self.term.bold(self.term.color_rgb(255, 0, 0)("●")))

        # Draw Y-axis scale (min and max values)
        with self.term.location(x + 2, y + 2):
            print(self.term.yellow(f"{max_val:.1f}"))
        with self.term.location(x + 2, y + graph_height - 3):
            print(self.term.yellow(f"{min_val:.1f}"))

    def _render_card(self, component: Component, y_pos: int, scale: float, dimmed: bool):
        """Render a single component card with perspective scaling"""
        # Card dimensions
        base_width = 100
        base_height = 22  # Increased to fit graph
        card_width = int(base_width * scale)
        card_height = int(base_height * scale)

        # Center horizontally
        x_offset = (self.term.width - card_width) // 2

        # Get ALL entries for graphing
        all_entries = self.db.get_entries_for_component(component.id)
        latest_entries = all_entries[:3] if all_entries else []

        # Choose color based on dimmed state
        if dimmed:
            border_color = lambda s: self.term.color_rgb(128, 0, 0)(s)  # Dark red
            text_color = lambda s: self.term.color_rgb(180, 0, 0)(s)    # Medium red
            value_color = lambda s: self.term.color_rgb(150, 150, 0)(s) # Dim yellow
        else:
            border_color = lambda s: self.term.bold(self.term.color_rgb(255, 0, 0)(s))  # Bright red
            text_color = lambda s: self.term.color_rgb(255, 80, 80)(s)    # Light red
            value_color = lambda s: self.term.bold(self.term.color_rgb(255, 215, 0)(s)) # Bright yellow

        # Draw top border
        top_border = "╔" + "═" * (card_width - 2) + "╗"
        with self.term.location(x_offset, y_pos):
            print(border_color(top_border))

        # Component name (centered)
        title = f"{component.name} ({component.unit})"
        title_padded = title.center(card_width - 2)
        with self.term.location(x_offset, y_pos + 1):
            print(border_color("║") + text_color(title_padded) + border_color("║"))

        # Divider
        divider = "╟" + "─" * (card_width - 2) + "╢"
        with self.term.location(x_offset, y_pos + 2):
            print(border_color(divider))

        # Latest values (if any)
        current_y = y_pos + 3
        if latest_entries:
            for i, entry in enumerate(latest_entries):
                value_line = f"  {entry.date}  →  {entry.value:.2f} {component.unit}"

                # Check if value is out of range
                out_of_range = False
                if component.normal_min and entry.value < component.normal_min:
                    out_of_range = True
                if component.normal_max and entry.value > component.normal_max:
                    out_of_range = True

                # Color the value based on range
                if out_of_range and not dimmed:
                    display_color = lambda s: self.term.bold(self.term.yellow(s))
                else:
                    display_color = value_color

                padded = value_line.ljust(card_width - 2)
                with self.term.location(x_offset, current_y + i):
                    print(border_color("║") + display_color(padded) + border_color("║"))
            current_y += 3
        else:
            no_data = "  No data yet".ljust(card_width - 2)
            with self.term.location(x_offset, current_y):
                print(border_color("║") + text_color(no_data) + border_color("║"))
            current_y += 1

        # Graph divider
        with self.term.location(x_offset, current_y):
            print(border_color(divider))
        current_y += 1

        # Render graph if we have data and this is not dimmed
        graph_height = int(10 * scale)
        if all_entries and len(all_entries) >= 2 and not dimmed:
            try:
                graph_lines = self._render_graph(component, all_entries, card_width - 4, graph_height)
                for i, line in enumerate(graph_lines):
                    if current_y + i < y_pos + card_height - 1:
                        padded = line.ljust(card_width - 2)
                        with self.term.location(x_offset, current_y + i):
                            print(border_color("║") + padded + border_color("║"))
                current_y += len(graph_lines)
            except Exception as e:
                # Graph rendering failed, show error instead of crashing
                error_msg = f"  Graph error: {str(e)[:40]}".ljust(card_width - 2)
                with self.term.location(x_offset, current_y):
                    print(border_color("║") + self.term.yellow(error_msg) + border_color("║"))
                current_y += 1
        else:
            # No graph, just empty space
            msg = "  (need 2+ entries for graph)".ljust(card_width - 2) if not dimmed else " " * (card_width - 2)
            with self.term.location(x_offset, current_y):
                print(border_color("║") + text_color(msg) + border_color("║"))
            current_y += 1

        # Fill remaining space
        while current_y < y_pos + card_height - 1:
            empty_line = " " * (card_width - 2)
            with self.term.location(x_offset, current_y):
                print(border_color("║") + empty_line + border_color("║"))
            current_y += 1

        # Bottom border
        bottom_border = "╚" + "═" * (card_width - 2) + "╝"
        with self.term.location(x_offset, y_pos + card_height - 1):
            print(border_color(bottom_border))

    def _render_graph(self, component: Component, entries: List[Entry], width: int, height: int) -> List[str]:
        """Render a graph using plotext, returns list of strings"""
        # Sort entries by date (oldest first for graph)
        sorted_entries = sorted(entries, key=lambda e: e.date)

        # Extract dates and values
        dates = [e.date for e in sorted_entries]
        values = [e.value for e in sorted_entries]

        # Configure plotext for terminal output
        plt.clf()
        plt.plotsize(width, height)
        plt.theme('dark')

        # Set date format to ISO (YYYY-MM-DD) - critical!
        plt.date_form('Y-m-d')

        # Plot the data with red color
        plt.plot(dates, values, marker="●", color="red")

        # Add normal range lines if defined (yellow for visibility)
        if component.normal_min:
            plt.hline(component.normal_min, "yellow")
        if component.normal_max:
            plt.hline(component.normal_max, "yellow")

        # Styling
        plt.xlabel("Date")
        plt.ylabel(component.unit)
        plt.title("")  # No title, we have it in the card header

        # Build the plot and get output
        plot_str = plt.build()

        # Split into lines - plotext already has colors baked in
        lines = plot_str.split('\n')

        return lines

    def _render_empty_state(self):
        """Render when no components exist"""
        msg = "No components found. Press 'c' to create one."
        x = (self.term.width - len(msg)) // 2
        y = self.term.height // 2

        with self.term.location(x, y):
            print(self.term.yellow(msg))

    def _handle_input(self, key):
        """Handle keyboard input"""
        if key.lower() == 'q':
            self.running = False
        elif key.name == 'KEY_DOWN' or key.lower() == 'j':
            if self.components:
                self.current_index = (self.current_index + 1) % len(self.components)
        elif key.name == 'KEY_UP' or key.lower() == 'k':
            if self.components:
                self.current_index = (self.current_index - 1) % len(self.components)
        elif key.lower() == 'n':
            if self.components:
                self._show_add_entry_modal()
        elif key.lower() == 'e':
            if self.components:
                self._show_edit_entry_modal()
        elif key.lower() == 'd':
            if self.components:
                self._show_delete_entry_modal()
        elif key.lower() == 'c':
            self._show_create_component_modal()

    def _show_add_entry_modal(self):
        """Show modal to add a new entry for the current component"""
        component = self.components[self.current_index]

        # Draw modal box
        modal_width = 60
        modal_height = 12
        x = (self.term.width - modal_width) // 2
        y = (self.term.height - modal_height) // 2

        # Get input for value
        print(self.term.clear())
        self._draw_modal_box(x, y, modal_width, modal_height, f"New Entry: {component.name}")

        # Value input
        with self.term.location(x + 2, y + 3):
            print(self.term.red(f"Value ({component.unit}):"))

        value_str = self._get_input(x + 2, y + 4, 20)
        if not value_str:
            return

        try:
            value = float(value_str)
        except ValueError:
            self._show_message("Invalid value. Press any key to continue.")
            return

        # Date input (default to today)
        with self.term.location(x + 2, y + 6):
            print(self.term.red("Date (YYYY-MM-DD) [Enter=today]:"))

        date_str = self._get_input(x + 2, y + 7, 20)
        if not date_str:
            date_str = date.today().isoformat()
        else:
            # Validate date format
            try:
                datetime.strptime(date_str, '%Y-%m-%d')
            except ValueError:
                self._show_message(f"Invalid date format. Use YYYY-MM-DD. Press any key.")
                return

        # Notes input
        with self.term.location(x + 2, y + 9):
            print(self.term.red("Notes (optional):"))

        notes = self._get_input(x + 2, y + 10, 40)

        # Save entry
        entry = Entry(
            id=None,
            component_id=component.id,
            value=value,
            date=date_str,
            notes=notes or ""
        )
        self.db.add_entry(entry)

        self._show_message("Entry added! Press any key to continue.")

    def _show_create_component_modal(self):
        """Show modal to create a new component"""
        # Draw modal box
        modal_width = 70
        modal_height = 18
        x = (self.term.width - modal_width) // 2
        y = (self.term.height - modal_height) // 2

        print(self.term.clear())
        self._draw_modal_box(x, y, modal_width, modal_height, "Create New Component")

        # Name input
        with self.term.location(x + 2, y + 3):
            print(self.term.red("Component name (e.g., HbA1c):"))

        name = self._get_input(x + 2, y + 4, 40)
        if not name:
            return

        # Unit input
        with self.term.location(x + 2, y + 6):
            print(self.term.red("Unit (e.g., mmol/mol):"))

        unit = self._get_input(x + 2, y + 7, 20)
        if not unit:
            return

        # Normal range min
        with self.term.location(x + 2, y + 9):
            print(self.term.red("Normal range minimum (optional):"))

        min_str = self._get_input(x + 2, y + 10, 15)
        normal_min = float(min_str) if min_str else None

        # Normal range max
        with self.term.location(x + 2, y + 12):
            print(self.term.red("Normal range maximum (optional):"))

        max_str = self._get_input(x + 2, y + 13, 15)
        normal_max = float(max_str) if max_str else None

        # Create component
        component = Component(
            id=None,
            name=name,
            unit=unit,
            normal_min=normal_min,
            normal_max=normal_max
        )
        new_id = self.db.create_component(component)

        # Reload components and select the new one
        self.components = self.db.get_all_components()
        for i, comp in enumerate(self.components):
            if comp.id == new_id:
                self.current_index = i
                break

        self._show_message("Component created! Press any key to continue.")

    def _show_edit_entry_modal(self):
        """Show modal to select and edit an entry"""
        component = self.components[self.current_index]
        entries = self.db.get_entries_for_component(component.id, limit=10)

        if not entries:
            self._show_message("No entries to edit. Press any key.")
            return

        # Show entry selection modal
        modal_width = 80
        modal_height = min(15, len(entries) + 5)
        x = (self.term.width - modal_width) // 2
        y = (self.term.height - modal_height) // 2

        selected = 0

        while True:
            print(self.term.clear())
            self._draw_modal_box(x, y, modal_width, modal_height, f"Edit Entry: {component.name}")

            # Draw entries list
            for i, entry in enumerate(entries[:10]):
                entry_line = f"{entry.date}  {entry.value:.2f} {component.unit}"
                if entry.notes:
                    entry_line += f"  ({entry.notes[:30]})"

                if i == selected:
                    display = f"→ {entry_line}".ljust(modal_width - 4)
                    with self.term.location(x + 2, y + 3 + i):
                        print(self.term.bold(self.term.yellow(display)))
                else:
                    display = f"  {entry_line}".ljust(modal_width - 4)
                    with self.term.location(x + 2, y + 3 + i):
                        print(self.term.red(display))

            # Instructions
            with self.term.location(x + 2, y + modal_height - 2):
                print(self.term.yellow("↑/↓: select  Enter: edit  Esc: cancel"))

            # Get input
            key = self.term.inkey()
            if key.name == 'KEY_UP':
                selected = (selected - 1) % len(entries)
            elif key.name == 'KEY_DOWN':
                selected = (selected + 1) % len(entries)
            elif key.name == 'KEY_ENTER':
                # Edit the selected entry
                self._edit_entry(entries[selected], component)
                return
            elif key.name == 'KEY_ESCAPE':
                return

    def _edit_entry(self, entry: Entry, component: Component):
        """Edit a specific entry"""
        modal_width = 60
        modal_height = 12
        x = (self.term.width - modal_width) // 2
        y = (self.term.height - modal_height) // 2

        print(self.term.clear())
        self._draw_modal_box(x, y, modal_width, modal_height, f"Edit: {component.name}")

        # Value input (pre-filled)
        with self.term.location(x + 2, y + 3):
            print(self.term.red(f"Value ({component.unit}):"))

        value_str = self._get_input_prefilled(x + 2, y + 4, 20, str(entry.value))
        if not value_str:
            return

        try:
            value = float(value_str)
        except ValueError:
            self._show_message("Invalid value. Press any key.")
            return

        # Date input (pre-filled)
        with self.term.location(x + 2, y + 6):
            print(self.term.red("Date (YYYY-MM-DD):"))

        date_str = self._get_input_prefilled(x + 2, y + 7, 20, entry.date)
        if not date_str:
            return

        # Validate date
        try:
            datetime.strptime(date_str, '%Y-%m-%d')
        except ValueError:
            self._show_message("Invalid date format. Use YYYY-MM-DD. Press any key.")
            return

        # Notes input (pre-filled)
        with self.term.location(x + 2, y + 9):
            print(self.term.red("Notes (optional):"))

        notes = self._get_input_prefilled(x + 2, y + 10, 40, entry.notes)

        # Update entry
        updated = Entry(
            id=entry.id,
            component_id=entry.component_id,
            value=value,
            date=date_str,
            notes=notes or ""
        )
        self.db.update_entry(updated)

        self._show_message("Entry updated! Press any key.")

    def _show_delete_entry_modal(self):
        """Show modal to select and delete an entry"""
        component = self.components[self.current_index]
        entries = self.db.get_entries_for_component(component.id, limit=10)

        if not entries:
            self._show_message("No entries to delete. Press any key.")
            return

        # Show entry selection modal
        modal_width = 80
        modal_height = min(15, len(entries) + 5)
        x = (self.term.width - modal_width) // 2
        y = (self.term.height - modal_height) // 2

        selected = 0

        while True:
            print(self.term.clear())
            self._draw_modal_box(x, y, modal_width, modal_height, f"Delete Entry: {component.name}")

            # Draw entries list
            for i, entry in enumerate(entries[:10]):
                entry_line = f"{entry.date}  {entry.value:.2f} {component.unit}"
                if entry.notes:
                    entry_line += f"  ({entry.notes[:30]})"

                if i == selected:
                    display = f"→ {entry_line}".ljust(modal_width - 4)
                    with self.term.location(x + 2, y + 3 + i):
                        print(self.term.bold(self.term.yellow(display)))
                else:
                    display = f"  {entry_line}".ljust(modal_width - 4)
                    with self.term.location(x + 2, y + 3 + i):
                        print(self.term.red(display))

            # Instructions
            with self.term.location(x + 2, y + modal_height - 2):
                print(self.term.yellow("↑/↓: select  Enter: delete  Esc: cancel"))

            # Get input
            key = self.term.inkey()
            if key.name == 'KEY_UP':
                selected = (selected - 1) % len(entries)
            elif key.name == 'KEY_DOWN':
                selected = (selected + 1) % len(entries)
            elif key.name == 'KEY_ENTER':
                # Confirm deletion
                self.db.delete_entry(entries[selected].id)
                self._show_message("Entry deleted! Press any key.")
                return
            elif key.name == 'KEY_ESCAPE':
                return

    def _draw_modal_box(self, x: int, y: int, width: int, height: int, title: str):
        """Draw a modal box with a title"""
        # Top border
        top = "╔" + "═" * (width - 2) + "╗"
        with self.term.location(x, y):
            print(self.term.bold(self.term.color_rgb(255, 0, 0)(top)))

        # Title
        title_padded = f" {title} ".center(width - 2)
        with self.term.location(x, y + 1):
            print(self.term.bold(self.term.color_rgb(255, 0, 0)("║")) +
                  self.term.bold(self.term.color_rgb(255, 215, 0)(title_padded)) +
                  self.term.bold(self.term.color_rgb(255, 0, 0)("║")))

        # Divider
        divider = "╟" + "─" * (width - 2) + "╢"
        with self.term.location(x, y + 2):
            print(self.term.bold(self.term.color_rgb(255, 0, 0)(divider)))

        # Empty content area
        for i in range(3, height - 1):
            empty = "║" + " " * (width - 2) + "║"
            with self.term.location(x, y + i):
                print(self.term.bold(self.term.color_rgb(255, 0, 0)(empty)))

        # Bottom border
        bottom = "╚" + "═" * (width - 2) + "╝"
        with self.term.location(x, y + height - 1):
            print(self.term.bold(self.term.color_rgb(255, 0, 0)(bottom)))

        # Ensure everything is flushed before taking input
        sys.stdout.flush()

    def _get_input(self, x: int, y: int, max_length: int) -> str:
        """Get text input from user at specific location"""
        input_str = ""
        cursor_pos = 0

        # Draw input box background
        with self.term.location(x, y):
            print(self.term.on_color_rgb(50, 0, 0)(" " * max_length))
        sys.stdout.flush()

        while True:
            # Display current input
            display = input_str.ljust(max_length)
            with self.term.location(x, y):
                print(self.term.yellow(self.term.on_color_rgb(50, 0, 0)(display)))

            # Show cursor
            with self.term.location(x + cursor_pos, y):
                print(self.term.reverse(display[cursor_pos]))

            key = self.term.inkey()

            if key.name == 'KEY_ENTER':
                break
            elif key.name == 'KEY_ESCAPE':
                return ""
            elif key.name == 'KEY_BACKSPACE' or key.name == 'KEY_DELETE':
                if cursor_pos > 0:
                    input_str = input_str[:cursor_pos - 1] + input_str[cursor_pos:]
                    cursor_pos -= 1
            elif key.name == 'KEY_LEFT':
                cursor_pos = max(0, cursor_pos - 1)
            elif key.name == 'KEY_RIGHT':
                cursor_pos = min(len(input_str), cursor_pos + 1)
            elif key.is_sequence:
                continue
            elif len(input_str) < max_length and key.isprintable():
                input_str = input_str[:cursor_pos] + key + input_str[cursor_pos:]
                cursor_pos += 1

        return input_str.strip()

    def _get_input_prefilled(self, x: int, y: int, max_length: int, initial: str) -> str:
        """Get text input with pre-filled value"""
        input_str = initial
        cursor_pos = len(input_str)

        # Draw input box background
        with self.term.location(x, y):
            print(self.term.on_color_rgb(50, 0, 0)(" " * max_length))
        sys.stdout.flush()

        while True:
            # Display current input
            display = input_str.ljust(max_length)
            with self.term.location(x, y):
                print(self.term.yellow(self.term.on_color_rgb(50, 0, 0)(display)))

            # Show cursor
            with self.term.location(x + cursor_pos, y):
                print(self.term.reverse(display[cursor_pos]))

            key = self.term.inkey()

            if key.name == 'KEY_ENTER':
                break
            elif key.name == 'KEY_ESCAPE':
                return ""
            elif key.name == 'KEY_BACKSPACE' or key.name == 'KEY_DELETE':
                if cursor_pos > 0:
                    input_str = input_str[:cursor_pos - 1] + input_str[cursor_pos:]
                    cursor_pos -= 1
            elif key.name == 'KEY_LEFT':
                cursor_pos = max(0, cursor_pos - 1)
            elif key.name == 'KEY_RIGHT':
                cursor_pos = min(len(input_str), cursor_pos + 1)
            elif key.is_sequence:
                continue
            elif len(input_str) < max_length and key.isprintable():
                input_str = input_str[:cursor_pos] + key + input_str[cursor_pos:]
                cursor_pos += 1

        return input_str.strip()

    def _show_message(self, message: str):
        """Show a message and wait for keypress"""
        msg_width = len(message) + 4
        x = (self.term.width - msg_width) // 2
        y = self.term.height // 2

        with self.term.location(x, y):
            print(self.term.bold(self.term.yellow(message)))

        with self.term.cbreak():
            self.term.inkey()


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Main entry point"""
    db = Database()
    try:
        ui = BloodPanelUI(db)
        ui.run()
    finally:
        db.close()


if __name__ == "__main__":
    main()
