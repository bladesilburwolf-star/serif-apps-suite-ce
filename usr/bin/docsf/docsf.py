#!/usr/bin/env python3
import sys
import os
from PyQt5.QtCore import Qt, QRect
from PyQt5.QtGui import QFont, QColor, QPainter, QPen, QTextFormat, QTextCharFormat, QSyntaxHighlighter
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QFrame, 
                             QTextEdit, QFileDialog, QLineEdit, QShortcut)

# Retro CRT Theme Palettes (matching your exact HTML color space)
THEMES = {
    "GREEN": {
        "primary": "#00ff80", "primary_rgb": (0, 255, 128),
        "bg": "#000a05", "bg_rgb": (0, 10, 5),
        "panel_bg": "#002211", "sidebar_bg": "#001a0f",
        "dim": "#007339"
    },
    "AMBER": {
        "primary": "#ffb000", "primary_rgb": (255, 176, 0),
        "bg": "#0c0600", "bg_rgb": (12, 6, 0),
        "panel_bg": "#2b1400", "sidebar_bg": "#1f0f00",
        "dim": "#996a00"
    },
    "CYAN": {
        "primary": "#00dcff", "primary_rgb": (0, 220, 255),
        "bg": "#00080a", "bg_rgb": (0, 8, 10),
        "panel_bg": "#002b33", "sidebar_bg": "#001f24",
        "dim": "#008399"
    },
    "MONO": {
        "primary": "#dcdcdc", "primary_rgb": (220, 220, 220),
        "bg": "#050505", "bg_rgb": (5, 5, 5),
        "panel_bg": "#222222", "sidebar_bg": "#191919",
        "dim": "#808080"
    }
}
THEME_ORDER = ["GREEN", "AMBER", "CYAN", "MONO"]


class RetroHighlighter(QSyntaxHighlighter):
    """High-speed real-time syntax highlighting for line numbers and search terms."""
    def __init__(self, document):
        super().__init__(document)
        self.search_term = ""
        self.line_numbers_enabled = True
        self.dim_color = QColor(0, 115, 57)
        self.primary_color = QColor(0, 255, 128)

    def set_rules(self, search_term, line_numbers, dim_hex, prim_hex):
        self.search_term = search_term.lower()
        self.line_numbers_enabled = line_numbers
        self.dim_color = QColor(dim_hex)
        self.primary_color = QColor(prim_hex)
        self.rehighlight()

    def highlightBlock(self, text):
        # 1. Format line numbers if they exist at the start of the line
        if self.line_numbers_enabled and text:
            # We match the prefix format "0001  "
            if len(text) >= 6 and text[:4].isdigit() and text[4:6] == "  ":
                num_format = QTextCharFormat()
                num_format.setForeground(self.dim_color)
                self.setFormat(0, 4, num_format)
                
                # Keep rest of the line themed properly
                rest_format = QTextCharFormat()
                rest_format.setForeground(self.primary_color)
                self.setFormat(4, len(text) - 4, rest_format)

        # 2. Format search matches
        if self.search_term and len(self.search_term) > 0:
            search_len = len(self.search_term)
            idx = text.lower().find(self.search_term)
            while idx >= 0:
                # Invert search highlights
                match_format = QTextCharFormat()
                match_format.setBackground(self.dim_color)
                match_format.setForeground(QColor("#ffffff"))
                self.setFormat(idx, search_len, match_format)
                idx = text.lower().find(self.search_term, idx + search_len)


