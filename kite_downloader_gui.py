#!/usr/bin/env python3

import sys
import os
import re
import time
import json
import threading
import traceback
from io import StringIO
from datetime import datetime, timedelta
from pathlib import Path

import requests
import pandas as pd
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QLabel, QLineEdit, QTextEdit, QPlainTextEdit,
    QPushButton, QComboBox, QDateEdit, QFileDialog, QFrame,
    QScrollArea, QSizePolicy, QProgressBar, QSpacerItem,
    QCheckBox, QToolButton, QMessageBox, QSplitter, QGroupBox,
    QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QStatusBar
)
from PyQt5.QtCore import (
    Qt, QThread, pyqtSignal, QDate, QTimer, QSize, QRect, QPropertyAnimation,
    QEasingCurve, QObject
)
from PyQt5.QtGui import (
    QFont, QFontDatabase, QColor, QPalette, QTextCursor,
    QIcon, QPixmap, QPainter, QBrush, QPen, QLinearGradient,
    QTextCharFormat, QSyntaxHighlighter
)

# ─── PALETTE ──────────────────────────────────────────────────────────────────
C = {
    "bg":        "#0D0F12",
    "surface":   "#141720",
    "panel":     "#1A1D26",
    "border":    "#252836",
    "border2":   "#2E3347",
    "text":      "#CDD6F4",
    "muted":     "#6C7086",
    "accent":    "#7EB8F7",   # steel blue — matches terminal/data tools
    "accent2":   "#5E9FDE",
    "green":     "#A6E3A1",
    "yellow":    "#F9E2AF",
    "red":       "#F38BA8",
    "orange":    "#FAB387",
    "teal":      "#94E2D5",
    "mauve":     "#CBA6F7",
    "input_bg":  "#11131A",
    "hover":     "#1E2130",
    "active":    "#232638",
}

# ─── FONTS ────────────────────────────────────────────────────────────────────
MONO  = "Consolas"          # always present on Windows
SANS  = "Segoe UI"          # Windows system UI font
TITLE = "Segoe UI"

# ─── KITE LIMITS ─────────────────────────────────────────────────────────────
CHUNK_DAYS = {
    "minute": 60, "3minute": 100, "5minute": 100, "10minute": 100,
    "15minute": 200, "30minute": 200, "60minute": 400,
    "day": 2000, "week": 2000, "month": 2000,
}
INTERVALS     = list(CHUNK_DAYS.keys())
BASE_URL      = "https://kite.zerodha.com/oms"
SETTINGS_FILE = Path(__file__).parent / "settings.json"

