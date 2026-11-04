"""FastAPI + server-rendered HTML dashboard over TrackingStore."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from naukari_pro.tracking.store import TrackingStore


def create_app(store: Optional[TrackingStore] = None):
    try:
        from fastapi import FastAPI
        from fastapi.responses import HTMLResponse, JSONResponse
    except ImportError as exc:
        raise RuntimeError("fastapi is required for the tracking dashboard") from exc

    store = store or TrackingStore()
    app = FastAPI(title="NaukariPro Tracking", version="0.6.0")

    @app.get("/api/funnel")
    def api_funnel():
        return store.funnel_counts()

    @app.get("/api/feed")
    def api_feed(limit: int = 50):
        return store.feed(limit=limit)

    @app.get("/api/rejections")
    def api_rejections():
        return {
            "histogram": store.rejection_histogram(),
            "by_ats": store.rejection_rate_by_ats(),
        }

    @app.get("/api/screen-pass")
    def api_screen_pass():
        return store.screen_pass_rate()

    @app.get("/", response_class=HTMLResponse)
    def home():
        funnel = store.funnel_counts()
        feed = store.feed(limit=25)
        hist = store.rejection_histogram()
        by_ats = store.rejection_rate_by_ats()
        spr = store.screen_pass_rate()
        rate_lbl = f"{spr['rate']:.0%}" if spr.get("rate") is not None else "n/a"
        rows = "".join(
            f"<tr><td>{r.get('company') or ''}</td><td>{r.get('title') or ''}</td>"
            f"<td>{r.get('fit_score') or ''}</td><td>{r.get('status')}</td>"
            f"<td>{r.get('ats') or ''}</td></tr>"
            for r in feed
        )
        funnel_cells = "".join(
            f"<div class='stat'><div class='n'>{v}</div><div class='l'>{k}</div></div>"
            for k, v in funnel.items()
        )
        hist_cells = "".join(
            f"<li>{k}: {v}</li>" for k, v in hist.items()
        )
        ats_cells = "".join(
            f"<li>{k}: {v:.0%}</li>" for k, v in by_ats.items()
        )
        board_cells = "".join(
            f"<li>{k}: {v['screens']}/{v['submitted']}"
            f" ({(v['rate'] or 0):.0%})</li>"
            for k, v in (spr.get("by_board") or {}).items()
        )
        html = f"""<!doctype html>
<html><head><meta charset="utf-8"><title>NaukariPro Tracking</title>
<style>
body{{font-family:ui-sans-serif,system-ui,sans-serif;margin:24px;background:#f7f7f5;color:#111}}
h1{{font-size:22px;margin:0 0 16px}}
.funnel{{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:20px}}
.stat{{background:#fff;border:1px solid #ddd;padding:12px 16px;min-width:90px}}
.stat .n{{font-size:22px;font-weight:700}}
.stat .l{{font-size:12px;color:#555;text-transform:uppercase}}
table{{width:100%;border-collapse:collapse;background:#fff}}
th,td{{border:1px solid #e5e5e5;padding:8px;text-align:left;font-size:13px}}
th{{background:#eee}}
.grid{{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:20px}}
</style></head><body>
<h1>NaukariPro Application Tracking</h1>
<div class="funnel">
<div class="stat"><div class="n">{rate_lbl}</div><div class="l">screen-pass</div></div>
<div class="stat"><div class="n">{spr.get('screens',0)}</div><div class="l">screens</div></div>
<div class="stat"><div class="n">{spr.get('submitted',0)}</div><div class="l">submitted</div></div>
{funnel_cells}
</div>
<table>
<thead><tr><th>Company</th><th>Title</th><th>Fit</th><th>Status</th><th>ATS</th></tr></thead>
<tbody>{rows or '<tr><td colspan=5>No applications yet</td></tr>'}</tbody>
</table>
<div class="grid">
<section><h2>Screen-pass by board</h2><ul>{board_cells or '<li>No data</li>'}</ul></section>
<section><h2>Time-to-rejection</h2><ul>{hist_cells or '<li>No data</li>'}</ul></section>
<section><h2>Rejection rate by ATS</h2><ul>{ats_cells or '<li>No data</li>'}</ul></section>
</div>
</body></html>"""
        return HTMLResponse(html)

    return app


def render_dashboard_html(store: Optional[TrackingStore] = None) -> str:
    """Offline HTML snapshot for tests / CLI without running uvicorn."""
    store = store or TrackingStore()
    funnel = store.funnel_counts()
    feed = store.feed(limit=10)
    spr = store.screen_pass_rate()
    return (
        f"<html><body><h1>NaukariPro Tracking</h1>"
        f"<pre>funnel={funnel}</pre>"
        f"<pre>screen_pass={spr}</pre>"
        f"<pre>feed_n={len(feed)}</pre></body></html>"
    )
