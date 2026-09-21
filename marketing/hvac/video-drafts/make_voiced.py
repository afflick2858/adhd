#!/usr/bin/env python3
"""Render a branded caption-card video from a spec JSON, optionally muxing a voiceover.

Usage: python3 make_voiced.py <spec.json>

Spec format:
{
  "id": "V04",
  "audio": "/abs/path/to/vo.mp3" | null,          # null = sound-off version
  "audio_end": 41.2,                               # end of speech in the audio (sec); required when audio set
  "starts": [0, 5.1, ...],                         # card start times synced to the audio (voiced mode)
  "durs": [3.0, 2.5, ...],                         # per-card durations (sound-off mode; used when audio is null)
  "cards": [["KICKER or empty", "headline html (<span class='o'>orange</span> allowed)", "sub line or empty"], ...]
}
Voiced output: <id>-voiced.mp4 · Sound-off output: <id>-soundoff.mp4 (1080x1920, 30fps)
"""
import json, os, subprocess, sys, tempfile
import imageio_ffmpeg
from PIL import Image

FF = imageio_ffmpeg.get_ffmpeg_exe()
CHROMIUM = "/opt/pw-browsers/chromium"
OUTDIR = os.path.dirname(os.path.abspath(__file__))
LEAD = 0.12
HOLD = 2.4

CSS = """
*{margin:0;padding:0;box-sizing:border-box} html{background:#0d1b2a}
body{width:1080px;height:1920px;overflow:hidden;position:relative;color:#fff;
 background:radial-gradient(120% 80% at 20% 0%,#13253a 0%,#0d1b2a 60%);
 font-family:'Archivo',sans-serif;display:flex;flex-direction:column;justify-content:center;padding:90px}
.k{display:inline-block;background:#ff6b35;color:#0d1b2a;font-family:'Archivo Black';font-size:54px;
 letter-spacing:3px;padding:16px 38px;border-radius:14px;margin-bottom:56px;align-self:flex-start}
h1{font-family:'Archivo Black';font-size:112px;line-height:1.06;letter-spacing:-2px;text-wrap:balance}
h1 .o{color:#ff6b35} .sub{font-size:52px;font-weight:600;color:rgba(255,255,255,.75);margin-top:52px}
.brand{position:absolute;bottom:84px;left:90px;font-size:34px;font-weight:700;color:rgba(255,255,255,.45)}
.bar{width:170px;height:16px;background:#ff6b35;border-radius:8px;margin-bottom:58px}
.prog{position:absolute;top:0;left:0;height:14px;background:#ff6b35}
"""

def main(spec_path):
    spec = json.load(open(spec_path))
    vid = spec["id"]; cards = spec["cards"]
    voiced = bool(spec.get("audio"))
    if voiced:
        starts = spec["starts"]
        assert len(starts) == len(cards), f"{vid}: {len(starts)} starts vs {len(cards)} cards"
        starts = [starts[0]] + [s - LEAD for s in starts[1:]]
        total = spec["audio_end"] + HOLD
        ends = starts[1:] + [total]
    else:
        durs = spec["durs"]
        assert len(durs) == len(cards)
        starts, t = [], 0.0
        for d in durs: starts.append(t); t += d
        total = t; ends = starts[1:] + [total]

    tmp = tempfile.mkdtemp()
    lines = []
    for i, ((kick, big, sub), st, en) in enumerate(zip(cards, starts, ends), 1):
        pw = int(1080 * st / total)
        top = f"<div class='k'>{kick}</div>" if kick else "<div class='bar'></div>"
        subhtml = f"<div class='sub'>{sub}</div>" if sub else ""
        html = (f"<!doctype html><html><head><meta charset='utf-8'><style>{CSS}</style></head><body>"
                f"<div class='prog' style='width:{pw}px'></div>{top}<h1>{big}</h1>"
                f"{subhtml}<div class='brand'>ClearFrequency.ai</div></body></html>")
        hp = os.path.join(tmp, f"c{i}.html"); open(hp, "w").write(html)
        png = os.path.join(tmp, f"c{i}.png")
        subprocess.run([CHROMIUM, "--headless=new", "--no-sandbox", "--disable-gpu",
                        "--force-device-scale-factor=1", "--hide-scrollbars",
                        f"--screenshot={png}", "--window-size=1080,1990", f"file://{hp}"],
                       check=True, capture_output=True)
        im = Image.open(png)
        if im.size != (1080, 1920): im.crop((0, 0, 1080, 1920)).save(png)
        lines += [f"file '{png}'", f"duration {en-st:.3f}"]
    lines.append(f"file '{tmp}/c{len(cards)}.png'")
    cf = os.path.join(tmp, "concat.txt"); open(cf, "w").write("\n".join(lines))

    suffix = "voiced" if voiced else "soundoff"
    out = os.path.join(OUTDIR, f"{vid}-{suffix}.mp4")
    cmd = [FF, "-y", "-f", "concat", "-safe", "0", "-i", cf]
    if voiced:
        cmd += ["-i", spec["audio"], "-af", "apad", "-c:a", "aac", "-b:a", "160k"]
    cmd += ["-vf", "fps=30,format=yuv420p", "-c:v", "libx264", "-preset", "medium", "-crf", "21",
            "-t", f"{total:.2f}", out]
    subprocess.run(cmd, check=True, capture_output=True)
    print(out, f"{total:.1f}s", os.path.getsize(out) // 1024, "KB")

if __name__ == "__main__":
    main(sys.argv[1])