# ─── STYLESHEET ───────────────────────────────────────────────────────────────
QSS = f"""
QWidget {{
    background-color: {C['bg']};
    color: {C['text']};
    font-family: "{SANS}";
    font-size: 13px;
    border: none;
    outline: none;
}}
QMainWindow, QDialog {{
    background-color: {C['bg']};
}}

/* ── PANELS ── */
QFrame#panel {{
    background-color: {C['panel']};
    border: 1px solid {C['border']};
    border-radius: 8px;
}}
QGroupBox {{
    background-color: {C['panel']};
    border: 1px solid {C['border']};
    border-radius: 8px;
    margin-top: 18px;
    padding-top: 6px;
    font-family: "{SANS}";
    font-size: 11px;
    font-weight: 600;
    color: {C['muted']};
    letter-spacing: 1.2px;
    text-transform: uppercase;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 4px;
    background-color: {C['panel']};
}}

/* ── INPUTS ── */
QLineEdit, QPlainTextEdit, QTextEdit {{
    background-color: {C['input_bg']};
    border: 1px solid {C['border']};
    border-radius: 6px;
    padding: 6px 10px;
    color: {C['text']};
    font-family: "{MONO}";
    font-size: 12px;
    selection-background-color: {C['accent2']};
}}
QLineEdit:focus, QPlainTextEdit:focus {{
    border: 1px solid {C['accent']};
}}
QPlainTextEdit {{
    padding: 8px;
}}

/* ── COMBO / DATE ── */
QComboBox {{
    background-color: {C['input_bg']};
    border: 1px solid {C['border']};
    border-radius: 6px;
    padding: 6px 10px;
    color: {C['text']};
    font-family: "{MONO}";
    min-width: 110px;
}}
QComboBox:focus {{ border: 1px solid {C['accent']}; }}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox::down-arrow {{
    width: 10px; height: 10px;
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid {C['muted']};
    margin-right: 6px;
}}
QComboBox QAbstractItemView {{
    background-color: {C['surface']};
    border: 1px solid {C['border2']};
    border-radius: 6px;
    color: {C['text']};
    selection-background-color: {C['accent2']};
    padding: 4px;
}}
QDateEdit {{
    background-color: {C['input_bg']};
    border: 1px solid {C['border']};
    border-radius: 6px;
    padding: 6px 10px;
    color: {C['text']};
    font-family: "{MONO}";
}}
QDateEdit:focus {{ border: 1px solid {C['accent']}; }}
QDateEdit::drop-down {{ border: none; width: 22px; }}
QDateEdit::down-arrow {{
    width: 10px; height: 10px;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid {C['muted']};
    margin-right: 6px;
}}

/* ── BUTTONS ── */
QPushButton {{
    background-color: {C['surface']};
    border: 1px solid {C['border2']};
    border-radius: 6px;
    padding: 8px 18px;
    color: {C['text']};
    font-family: "{SANS}";
    font-weight: 500;
    font-size: 13px;
}}
QPushButton:hover {{
    background-color: {C['hover']};
    border-color: {C['accent']};
}}
QPushButton:pressed {{
    background-color: {C['active']};
}}
QPushButton#primary {{
    background-color: {C['accent2']};
    border: 1px solid {C['accent']};
    color: #0D0F12;
    font-weight: 700;
    font-size: 14px;
    padding: 10px 28px;
    letter-spacing: 0.5px;
}}
QPushButton#primary:hover {{
    background-color: {C['accent']};
}}
QPushButton#primary:disabled {{
    background-color: {C['border']};
    border-color: {C['border']};
    color: {C['muted']};
}}
QPushButton#danger {{
    background-color: transparent;
    border: 1px solid {C['red']};
    color: {C['red']};
}}
QPushButton#danger:hover {{
    background-color: rgba(243,139,168,0.12);
}}
QPushButton#small {{
    padding: 5px 12px;
    font-size: 12px;
    border-radius: 5px;
}}

/* ── PROGRESS BAR ── */
QProgressBar {{
    background-color: {C['surface']};
    border: 1px solid {C['border']};
    border-radius: 4px;
    height: 6px;
    text-align: center;
    color: transparent;
}}
QProgressBar::chunk {{
    background-color: {C['accent']};
    border-radius: 4px;
}}

/* ── TABLE ── */
QTableWidget {{
    background-color: {C['surface']};
    border: 1px solid {C['border']};
    border-radius: 6px;
    gridline-color: {C['border']};
    font-family: "{MONO}";
    font-size: 12px;
}}
QTableWidget::item {{
    padding: 5px 8px;
    border-bottom: 1px solid {C['border']};
}}
QTableWidget::item:selected {{
    background-color: {C['active']};
    color: {C['accent']};
}}
QHeaderView::section {{
    background-color: {C['panel']};
    border: none;
    border-bottom: 1px solid {C['border2']};
    border-right: 1px solid {C['border']};
    padding: 6px 8px;
    font-family: "{SANS}";
    font-size: 11px;
    font-weight: 600;
    color: {C['muted']};
    letter-spacing: 0.8px;
    text-transform: uppercase;
}}

/* ── SCROLLBARS ── */
QScrollBar:vertical {{
    background: {C['bg']};
    width: 8px;
    border-radius: 4px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {C['border2']};
    border-radius: 4px;
    min-height: 20px;
}}
QScrollBar::handle:vertical:hover {{ background: {C['muted']}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{
    background: {C['bg']};
    height: 8px;
    border-radius: 4px;
}}
QScrollBar::handle:horizontal {{
    background: {C['border2']};
    border-radius: 4px;
    min-width: 20px;
}}
QScrollBar::handle:horizontal:hover {{ background: {C['muted']}; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}

/* ── CHECKBOX ── */
QCheckBox {{
    spacing: 8px;
    color: {C['text']};
    font-size: 13px;
}}
QCheckBox::indicator {{
    width: 16px; height: 16px;
    border: 1px solid {C['border2']};
    border-radius: 4px;
    background-color: {C['input_bg']};
}}
QCheckBox::indicator:checked {{
    background-color: {C['accent2']};
    border-color: {C['accent']};
}}

/* ── STATUS BAR ── */
QStatusBar {{
    background-color: {C['surface']};
    border-top: 1px solid {C['border']};
    color: {C['muted']};
    font-size: 12px;
    padding: 0 10px;
}}

/* ── SPLITTER ── */
QSplitter::handle {{
    background-color: {C['border']};
}}
QSplitter::handle:horizontal {{ width: 1px; }}
QSplitter::handle:vertical   {{ height: 1px; }}

/* ── LABEL variants ── */
QLabel#section_title {{
    color: {C['muted']};
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 1.2px;
    text-transform: uppercase;
}}
QLabel#value {{
    color: {C['text']};
    font-family: "{MONO}";
    font-size: 13px;
}}
QLabel#accent {{
    color: {C['accent']};
    font-family: "{MONO}";
    font-size: 13px;
    font-weight: 600;
}}
"""

# ─── WORKER THREAD ────────────────────────────────────────────────────────────

