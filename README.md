"""
Kite Historical Downloader — GUI
=================================
Dark terminal-style GUI for bulk historical data download from Zerodha Kite.
- enctoken auth only (no API key / no paid plan)
- Auto symbol/token resolution from instruments master
- Chunked requests respecting Kite API limits
- Threaded — UI never freezes
- Live progress log
- Per-instrument CSVs + optional merged file

Requirements:
    pip install PyQt5 pandas requests python-dateutil

Run:
    python kite_downloader_gui.py
"""

UI design boilerplate assisted by AI