class CRTTextEdit(QTextEdit):
    """Customized text edit to render optional scanline overlays in real-time."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scanlines_enabled = False

    def set_scanlines(self, enabled):
        self.scanlines_enabled = enabled
        self.viewport().update()

    def paintEvent(self, event):
        super().paintEvent(event)
        
        # Draw physical scanlines over the screen viewport
        if self.scanlines_enabled:
            painter = QPainter(self.viewport())
            painter.setRenderHint(QPainter.Antialiasing, False)
            scanline_color = QColor(0, 0, 0, 60)
            pen = QPen(scanline_color, 1)
            painter.setPen(pen)
            
            for y in range(0, self.viewport().height(), 4):
                painter.drawLine(0, y, self.viewport().width(), y)


class GloriaTextViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GLORIA RETRO CAD - TXT VIEWER")
        self.setMinimumSize(980, 640)
        self.resize(1024, 680)

        self.raw_text = ""
        self.theme_index = 0
        self.wrap_on = False
        self.line_numbers_on = True
        self.scanlines_on = False

        self.init_ui()
        self.highlighter = RetroHighlighter(self.text_edit.document())
        self.apply_theme("GREEN")
        self.setup_shortcuts()

    def init_ui(self):
        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(6)

        # 1. TOP BAR
        self.top_bar = QFrame(self)
        self.top_bar.setFixedHeight(40)
        top_layout = QHBoxLayout(self.top_bar)
        top_layout.setContentsMargins(10, 0, 10, 0)

        self.btn_f1 = QPushButton("F1 LOAD TXT", self.top_bar)
        self.btn_f2 = QPushButton("F2 RESET VIEW", self.top_bar)
        self.btn_f3 = QPushButton("F3 WRAP ON/OFF", self.top_bar)
        self.btn_f4 = QPushButton("F4 FIND IN TEXT", self.top_bar)
        self.btn_f5 = QPushButton("F5 SCANLINES", self.top_bar)

        for btn in [self.btn_f1, self.btn_f2, self.btn_f3, self.btn_f4, self.btn_f5]:
            btn.setFlat(True)
            btn.setCursor(Qt.PointingHandCursor)

        self.btn_f1.clicked.connect(self.action_load_file)
        self.btn_f2.clicked.connect(self.action_reset_view)
        self.btn_f3.clicked.connect(self.action_toggle_wrap)
        self.btn_f4.clicked.connect(self.action_toggle_search)
        self.btn_f5.clicked.connect(self.action_toggle_scanlines)

        top_layout.addWidget(self.btn_f1)
        top_layout.addWidget(QLabel("|", self.top_bar))
        top_layout.addWidget(self.btn_f2)
        top_layout.addWidget(QLabel("|", self.top_bar))
        top_layout.addWidget(self.btn_f3)
        top_layout.addWidget(QLabel("|", self.top_bar))
        top_layout.addWidget(self.btn_f4)
        top_layout.addWidget(QLabel("|", self.top_bar))
        top_layout.addWidget(self.btn_f5)
        top_layout.addStretch()

        # 2. MIDDLE VIEW
        self.middle_frame = QFrame(self)
        middle_layout = QHBoxLayout(self.middle_frame)
        middle_layout.setContentsMargins(0, 0, 0, 0)
        middle_layout.setSpacing(6)

        # Sidebar
        self.sidebar = QFrame(self.middle_frame)
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(240)
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(15, 15, 15, 15)
        sidebar_layout.setSpacing(10)

        self.lbl_file_header = QLabel("FILE NAME:", self.sidebar)
        self.lbl_file_name = QLabel("NO_FILE_LOADED", self.sidebar)
        self.lbl_file_name.setWordWrap(True)

        self.lbl_analytics_header = QLabel("DATA ANALYTICS:", self.sidebar)
        self.lbl_stat_lines = QLabel("Lines: 0", self.sidebar)
        self.lbl_stat_words = QLabel("Words: 0", self.sidebar)
        self.lbl_stat_chars = QLabel("Chars: 0", self.sidebar)
        self.lbl_stat_size = QLabel("Size: 0 B", self.sidebar)

        self.btn_sidebar_wrap = QPushButton("WORD WRAP: OFF", self.sidebar)
        self.btn_sidebar_wrap.clicked.connect(self.action_toggle_wrap)
        
        self.btn_sidebar_lines = QPushButton("LINE NUMBERS: ON", self.sidebar)
        self.btn_sidebar_lines.clicked.connect(self.action_toggle_line_numbers)

        sidebar_layout.addWidget(self.lbl_file_header)
        sidebar_layout.addWidget(self.lbl_file_name)
        sidebar_layout.addWidget(QFrame(self.sidebar))
        sidebar_layout.addWidget(self.lbl_analytics_header)
        sidebar_layout.addWidget(self.lbl_stat_lines)
        sidebar_layout.addWidget(self.lbl_stat_words)
        sidebar_layout.addWidget(self.lbl_stat_chars)
        sidebar_layout.addWidget(self.lbl_stat_size)
        sidebar_layout.addStretch()
        sidebar_layout.addWidget(self.btn_sidebar_wrap)
        sidebar_layout.addWidget(self.btn_sidebar_lines)

        # Right Text Panel
        self.right_container = QFrame(self.middle_frame)
        right_container_layout = QVBoxLayout(self.right_container)
        right_container_layout.setContentsMargins(0, 0, 0, 0)
        right_container_layout.setSpacing(0)

        # Search / Find Bar
        self.search_bar = QFrame(self.right_container)
        self.search_bar.setObjectName("search_bar")
        self.search_bar.setFixedHeight(38)
        self.search_bar.hide()
        search_layout = QHBoxLayout(self.search_bar)
        search_layout.setContentsMargins(10, 0, 10, 0)

        self.search_input = QLineEdit(self.search_bar)
        self.search_input.setPlaceholderText("SEARCH...")
        self.search_input.textChanged.connect(self.perform_search)
        self.search_input.returnPressed.connect(self.find_next)

        self.lbl_search_count = QLabel("0 / 0", self.search_bar)
        self.lbl_search_hint = QLabel("ENTER: NEXT | SHIFT+ENTER: PREV | ESC: CLOSE", self.search_bar)

        search_layout.addWidget(self.search_input, 1)
        search_layout.addWidget(self.lbl_search_count)
        search_layout.addWidget(self.lbl_search_hint)

        # Text Area
        self.text_edit = CRTTextEdit(self.right_container)
        self.text_edit.setReadOnly(True)
        self.text_edit.setLineWrapMode(QTextEdit.NoWrap)
        self.text_edit.setPlainText("[ NO SOURCE - PRESS F1 TO LOAD A TEXT FILE ]")

        right_container_layout.addWidget(self.search_bar)
        right_container_layout.addWidget(self.text_edit)

        middle_layout.addWidget(self.sidebar)
        middle_layout.addWidget(self.right_container, 1)

        # 3. BOTTOM BAR
        self.bottom_bar = QFrame(self)
        self.bottom_bar.setFixedHeight(65)
        bottom_layout = QHBoxLayout(self.bottom_bar)
        bottom_layout.setContentsMargins(15, 10, 15, 10)

        status_text_layout = QVBoxLayout()
        self.lbl_status = QLabel("SYSTEM_STATUS: AWAITING FILE INPUT...", self.bottom_bar)
        self.lbl_status_hints = QLabel("F4 TO FIND IN TEXT | F3 FOR WRAP / LINE NUMBER TOGGLES", self.bottom_bar)
        status_text_layout.addWidget(self.lbl_status)
        status_text_layout.addWidget(self.lbl_status_hints)

        self.btn_theme = QPushButton("THEME: GREEN", self.bottom_bar)
        self.btn_theme.clicked.connect(self.action_cycle_theme)
        self.btn_theme.setCursor(Qt.PointingHandCursor)

        bottom_layout.addLayout(status_text_layout, 1)
        bottom_layout.addWidget(self.btn_theme)

        self.main_layout.addWidget(self.top_bar)
        self.main_layout.addWidget(self.middle_frame, 1)
        self.main_layout.addWidget(self.bottom_bar)

    def setup_shortcuts(self):
        QShortcut(Qt.Key_F1, self, self.action_load_file)
        QShortcut(Qt.Key_F2, self, self.action_reset_view)
        QShortcut(Qt.Key_F3, self, self.action_toggle_wrap)
        QShortcut(Qt.Key_F4, self, self.action_toggle_search)
        QShortcut(Qt.Key_F5, self, self.action_toggle_scanlines)
        QShortcut(Qt.Key_Escape, self, self.action_close_search)

        # Shift+Enter search key overrides
        QShortcut(Qt.Key_Return, self.search_input, self.find_next)
        QShortcut(Qt.Key_Enter, self.search_input, self.find_next)
        
        shift_return = QShortcut(Qt.Key_Shift + Qt.Key_Return, self.search_input)
        shift_return.activated.connect(self.find_prev)
        shift_enter = QShortcut(Qt.Key_Shift + Qt.Key_Enter, self.search_input)
        shift_enter.activated.connect(self.find_prev)

    def apply_theme(self, name):
        t = THEMES[name]
        self.theme_name = name

        p = t["primary"]
        bg = t["bg"]
        p_bg = t["panel_bg"]
        s_bg = t["sidebar_bg"]

        self.setStyleSheet(f"""
            QMainWindow {{ background-color: #000000; }}
            QLabel {{
                color: {p};
                font-family: 'Courier New', monospace;
                font-weight: bold;
                font-size: 11px;
            }}
            QFrame {{
                background-color: {p_bg};
                border: 2px solid {p};
                font-family: 'Courier New', monospace;
            }}
            QFrame#sidebar {{
                background-color: {s_bg};
                border: 2px solid {p};
            }}
            QPushButton {{
                background-color: {bg};
                color: {p};
                border: 2px solid {p};
                font-family: 'Courier New', monospace;
                font-weight: bold;
                font-size: 11px;
                padding: 5px 12px;
            }}
            QPushButton:hover {{
                background-color: {p};
                color: #000000;
            }}
            QTextEdit {{
                background-color: {bg};
                color: {p};
                border: 2px solid {p};
                font-family: 'Courier New', monospace;
                font-size: 13px;
            }}
            QFrame#search_bar {{
                background-color: {p_bg};
                border: 2px solid {p};
                border-bottom: none;
            }}
            QLineEdit {{
                background-color: #000000;
                color: {p};
                border: 1px solid {p};
                font-family: 'Courier New', monospace;
                padding: 4px;
            }}
        """)

        self.btn_theme.setText(f"THEME: {name}")
        self.set_status_message(f"Palette Switched: {name}")
        
        # Apply the palette change directly to the Syntax Highlighter rules
        self.highlighter.set_rules(
            self.search_input.text(),
            self.line_numbers_on,
            t["dim"],
            t["primary"]
        )

    def set_status_message(self, message):
        self.lbl_status.setText(f"SYSTEM_STATUS: {message.upper()}")

    # --- File Loading and Parsing ---

    def action_load_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Text File", "", "Text Files (*.txt *.md *.log *.csv *.ini *.cfg);;All Files (*)"
        )
        if not file_path:
            return

        self.set_status_message(f"Reading File: {os.path.basename(file_path)}")

        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                self.raw_text = f.read()

            self.lbl_file_name.setText(os.path.basename(file_path).upper())
            self.render_text_to_widget()
            self.calculate_statistics(file_path)
            self.set_status_message(f"File Loaded: {os.path.basename(file_path)}")

        except Exception as e:
            self.set_status_message(f"Error Loading File: {str(e)}")

    def render_text_to_widget(self):
        """Build plain text line-by-line so SyntaxHighlighter formats it beautifully."""
        if not self.raw_text:
            return

        lines = self.raw_text.splitlines()
        processed_lines = []

        for idx, line in enumerate(lines):
            if self.line_numbers_on:
                line_num_str = f"{idx + 1:04d}  "
                processed_lines.append(f"{line_num_str}{line}")
            else:
                processed_lines.append(line)

        # We use setPlainText (NO raw HTML strings) to prevent tag leak bugs!
        self.text_edit.setPlainText("\n".join(processed_lines))
        
        # Update our highlighter rules
        t = THEMES[self.theme_name]
        self.highlighter.set_rules(
            self.search_input.text(),
            self.line_numbers_on,
            t["dim"],
            t["primary"]
        )

    def action_reset_view(self):
        self.text_edit.verticalScrollBar().setValue(0)
        self.action_close_search()
        self.set_status_message("View reset to top")

    def action_toggle_wrap(self):
        self.wrap_on = not self.wrap_on
        if self.wrap_on:
            self.text_edit.setLineWrapMode(QTextEdit.WidgetWidth)
            self.btn_sidebar_wrap.setText("WORD WRAP: ON")
        else:
            self.text_edit.setLineWrapMode(QTextEdit.NoWrap)
            self.btn_sidebar_wrap.setText("WORD WRAP: OFF")
        self.set_status_message(f"Word wrap: {'ON' if self.wrap_on else 'OFF'}")

    def action_toggle_line_numbers(self):
        self.line_numbers_on = not self.line_numbers_on
        self.btn_sidebar_lines.setText(f"LINE NUMBERS: {'ON' if self.line_numbers_on else 'OFF'}")
        if self.raw_text:
            self.render_text_to_widget()
        self.set_status_message(f"Line numbers: {'ON' if self.line_numbers_on else 'OFF'}")

    def action_toggle_scanlines(self):
        self.scanlines_on = not self.scanlines_on
        self.text_edit.set_scanlines(self.scanlines_on)
        self.set_status_message(f"Scanline overlay: {'ON' if self.scanlines_on else 'OFF'}")

    def action_cycle_theme(self):
        self.theme_index = (self.theme_index + 1) % len(THEME_ORDER)
        self.apply_theme(THEME_ORDER[self.theme_index])

    def action_toggle_search(self):
        if not self.raw_text:
            self.set_status_message("No file loaded - nothing to search")
            return

        if self.search_bar.isVisible():
            self.action_close_search()
        else:
            self.search_bar.show()
            self.search_input.setFocus()
            self.set_status_message("Find mode active")

    def action_close_search(self):
        self.search_bar.hide()
        self.search_input.clear()
        self.lbl_search_count.setText("0 / 0")
        if self.raw_text:
            self.render_text_to_widget()

    # --- High-Performance Text Search and Scroll Navigation ---

    def perform_search(self):
        text = self.search_input.text()
        t = THEMES[self.theme_name]
        
        # Trigger highlighter to draw background overlays over matched words
        self.highlighter.set_rules(text, self.line_numbers_on, t["dim"], t["primary"])
        
        if not text:
            self.lbl_search_count.setText("0 / 0")
            return

        # Use Qt's native finding logic to count matched indexes
        matches = []
        cursor = self.text_edit.document().find(text)
        while not cursor.isNull():
            matches.append(cursor.position())
            cursor = self.text_edit.document().find(text, cursor)

        total = len(matches)
        current = 1 if total > 0 else 0
        self.lbl_search_count.setText(f"{current} / {total}")
        
        if total > 0:
            # Scroll directly to first found occurrence
            self.text_edit.moveCursor(self.text_edit.textCursor().Start)
            self.text_edit.find(text)

    def find_next(self):
        text = self.search_input.text()
        if not text:
            return
        
        # Move scroll viewport to next found pattern
        found = self.text_edit.find(text)
        if not found:
            # Wrap around back to top of the document
            self.text_edit.moveCursor(self.text_edit.textCursor().Start)
            self.text_edit.find(text)
        self.update_search_match_index()

    def find_prev(self):
        text = self.search_input.text()
        if not text:
            return
            
        # Move scroll viewport backwards
        found = self.text_edit.find(text, QTextDocument.FindBackward) if 'QTextDocument' in globals() else self.text_edit.find(text, self.text_edit.document().FindBackward)
        if not found:
            # Wrap around back to bottom of the document
            self.text_edit.moveCursor(self.text_edit.textCursor().End)
            self.text_edit.find(text, 1) # 1 is the binary flag value for FindBackward in PyQt
        self.update_search_match_index()

    def update_search_match_index(self):
        """Determine what match index the active cursor selection is currently at."""
        text = self.search_input.text()
        if not text:
            return

        current_cursor_pos = self.text_edit.textCursor().position()
        
        # Loop document to calculate index
        matches = []
        cursor = self.text_edit.document().find(text)
        current_idx = 0
        
        while not cursor.isNull():
            matches.append(cursor.position())
            if cursor.position() <= current_cursor_pos:
                current_idx = len(matches)
            cursor = self.text_edit.document().find(text, cursor)
            
        total = len(matches)
        self.lbl_search_count.setText(f"{current_idx if total > 0 else 0} / {total}")

    def calculate_statistics(self, path):
        lines = len(self.raw_text.splitlines())
        words = len(self.raw_text.split()) if self.raw_text.strip() else 0
        chars = len(self.raw_text)

        byte_size = os.path.getsize(path)
        if byte_size < 1024:
            size_str = f"{byte_size} B"
        elif byte_size < 1024 * 1024:
            size_str = f"{byte_size / 1024:.1f} KB"
        else:
            size_str = f"{byte_size / (1024 * 1024):.2f} MB"

        self.lbl_stat_lines.setText(f"Lines: {lines}")
        self.lbl_stat_words.setText(f"Words: {words}")
        self.lbl_stat_chars.setText(f"Chars: {chars}")
        self.lbl_stat_size.setText(f"Size: {size_str}")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    viewer = GloriaTextViewer()
    viewer.show()
    sys.exit(app.exec_())
