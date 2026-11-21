"""
DataDowner Pro Web  —  Fast High-Performance Kite Downloader & Technical Analyzer
================================================================================
• Engine: Local FastAPI + Uvicorn web app (zero PyQt freezes, instant 100ms load)
• UI    : Responsive CSS Grid & Flexbox layout with Dark / Light Theme
• Chart : TradingView Lightweight Charts (60 FPS canvas, pan, zoom, crosshair)
• Data  : Auto-timeframe resampler (1m -> 5m, 15m, 1h, 1D, 1W, 1M)
• TA    : Full OpenAlgo Indicator Catalog (30+ indicators across MA, Oscillators, Bands, Trend, Vol)
• Tools : Interactive Trendlines & Horizontal lines with persistent JSON saving
"""
from __future__ import annotations
import sys, webbrowser, threading, time
from pathlib import Path
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from datadowner_engine import AppAPI, HERE, HTML_FILE

app = FastAPI(title="DataDowner Pro Web")
api = AppAPI()

# Mount static files (e.g. lightweight-charts.standalone.js)
if HERE.exists():
    app.mount("/static", StaticFiles(directory=str(HERE)), name="static")

@app.get("/", response_class=HTMLResponse)
async def serve_root():
    return HTMLResponse(HTML_FILE.read_text(encoding="utf-8"))

@app.get("/api/settings")
async def get_settings():
    return JSONResponse(api.get_settings())

@app.post("/api/settings")
async def save_settings(req: Request):
    data = await req.json()
    return JSONResponse(api.save_settings(data))

@app.post("/api/validate-token")
async def validate_token(req: Request):
    data = await req.json()
    uid = str(data.get("uid", ""))
    enc = str(data.get("enc", ""))
    return JSONResponse(api.validate_token(uid, enc))

@app.get("/api/cache-status")
async def get_cache_status():
    return JSONResponse(api.get_cache_status())

@app.post("/api/fetch-instruments")
async def fetch_instruments(req: Request):
    data = await req.json()
    force = bool(data.get("force", False))
    uid   = str(data.get("uid", ""))
    enc   = str(data.get("enc", ""))
    return JSONResponse(api.fetch_instruments(force, uid, enc))

@app.get("/api/search-instruments")
async def search_instruments(q: str = "", exch: str = "All", type: str = "All", limit: int = 100):
    return JSONResponse(api.search_instruments(q, exch, type, limit))

@app.post("/api/start-download")
async def start_download(req: Request):
    payload = await req.json()
    return JSONResponse(api.start_download(payload))

@app.post("/api/stop-download")
async def stop_download():
    return JSONResponse(api.stop_download())

@app.get("/api/download-status")
async def get_download_status():
    return JSONResponse(api.get_download_status())

@app.api_route("/api/open-folder", methods=["GET", "POST"])
async def open_folder():
    return JSONResponse(api.open_data_folder())

@app.get("/api/list-csv-files")
async def list_csv_files():
    return JSONResponse(api.list_csv_files())

@app.get("/api/load-chart-data")
async def load_chart_data(filename: str, timeframe: str = "1D", chart_style: str = "candles"):
    return JSONResponse(api.load_chart_data(filename, timeframe, chart_style))

@app.post("/api/save-analysis")
async def save_analysis(req: Request):
    payload = await req.json()
    return JSONResponse(api.save_analysis(payload))

@app.post("/api/quick-fetch-chart")
async def quick_fetch_chart(req: Request):
    payload = await req.json()
    return JSONResponse(api.quick_fetch_chart(payload))

def main():
    port = 8765
    def open_browser():
        time.sleep(0.8)
        webbrowser.open(f"http://localhost:{port}")

    threading.Thread(target=open_browser, daemon=True).start()
    print(f"🚀 DataDowner Pro Web running at http://localhost:{port}")
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")

if __name__ == "__main__":
    main()