class DownloadWorker(QThread):
    log_signal       = pyqtSignal(str, str)   # (message, level)
    progress_signal  = pyqtSignal(int, int)    # (current, total)
    row_signal       = pyqtSignal(dict)        # one completed instrument
    done_signal      = pyqtSignal(bool, str)   # (success, summary)

    def __init__(self, config: dict):
        super().__init__()
        self.config  = config
        self._cancel = False

    def cancel(self):
        self._cancel = True

    def log(self, msg, level="info"):
        self.log_signal.emit(msg, level)

    # ── helpers ────────────────────────────────────────────────────────────────

    def _headers(self):
        uid = self.config["user_id"]
        tok = self.config["enctoken"]
        return {
            "Authorization": f"enctoken {tok}",
            "X-Kite-Version": "3",
            "User-Agent":    f"Kite/{uid}",
        }

    def _instruments(self):
        self.log("Fetching instruments master…", "info")
        url = "https://api.kite.trade/instruments"
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        df = pd.read_csv(StringIO(r.text))
        self.log(f"Instruments loaded: {len(df):,} rows", "ok")
        return df

    def _resolve(self, identifier, df):
        if str(identifier).strip().lstrip("-").isdigit():
            token = int(identifier)
            row   = df[df["instrument_token"] == token]
            if row.empty:
                raise ValueError(f"Token {token} not found")
            r = row.iloc[0]
            return int(r["instrument_token"]), r["tradingsymbol"], r["exchange"]

        sym   = str(identifier).strip().upper()
        exch  = self.config["exchange"].upper()
        row   = df[(df["tradingsymbol"].str.upper() == sym) &
                   (df["exchange"].str.upper() == exch)]
        if row.empty:
            row = df[df["tradingsymbol"].str.upper() == sym]
        if row.empty:
            raise ValueError(f"'{identifier}' not found in instruments master")
        r = row.iloc[0]
        return int(r["instrument_token"]), r["tradingsymbol"], r["exchange"]

    def _date_chunks(self, from_date, to_date, chunk_days):
        start   = datetime.strptime(from_date, "%Y-%m-%d")
        end     = datetime.strptime(to_date,   "%Y-%m-%d")
        current = start
        while current <= end:
            chunk_end = min(current + timedelta(days=chunk_days - 1), end)
            yield current.strftime("%Y-%m-%d"), chunk_end.strftime("%Y-%m-%d")
            current = chunk_end + timedelta(days=1)

    def _fetch_chunk(self, token, start, end, interval, headers):
        url    = f"{BASE_URL}/instruments/historical/{token}/{interval}"
        params = {"from": start, "to": end, "continuous": 0, "oi": 1}
        for attempt in range(3):
            if self._cancel:
                return []
            try:
                r = requests.get(url, headers=headers, params=params, timeout=30)
                if r.status_code == 429:
                    self.log(f"  Rate limited — waiting 3s…", "warn")
                    time.sleep(3)
                    continue
                if r.status_code != 200:
                    self.log(f"  HTTP {r.status_code} [{start}→{end}]: {r.text[:80]}", "err")
                    return []
                data = r.json()
                if data.get("status") != "success":
                    self.log(f"  API error: {data.get('message', '?')}", "err")
                    return []
                return data.get("data", {}).get("candles", [])
            except Exception as e:
                self.log(f"  Request error (attempt {attempt+1}/3): {e}", "warn")
                time.sleep(1.5)
        return []

    # ── main run ───────────────────────────────────────────────────────────────

    def run(self):
        try:
            cfg       = self.config
            headers   = self._headers()
            inst_df   = self._instruments()
            symbols   = [s.strip() for s in cfg["symbols"] if s.strip()]
            interval  = cfg["interval"]
            from_date = cfg["from_date"]
            to_date   = cfg["to_date"]
            out_dir   = Path(cfg["out_dir"])
            out_dir.mkdir(parents=True, exist_ok=True)
            delay     = cfg.get("delay", 0.35)

            chunk_days  = CHUNK_DAYS.get(interval, 60)
            total_syms  = len(symbols)
            saved_paths = []

            self.log(f"Starting download: {total_syms} instrument(s) / {interval}", "info")
            self.log(f"Range: {from_date} → {to_date}  |  Chunk: {chunk_days}d", "info")
            self.log("─" * 56, "muted")

            for idx, ident in enumerate(symbols):
                if self._cancel:
                    self.log("⚠  Cancelled by user.", "warn")
                    break

                self.progress_signal.emit(idx, total_syms)
                self.log(f"[{idx+1}/{total_syms}] Resolving: {ident}", "info")

                try:
                    token, symbol, exchange = self._resolve(ident, inst_df)
                except ValueError as e:
                    self.log(f"  ✗ {e}", "err")
                    self.row_signal.emit({
                        "symbol": str(ident), "exchange": "—", "token": "—",
                        "rows": 0, "status": "NOT FOUND", "file": ""
                    })
                    continue

                self.log(f"  Token={token}  Symbol={symbol}  Exchange={exchange}", "accent")
                chunks     = list(self._date_chunks(from_date, to_date, chunk_days))
                all_candles = []

                for i, (start, end) in enumerate(chunks):
                    if self._cancel:
                        break
                    candles = self._fetch_chunk(token, start, end, interval, headers)
                    all_candles.extend(candles)
                    self.log(
                        f"  chunk {i+1:>2}/{len(chunks)}  {start} → {end}  "
                        f"({len(candles)} bars)", "muted"
                    )
                    time.sleep(delay)

                if not all_candles:
                    self.log(f"  ✗ No data for {symbol}", "err")
                    self.row_signal.emit({
                        "symbol": symbol, "exchange": exchange, "token": str(token),
                        "rows": 0, "status": "NO DATA", "file": ""
                    })
                    continue

                cols = ["date", "open", "high", "low", "close", "volume", "oi"]
                df = pd.DataFrame(all_candles, columns=cols[:len(all_candles[0])])
                df["date"] = pd.to_datetime(df["date"])
                df.drop_duplicates(subset=["date"], inplace=True)
                df.sort_values("date", inplace=True)
                df.reset_index(drop=True, inplace=True)
                df.insert(0, "symbol",   symbol)
                df.insert(1, "exchange", exchange)
                df.insert(2, "token",    token)
                df.insert(3, "interval", interval)

                safe = symbol.replace(" ", "_").replace("/", "-")
                fname = out_dir / f"{exchange}_{safe}_{interval}.csv"
                df.to_csv(fname, index=False)
                saved_paths.append(fname)

                self.log(f"  ✓ {len(df):,} rows → {fname.name}", "ok")
                self.log("─" * 56, "muted")
                self.row_signal.emit({
                    "symbol": symbol, "exchange": exchange, "token": str(token),
                    "rows": len(df), "status": "DONE", "file": str(fname)
                })

            self.progress_signal.emit(total_syms, total_syms)

            # Merge
            if cfg.get("merge") and len(saved_paths) > 1:
                self.log("Merging all files…", "info")
                merged = pd.concat([pd.read_csv(p) for p in saved_paths], ignore_index=True)
                merged["date"] = pd.to_datetime(merged["date"])
                merged.sort_values(["symbol", "date"], inplace=True)
                merged.reset_index(drop=True, inplace=True)
                mpath = out_dir / f"merged_{interval}_{from_date}_{to_date}.csv"
                merged.to_csv(mpath, index=False)
                self.log(f"✓ Merged: {mpath.name}  ({len(merged):,} total rows)", "ok")

            n = len(saved_paths)
            summary = f"{n}/{total_syms} instrument(s) downloaded to {out_dir}"
            self.done_signal.emit(not self._cancel, summary)

        except Exception:
            tb = traceback.format_exc()
            self.log(f"Fatal error:\n{tb}", "err")
            self.done_signal.emit(False, "Download failed — see log")


