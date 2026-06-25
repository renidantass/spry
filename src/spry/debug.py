from __future__ import annotations

import traceback as tb_module
from html import escape

from spry.http import Request


def render_debug_page(exception: Exception, request: Request) -> str:
    tb_lines = tb_module.format_exception(type(exception), exception, exception.__traceback__)
    tb_text = "".join(tb_lines)

    frames = []
    tb = exception.__traceback__
    while tb:
        frame = tb.tb_frame
        locals_snapshot = {
            k: repr(v)[:200] for k, v in frame.f_locals.items()
            if not k.startswith("_")
        }
        frames.append({
            "file": frame.f_code.co_filename,
            "line": tb.tb_lineno,
            "function": frame.f_code.co_name,
            "locals": locals_snapshot,
        })
        tb = tb.tb_next

    def esc(s: str) -> str:
        return escape(s)

    def highlight_tb(text: str) -> str:
        text = esc(text)
        text = text.replace("  File ", '<span class="dt-file">  File </span>')
        text = text.replace('File "<span class="dt-file">', 'File "<span class="dt-file">')
        import re
        text = re.sub(r'"(.*?)", line (\d+)', r'"<span class="dt-path">\1</span>", line <span class="dt-num">\2</span>', text)
        return text

    frames_html = ""
    for i, f in enumerate(frames):
        vars_html = "".join(
            f'<span class="dv-key">{esc(k)}</span> = <span class="dv-val">{esc(v)}</span><br/>'
            for k, v in f["locals"].items()
        )
        frames_html += f"""
        <details class="df" {" open" if i == 0 else ""}>
            <summary class="df-hd">
                <span class="df-file">{esc(f['file'])}</span>:
                <span class="df-fn">{esc(f['function'])}</span>
                line <span class="df-ln">{f['line']}</span>
            </summary>
            <div class="df-bd">{vars_html}</div>
        </details>"""

    request_html = f"""
    <table class="dt-table">
        <tr><td class="dt-label">Method</td><td>{esc(request.method)}</td></tr>
        <tr><td class="dt-label">Path</td><td>{esc(request.path)}</td></tr>
        <tr><td class="dt-label">Scheme</td><td>{esc(request.scheme)}</td></tr>
        <tr><td class="dt-label">Host</td><td>{esc(request.host)}</td></tr>
        <tr><td class="dt-label">Query</td><td>{esc(str(request.query))}</td></tr>
    </table>
    <details class="df">
        <summary class="df-hd">Headers ({len(request.headers)})</summary>
        <div class="df-bd">
            {"".join(f'<span class="dv-key">{esc(k)}</span>: {esc(v)}<br/>' for k, v in sorted(request.headers.items()))}
        </div>
    </details>
    <details class="df">
        <summary class="df-hd">Body</summary>
        <div class="df-bd"><pre class="dt-pre">{esc(request.text()[:2000])}</pre></div>
    </details>
    <details class="df">
        <summary class="df-hd">Cookies ({len(request.cookies)})</summary>
        <div class="df-bd">
            {"".join(f'<span class="dv-key">{esc(k)}</span>: {esc(v)}<br/>' for k, v in request.cookies.items())}
        </div>
    </details>
    """

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>{esc(type(exception).__name__)} — Spry Debug</title>
<style>
:root {{
    --bg: #0b0d14; --bg2: #11131f; --bg3: #181b2a; --bg4: #202336;
    --tx: #e1e4f0; --tx2: #8b8fa8; --tx3: #5c6080;
    --ac: #79f2c0; --bl: #8ea8ff; --rd: #ff6b6b; --yl: #ffd93d;
    --ff: 'Inter', system-ui, sans-serif; --fm: 'JetBrains Mono', monospace;
    --r: 8px;
}}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ font-family: var(--ff); background: var(--bg); color: var(--tx); line-height: 1.6; padding: 24px; }}
h1 {{ font-size: 28px; color: var(--rd); margin-bottom: 8px; }}
h2 {{ font-size: 18px; color: var(--bl); margin: 24px 0 12px; }}
.dt-exc {{ color: var(--rd); font-size: 14px; margin-bottom: 24px; font-family: var(--fm); white-space: pre-wrap; }}
.dt-file {{ color: var(--tx3) !important; }}
.dt-path {{ color: var(--bl); }}
.dt-num {{ color: var(--yl); }}
.df {{ background: var(--bg3); border: 1px solid var(--bg4); border-radius: var(--r); margin-bottom: 8px; }}
.df-hd {{ padding: 10px 14px; cursor: pointer; font-size: 13px; user-select: none; }}
.df-hd:hover {{ background: var(--bg4); }}
.df-file {{ color: var(--tx2); }}
.df-fn {{ color: var(--ac); font-weight: 600; }}
.df-ln {{ color: var(--yl); }}
.df-bd {{ padding: 10px 14px; border-top: 1px solid var(--bg4); font-family: var(--fm); font-size: 12px; line-height: 1.5; }}
.dv-key {{ color: var(--bl); }}
.dv-val {{ color: var(--tx2); }}
.dt-table {{ width: 100%; border-collapse: collapse; margin-bottom: 12px; }}
.dt-table td {{ padding: 6px 10px; border-bottom: 1px solid var(--bg4); font-size: 13px; }}
.dt-label {{ color: var(--tx3); width: 100px; }}
.dt-pre {{ font-family: var(--fm); font-size: 12px; white-space: pre-wrap; word-break: break-all; color: var(--tx2); }}
.ftr {{ margin-top: 24px; color: var(--tx3); font-size: 12px; }}
</style>
</head>
<body>
<h1>{esc(type(exception).__name__)}</h1>
<div class="dt-exc">{highlight_tb(tb_text)}</div>

<h2>Request</h2>
{request_html}

<h2>Traceback</h2>
{frames_html}

<div class="ftr">Spry Debug Mode — {esc(type(exception).__name__)}: {esc(str(exception)[:200])}</div>
</body>
</html>"""
