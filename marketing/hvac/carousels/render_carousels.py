#!/usr/bin/env python3
"""Render carousel slide PNGs (1080x1350) from specs/*.json using headless Chromium.

Usage: python3 render_carousels.py [C01 C02 ...]   (no args = all specs)
Output: <this dir>/<ID>/slide-N.png
"""
import json, os, subprocess, sys, tempfile, html

BASE = os.path.dirname(os.path.abspath(__file__))
CHROMIUM = "/opt/pw-browsers/chromium"
NAVY, NAVY2, ORANGE, WHITE = "#0d1b2a", "#13253a", "#ff6b35", "#ffffff"

CSS = f"""
* {{ margin:0; padding:0; box-sizing:border-box; }}
html {{ background:{NAVY}; }}
body {{ width:1080px; height:1350px; overflow:hidden; position:relative;
  background: radial-gradient(120% 90% at 20% 0%, {NAVY2} 0%, {NAVY} 60%);
  font-family:'Archivo', sans-serif; color:{WHITE}; }}
.pad {{ position:absolute; inset:0; padding:90px 84px; display:flex; flex-direction:column; }}
.badge {{ display:inline-block; background:{ORANGE}; color:{NAVY}; font-family:'Archivo Black';
  font-size:40px; letter-spacing:2px; padding:14px 30px; border-radius:12px; }}
.pagenum {{ position:absolute; top:98px; right:84px; font-size:34px; font-weight:600; color:rgba(255,255,255,.45); }}
.stat {{ font-family:'Archivo Black'; color:{ORANGE}; font-size:230px; line-height:.95; margin:36px 0 10px;
  letter-spacing:-4px; word-break:break-word; }}
.stat.long {{ font-size:150px; letter-spacing:-2px; }}
h1 {{ font-family:'Archivo Black'; font-size:84px; line-height:1.04; margin:28px 0 34px; text-wrap:balance; }}
h1.hook {{ font-size:108px; margin-top:40px; }}
.body {{ font-size:44px; line-height:1.42; font-weight:400; color:rgba(255,255,255,.88); max-width:880px; }}
.body.compact {{ font-size:33px; line-height:1.5; max-width:920px; }}
.body.compact .hl {{ color:{ORANGE}; font-weight:700; }}
.body b, .body strong {{ color:{ORANGE}; font-weight:700; }}
.icon {{ position:absolute; bottom:250px; right:70px; font-size:170px; opacity:.9;
  font-family:'Noto Color Emoji', sans-serif;
  filter: drop-shadow(0 12px 30px rgba(0,0,0,.45)); }}
.footer {{ position:absolute; left:84px; right:84px; bottom:150px; border-top:3px solid rgba(255,107,53,.55);
  padding-top:26px; font-size:31px; font-weight:600; color:rgba(255,255,255,.62); }}
.brand {{ position:absolute; left:84px; bottom:70px; font-size:30px; font-weight:700; letter-spacing:1px;
  color:rgba(255,255,255,.5); }}
.swipe {{ position:absolute; right:84px; bottom:64px; font-family:'Archivo Black'; font-size:36px; color:{ORANGE}; }}
.accentbar {{ width:150px; height:14px; background:{ORANGE}; border-radius:7px; margin-bottom:44px; }}
.spacer {{ flex:1; }}
"""

def esc(s):
    return html.escape(s or "")

def slide_html(s, idx, total, carousel_title):
    role = s.get("role", "content")
    badge = s.get("badge"); stat = s.get("stat"); footer = s.get("footer"); icon = s.get("icon")
    parts = [f"<div class='pagenum'>{idx}/{total}</div>", "<div class='pad'>"]
    if role == "hook":
        parts.append("<div class='accentbar' style='margin-top:30px'></div>")
        parts.append(f"<h1 class='hook'>{esc(s['headline'])}</h1>")
        parts.append(f"<div class='body'>{esc(s['body'])}</div>")
        if icon: parts.append(f"</div><div class='icon'>{icon}</div><div class='pad' style='pointer-events:none'>")
        parts.append("<div class='spacer'></div>")
        swipe = "<div class='swipe'>SWIPE &#10145;</div>"
    else:
        if badge: parts.append(f"<div><span class='badge'>{esc(badge)}</span></div>")
        else: parts.append("<div class='accentbar' style='margin-top:10px'></div>")
        if stat:
            cls = "stat long" if len(stat) > 5 else "stat"
            parts.append(f"<div class='{cls}'>{esc(stat)}</div>")
        compact = s.get("compact")
        hstyle = " style='font-size:64px'" if compact else ""
        parts.append(f"<h1{hstyle}>{esc(s['headline'])}</h1>")
        body = esc(s['body']).replace("\n", "<br>")
        if compact:
            import re as _re
            body = _re.sub(r"\[\[(.*?)\]\]", r"<span class='hl'>\1</span>", body)
        parts.append(f"<div class='body{' compact' if compact else ''}'>{body}</div>")
        if icon and not compact: parts.append(f"</div><div class='icon'>{icon}</div><div class='pad' style='pointer-events:none'>")
        parts.append("<div class='spacer'></div>")
        swipe = "<div class='swipe'>SWIPE &#10145;</div>" if idx < total else ""
    parts.append("</div>")
    if footer: parts.append(f"<div class='footer'>{esc(footer)}</div>")
    parts.append("<div class='brand'>ClearFrequency.ai</div>")
    parts.append(swipe)
    return ("<!doctype html><html><head><meta charset='utf-8'>"
            f"<style>{CSS}</style></head><body>{''.join(parts)}</body></html>")

def render(spec_path):
    spec = json.load(open(spec_path))
    cid = spec["id"]; slides = spec["slides"]; total = len(slides)
    outdir = os.path.join(BASE, cid); os.makedirs(outdir, exist_ok=True)
    for i, s in enumerate(slides, 1):
        with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False) as f:
            f.write(slide_html(s, i, total, spec["title"])); tmp = f.name
        out = os.path.join(outdir, f"slide-{i}.png")
        subprocess.run([CHROMIUM, "--headless=new", "--no-sandbox", "--disable-gpu",
                        "--force-device-scale-factor=1", "--hide-scrollbars",
                        f"--screenshot={out}", "--window-size=1080,1400", f"file://{tmp}"],
                       check=True, capture_output=True)
        os.unlink(tmp)
        from PIL import Image
        img = Image.open(out)
        if img.size != (1080, 1350):
            img.crop((0, 0, 1080, 1350)).save(out)
    print(f"{cid}: {total} slides -> {outdir}")

if __name__ == "__main__":
    specdir = os.path.join(BASE, "specs")
    ids = sys.argv[1:] or sorted(f[:-5] for f in os.listdir(specdir) if f.endswith(".json"))
    for cid in ids:
        render(os.path.join(specdir, f"{cid}.json"))