# ─── LOG HIGHLIGHTER ──────────────────────────────────────────────────────────

class LogHighlighter(QSyntaxHighlighter):
    def __init__(self, doc):
        super().__init__(doc)
        self.rules = [
            (re.compile(r"✓.*"),         QColor(C["green"])),
            (re.compile(r"✗.*"),         QColor(C["red"])),
            (re.compile(r"⚠.*"),         QColor(C["yellow"])),
            (re.compile(r"Fatal.*"),      QColor(C["red"])),
            (re.compile(r"^─+$"),         QColor(C["border2"])),
            (re.compile(r"Token=\d+"),    QColor(C["mauve"])),
            (re.compile(r"Symbol=\S+"),   QColor(C["accent"])),
            (re.compile(r"\d{4}-\d{2}-\d{2}"), QColor(C["teal"])),
            (re.compile(r"\d{1,3}(?:,\d{3})*\s+rows"), QColor(C["orange"])),
            (re.compile(r"\[.*?\]"),      QColor(C["muted"])),
        ]

    def highlightBlock(self, text):
        for pattern, color in self.rules:
            fmt = QTextCharFormat()
            fmt.setForeground(color)
            for m in pattern.finditer(text):
                self.setFormat(m.start(), m.end() - m.start(), fmt)


# ─── STAT CARD ────────────────────────────────────────────────────────────────

class StatCard(QFrame):
    def __init__(self, label, value="—", accent=False):
        super().__init__()
        self.setObjectName("panel")
        self.setFixedHeight(64)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 8, 14, 8)
        lay.setSpacing(2)

        self._lbl = QLabel(label.upper())
        self._lbl.setObjectName("section_title")
        self._lbl.setFont(QFont(SANS, 10, QFont.DemiBold))

        color = C["accent"] if accent else C["text"]
        self._val = QLabel(value)
        self._val.setFont(QFont(MONO, 15, QFont.Bold))
        self._val.setStyleSheet(f"color: {color}; background: transparent;")

        lay.addWidget(self._lbl)
        lay.addWidget(self._val)

    def set_value(self, v):
        self._val.setText(str(v))


# ─── INSTRUMENT TABLE ─────────────────────────────────────────────────────────

class InstrumentTable(QTableWidget):
    COLS = ["Symbol", "Exchange", "Token", "Rows", "Status"]

    def __init__(self):
        super().__init__(0, len(self.COLS))
        self.setHorizontalHeaderLabels(self.COLS)
        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.verticalHeader().setVisible(False)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setAlternatingRowColors(False)
        self.setShowGrid(False)
        self.setFocusPolicy(Qt.NoFocus)

    def add_row(self, data: dict):
        r = self.rowCount()
        self.insertRow(r)
        cells = [
            data.get("symbol", ""),
            data.get("exchange", ""),
            data.get("token", ""),
            f'{data.get("rows", 0):,}' if data.get("rows") else "—",
            data.get("status", ""),
        ]
        status_colors = {
            "DONE":      C["green"],
            "NO DATA":   C["yellow"],
            "NOT FOUND": C["red"],
        }
        for col, text in enumerate(cells):
            item = QTableWidgetItem(text)
            item.setTextAlignment(Qt.AlignVCenter | (Qt.AlignRight if col == 3 else Qt.AlignLeft))
            if col == 4:
                color = status_colors.get(text, C["muted"])
                item.setForeground(QColor(color))
                item.setFont(QFont(MONO, 11, QFont.Bold))
            self.setItem(r, col, item)
        self.scrollToBottom()


# ─── MAIN WINDOW ─────────────────────────────────────────────────────────────

class KiteDownloader(QMainWindow):
    def __init__(self):
        super().__init__()
        self.worker      = None
        self._downloaded = 0
        self._total      = 0
        self._start_time = None

        self.setWindowTitle("Kite Historical Downloader")
        self.setMinimumSize(1080, 720)
        self.resize(1200, 800)
        self.setStyleSheet(QSS)

        self._build_ui()
        self._tick_timer = QTimer()
        self._tick_timer.timeout.connect(self._tick)
        self._load_settings()

    # ── UI BUILD ──────────────────────────────────────────────────────────────

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── header bar ──
        root.addWidget(self._header())

        # ── body ──
        body = QSplitter(Qt.Horizontal)
        body.setHandleWidth(1)
        body.addWidget(self._left_panel())
        body.addWidget(self._right_panel())
        body.setSizes([420, 780])
        root.addWidget(body, 1)

        # ── status bar ──
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

    def _header(self):
        bar = QFrame()
        bar.setFixedHeight(52)
        bar.setStyleSheet(f"""
            QFrame {{
                background-color: {C['surface']};
                border-bottom: 1px solid {C['border']};
            }}
        """)
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(20, 0, 20, 0)

        # Logo / title
        title = QLabel("KITE  HISTORICAL")
        title.setFont(QFont(SANS, 14, QFont.Bold))
        title.setStyleSheet(f"color: {C['text']}; letter-spacing: 2px; background: transparent;")

        badge = QLabel("enctoken")
        badge.setFont(QFont(MONO, 10))
        badge.setStyleSheet(f"""
            color: {C['accent']};
            background: rgba(126,184,247,0.12);
            border: 1px solid rgba(126,184,247,0.3);
            border-radius: 4px;
            padding: 2px 8px;
        """)

        lay.addWidget(title)
        lay.addWidget(badge)
        lay.addStretch()

        self._clock = QLabel()
        self._clock.setFont(QFont(MONO, 11))
        self._clock.setStyleSheet(f"color: {C['muted']}; background: transparent;")
        QTimer.singleShot(0, self._update_clock)
        QTimer.singleShot(1000, self._start_clock)
        lay.addWidget(self._clock)

        return bar

    def _start_clock(self):
        t = QTimer(self)
        t.timeout.connect(self._update_clock)
        t.start(1000)

    def _update_clock(self):
        self._clock.setText(datetime.now().strftime("%H:%M:%S  %d %b %Y"))

    def _left_panel(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(14, 14, 8, 14)
        lay.setSpacing(12)

        # ── AUTH ──────────────────────────────────────────────────────────────
        auth_group = QGroupBox("Auth")
        ag = QGridLayout(auth_group)
        ag.setContentsMargins(12, 16, 12, 12)
        ag.setVerticalSpacing(8)
        ag.setHorizontalSpacing(10)

        ag.addWidget(self._label("User ID"), 0, 0)
        self.inp_uid = QLineEdit()
        self.inp_uid.setPlaceholderText("e.g. ZA1234")
        ag.addWidget(self.inp_uid, 0, 1)

        ag.addWidget(self._label("Enctoken"), 1, 0)
        self.inp_tok = QLineEdit()
        self.inp_tok.setPlaceholderText("Paste from kite.zerodha.com cookies")
        self.inp_tok.setEchoMode(QLineEdit.Password)
        self.show_tok_btn = QPushButton("Show")
        self.show_tok_btn.setObjectName("small")
        self.show_tok_btn.setFixedWidth(52)
        self.show_tok_btn.clicked.connect(self._toggle_token)
        tok_row = QHBoxLayout()
        tok_row.setSpacing(6)
        tok_row.addWidget(self.inp_tok)
        tok_row.addWidget(self.show_tok_btn)
        ag.addLayout(tok_row, 1, 1)

        lay.addWidget(auth_group)

        # ── INSTRUMENTS ────────────────────────────────────────────────────────
        sym_group = QGroupBox("Instruments")
        sg = QVBoxLayout(sym_group)
        sg.setContentsMargins(12, 16, 12, 12)
        sg.setSpacing(8)

        hint = QLabel("One symbol or token per line  •  Mix NSE/NFO/MCX freely")
        hint.setFont(QFont(SANS, 10))
        hint.setStyleSheet(f"color: {C['muted']}; background: transparent;")
        hint.setWordWrap(True)
        sg.addWidget(hint)

        self.inp_symbols = QPlainTextEdit()
        self.inp_symbols.setPlaceholderText(
            "RELIANCE\nINFY\nNIFTY 50\n256265\nGOLD24JUNFUT"
        )
        self.inp_symbols.setMinimumHeight(130)
        sg.addWidget(self.inp_symbols)

        exch_row = QHBoxLayout()
        exch_row.addWidget(self._label("Default Exchange"))
        self.cmb_exch = QComboBox()
        self.cmb_exch.addItems(["NSE", "BSE", "NFO", "MCX", "CDS", "BFO"])
        exch_row.addWidget(self.cmb_exch)
        sg.addLayout(exch_row)

        lay.addWidget(sym_group)

        # ── DATE / INTERVAL ────────────────────────────────────────────────────
        di_group = QGroupBox("Date & Interval")
        dg = QGridLayout(di_group)
        dg.setContentsMargins(12, 16, 12, 12)
        dg.setVerticalSpacing(8)
        dg.setHorizontalSpacing(10)

        dg.addWidget(self._label("From"), 0, 0)
        self.date_from = QDateEdit(QDate(2020, 1, 1))
        self.date_from.setCalendarPopup(True)
        self.date_from.setDisplayFormat("yyyy-MM-dd")
        dg.addWidget(self.date_from, 0, 1)

        dg.addWidget(self._label("To"), 1, 0)
        self.date_to = QDateEdit(QDate.currentDate())
        self.date_to.setCalendarPopup(True)
        self.date_to.setDisplayFormat("yyyy-MM-dd")
        dg.addWidget(self.date_to, 1, 1)

        dg.addWidget(self._label("Interval"), 2, 0)
        self.cmb_interval = QComboBox()
        self.cmb_interval.addItems(INTERVALS)
        self.cmb_interval.setCurrentText("day")
        dg.addWidget(self.cmb_interval, 2, 1)

        lay.addWidget(di_group)

        # ── OUTPUT ─────────────────────────────────────────────────────────────
        out_group = QGroupBox("Output")
        og = QVBoxLayout(out_group)
        og.setContentsMargins(12, 16, 12, 12)
        og.setSpacing(8)

        out_row = QHBoxLayout()
        out_row.setSpacing(6)
        self.inp_outdir = QLineEdit()
        self.inp_outdir.setText(str(Path.home() / "kite_data"))
        browse_btn = QPushButton("Browse")
        browse_btn.setObjectName("small")
        browse_btn.setFixedWidth(64)
        browse_btn.clicked.connect(self._browse_dir)
        out_row.addWidget(self.inp_outdir)
        out_row.addWidget(browse_btn)
        og.addLayout(out_row)

        self.chk_merge = QCheckBox("Merge all instruments into one CSV")
        self.chk_merge.setChecked(True)
        og.addWidget(self.chk_merge)

        lay.addWidget(out_group)

        # ── ACTIONS ───────────────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self.btn_start = QPushButton("▶  Start Download")
        self.btn_start.setObjectName("primary")
        self.btn_start.clicked.connect(self._start)

        self.btn_stop = QPushButton("■  Stop")
        self.btn_stop.setObjectName("danger")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self._stop)

        btn_row.addWidget(self.btn_start)
        btn_row.addWidget(self.btn_stop)
        lay.addLayout(btn_row)

        lay.addStretch()
        return w

    def _right_panel(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(8, 14, 14, 14)
        lay.setSpacing(12)

        # ── STAT CARDS ────────────────────────────────────────────────────────
        cards_row = QHBoxLayout()
        cards_row.setSpacing(10)
        self.card_done    = StatCard("Downloaded",  "0",    accent=True)
        self.card_total   = StatCard("Total",       "—")
        self.card_rows    = StatCard("Total Rows",  "—")
        self.card_elapsed = StatCard("Elapsed",     "00:00")
        cards_row.addWidget(self.card_done)
        cards_row.addWidget(self.card_total)
        cards_row.addWidget(self.card_rows)
        cards_row.addWidget(self.card_elapsed)
        lay.addLayout(cards_row)

        # ── PROGRESS ──────────────────────────────────────────────────────────
        self.progress = QProgressBar()
        self.progress.setFixedHeight(6)
        self.progress.setValue(0)
        lay.addWidget(self.progress)

        # ── RESULTS TABLE ─────────────────────────────────────────────────────
        tbl_label = QLabel("RESULTS")
        tbl_label.setObjectName("section_title")
        tbl_label.setFont(QFont(SANS, 10, QFont.DemiBold))
        lay.addWidget(tbl_label)

        self.results_table = InstrumentTable()
        self.results_table.setMaximumHeight(220)
        lay.addWidget(self.results_table)

        # ── LOG ───────────────────────────────────────────────────────────────
        log_hdr = QHBoxLayout()
        log_label = QLabel("ACTIVITY LOG")
        log_label.setObjectName("section_title")
        log_label.setFont(QFont(SANS, 10, QFont.DemiBold))
        clear_btn = QPushButton("Clear")
        clear_btn.setObjectName("small")
        clear_btn.setFixedWidth(52)
        clear_btn.clicked.connect(self._clear_log)
        log_hdr.addWidget(log_label)
        log_hdr.addStretch()
        log_hdr.addWidget(clear_btn)
        lay.addLayout(log_hdr)

        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setFont(QFont(MONO, 11))
        self.log_view.setStyleSheet(f"""
            QPlainTextEdit {{
                background-color: {C['input_bg']};
                border: 1px solid {C['border']};
                border-radius: 6px;
                color: {C['text']};
                padding: 10px;
            }}
        """)
        self._highlighter = LogHighlighter(self.log_view.document())
        lay.addWidget(self.log_view, 1)

        self._append_log("Ready. Configure credentials and instruments, then press Start.", "muted")

        return w

    # ── helpers ───────────────────────────────────────────────────────────────

    def _label(self, text):
        lbl = QLabel(text)
        lbl.setFont(QFont(SANS, 12))
        lbl.setStyleSheet(f"color: {C['muted']}; background: transparent;")
        lbl.setFixedWidth(130)
        return lbl

    def _toggle_token(self):
        if self.inp_tok.echoMode() == QLineEdit.Password:
            self.inp_tok.setEchoMode(QLineEdit.Normal)
            self.show_tok_btn.setText("Hide")
        else:
            self.inp_tok.setEchoMode(QLineEdit.Password)
            self.show_tok_btn.setText("Show")

    def _browse_dir(self):
        d = QFileDialog.getExistingDirectory(self, "Select output directory",
                                              self.inp_outdir.text())
        if d:
            self.inp_outdir.setText(d)

    def _clear_log(self):
        self.log_view.clear()

    # ── log display ───────────────────────────────────────────────────────────

    def _append_log(self, msg, level="info"):
        ts    = datetime.now().strftime("%H:%M:%S")
        line  = f"[{ts}]  {msg}"
        self.log_view.appendPlainText(line)
        cur = self.log_view.textCursor()
        cur.movePosition(QTextCursor.End)
        self.log_view.setTextCursor(cur)

    def _on_log(self, msg, level):
        self._append_log(msg, level)

    # ── progress / results ────────────────────────────────────────────────────

    def _on_progress(self, current, total):
        self._downloaded = current
        self._total      = total
        self.card_done.set_value(current)
        self.card_total.set_value(total)
        if total > 0:
            self.progress.setMaximum(total)
            self.progress.setValue(current)

    def _on_row(self, data):
        self.results_table.add_row(data)
        rows = data.get("rows", 0)
        if rows:
            try:
                cur = int(self.card_rows._val.text().replace(",", "").replace("—", "0"))
            except Exception:
                cur = 0
            self.card_rows.set_value(f"{cur + rows:,}")

    def _tick(self):
        if self._start_time:
            elapsed = int(time.time() - self._start_time)
            m, s = divmod(elapsed, 60)
            self.card_elapsed.set_value(f"{m:02d}:{s:02d}")

    # ── download control ──────────────────────────────────────────────────────

    def _start(self):
        uid  = self.inp_uid.text().strip()
        tok  = self.inp_tok.text().strip()
        syms = [s for s in self.inp_symbols.toPlainText().splitlines() if s.strip()]

        if not uid or not tok:
            QMessageBox.warning(self, "Missing Credentials",
                                "Please enter your User ID and Enctoken.")
            return
        if not syms:
            QMessageBox.warning(self, "No Instruments",
                                "Add at least one symbol or token.")
            return

        # Reset UI
        self.results_table.setRowCount(0)
        self.card_done.set_value("0")
        self.card_total.set_value(str(len(syms)))
        self.card_rows.set_value("—")
        self.card_elapsed.set_value("00:00")
        self.progress.setValue(0)
        self.progress.setMaximum(len(syms))
        self._downloaded = 0
        self._total      = len(syms)
        self._start_time = time.time()

        config = {
            "user_id":   uid,
            "enctoken":  tok,
            "symbols":   syms,
            "exchange":  self.cmb_exch.currentText(),
            "interval":  self.cmb_interval.currentText(),
            "from_date": self.date_from.date().toString("yyyy-MM-dd"),
            "to_date":   self.date_to.date().toString("yyyy-MM-dd"),
            "out_dir":   self.inp_outdir.text().strip() or str(Path.home() / "kite_data"),
            "merge":     self.chk_merge.isChecked(),
            "delay":     0.35,
        }

        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.status_bar.showMessage("Downloading…")
        self._tick_timer.start(1000)

        self.worker = DownloadWorker(config)
        self.worker.log_signal.connect(self._on_log)
        self.worker.progress_signal.connect(self._on_progress)
        self.worker.row_signal.connect(self._on_row)
        self.worker.done_signal.connect(self._on_done)
        self.worker.start()

    def _stop(self):
        if self.worker:
            self.worker.cancel()
        self.btn_stop.setEnabled(False)

    # ── settings persistence ──────────────────────────────────────────────────

    def _save_settings(self):
        data = {
            "user_id":   self.inp_uid.text(),
            "enctoken":  self.inp_tok.text(),
            "symbols":   self.inp_symbols.toPlainText(),
            "exchange":  self.cmb_exch.currentText(),
            "interval":  self.cmb_interval.currentText(),
            "from_date": self.date_from.date().toString("yyyy-MM-dd"),
            "to_date":   self.date_to.date().toString("yyyy-MM-dd"),
            "out_dir":   self.inp_outdir.text(),
            "merge":     self.chk_merge.isChecked(),
        }
        try:
            SETTINGS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as e:
            print(f"[settings] save failed: {e}")

    def _load_settings(self):
        if not SETTINGS_FILE.exists():
            return
        try:
            data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"[settings] load failed: {e}")
            return

        self.inp_uid.setText(data.get("user_id", ""))
        self.inp_tok.setText(data.get("enctoken", ""))
        syms = data.get("symbols", "")
        if syms:
            self.inp_symbols.setPlainText(syms)
        idx = self.cmb_exch.findText(data.get("exchange", "NSE"))
        if idx >= 0:
            self.cmb_exch.setCurrentIndex(idx)
        idx = self.cmb_interval.findText(data.get("interval", "day"))
        if idx >= 0:
            self.cmb_interval.setCurrentIndex(idx)
        for attr, key in [("date_from", "from_date"), ("date_to", "to_date")]:
            val = data.get(key, "")
            if val:
                d = QDate.fromString(val, "yyyy-MM-dd")
                if d.isValid():
                    getattr(self, attr).setDate(d)
        self.inp_outdir.setText(data.get("out_dir", str(Path.home() / "kite_data")))
        self.chk_merge.setChecked(bool(data.get("merge", True)))

    def closeEvent(self, event):
        self._save_settings()
        event.accept()

    def _on_done(self, success, summary):
        self._tick_timer.stop()
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)

        icon   = "✓" if success else "✗"
        level  = "ok" if success else "err"
        self._append_log(f"{icon}  {summary}", level)
        self.status_bar.showMessage(summary)

        if success:
            out = self.inp_outdir.text().strip() or str(Path.home() / "kite_data")
            ret = QMessageBox.information(
                self, "Download Complete",
                f"{summary}\n\nOpen output folder?",
                QMessageBox.Yes | QMessageBox.No
            )
            if ret == QMessageBox.Yes:
                os.startfile(out)   # Windows only


# ─── ENTRY ───────────────────────────────────────────────────────────────────

def main():
    # Enable HiDPI on Windows
    if hasattr(Qt, "AA_EnableHighDpiScaling"):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, "AA_UseHighDpiPixmaps"):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setStyle("Fusion")          # Consistent cross-platform baseline

    # Dark palette so native widgets (dialogs, file pickers) match
    pal = QPalette()
    pal.setColor(QPalette.Window,          QColor(C["bg"]))
    pal.setColor(QPalette.WindowText,      QColor(C["text"]))
    pal.setColor(QPalette.Base,            QColor(C["input_bg"]))
    pal.setColor(QPalette.AlternateBase,   QColor(C["surface"]))
    pal.setColor(QPalette.ToolTipBase,     QColor(C["surface"]))
    pal.setColor(QPalette.ToolTipText,     QColor(C["text"]))
    pal.setColor(QPalette.Text,            QColor(C["text"]))
    pal.setColor(QPalette.Button,          QColor(C["surface"]))
    pal.setColor(QPalette.ButtonText,      QColor(C["text"]))
    pal.setColor(QPalette.BrightText,      QColor(C["red"]))
    pal.setColor(QPalette.Link,            QColor(C["accent"]))
    pal.setColor(QPalette.Highlight,       QColor(C["accent2"]))
    pal.setColor(QPalette.HighlightedText, QColor(C["bg"]))
    app.setPalette(pal)

    win = KiteDownloader()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
