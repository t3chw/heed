"""Builds the static index.html (and restyles privacy.html) from the numbers below. No dependencies.

    python3 _src/build.py

Every number comes from the Heed research log (heed-research, EXP-063 search, EXP-064 task quality).
Task quality is the EXP-064 sealed test: 617 notes, used once, Heed's int8 model on a OnePlus phone (Step 75, D180).
"""
import html
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAY = "https://play.google.com/store/apps/details?id=com.heedapp.android&amp;hl=en"

# ---------------------------------------------------------------- numbers
EVAL_SET = "617 sealed test notes never used for training or tuning, 126 of them real; Heed ran on a real phone"
# judged task quality (F1, 0-100), all notes and real notes; Gemini 3.1 Pro, blind
TASKS = [
    # name, where it runs, all notes, real notes, is_heed
    ("Claude Sonnet 5.5", "Cloud · Heed's teacher", 94.8, 95.1, False),
    ("Gemini 3.5 Flash", "Cloud", 91.8, 94.2, False),
    ("Claude Haiku 5.5", "Cloud", 85.6, 92.0, False),
    ("Heed (Qwen3 0.6B)", "On your phone · offline", 75.6, 80.1, True),
    ("GPT-5.4 mini", "Cloud", 55.5, 75.3, False),
]
# second judge, GPT-5.4, same 100 notes
CHECK = [("Claude Sonnet 5.5", 85.9), ("Gemini 3.5 Flash", 82.8), ("Claude Haiku 5.5", 81.0), ("Heed", 74.0), ("GPT-5.4 mini", 63.7)]
LENGTH = {  # judged quality by note length (words)
    "bins": ["under 15", "15–39", "40–99", "100+"],
    "Heed": [81.9, 82.9, 70.5, 78.3],
    "Claude Haiku 5.5": [88.0, 93.0, 82.6, 85.9],
    "Claude Sonnet 5.5": [91.7, 96.1, 95.2, 93.7],
}
# search: nDCG@10 on held-out users vs median search time on the phone (ms); OnePlus CPH2717
SEARCH = [
    ("Keywords only (BM25)", 0.5, 0.461, False, "right"),
    ("Keywords + tiny static vectors", 1.7, 0.584, False, "right"),
    ("Keywords + MiniLM", 4.9, 0.622, False, "left"),
    ("EmbeddingGemma alone", 24.5, 0.648, False, "left"),
    ("Heed: keywords + EmbeddingGemma + dates", 26.8, 0.689, True, "left"),
    ("Heed + a re-ranking model", 340.9, 0.649, False, "left"),
]
KINDS = [  # nDCG@10 by kind of search, keywords only -> Heed
    ("Same meaning, other words", 0.327, 0.788),
    ("Vague (“that thing about the car”)", 0.421, 0.816),
    ("By feeling", 0.389, 0.768),
    ("By time (“last week”)", 0.039, 0.528),
    ("Exact words", 0.881, 0.912),
    ("By priority (“urgent”)", 0.185, 0.248),
]


def esc(s):
    return html.escape(s, quote=True)


# ---------------------------------------------------------------- charts (inline SVG, colours by role)
def bars_tasks():
    W, L, R, top, bh, gap = 680, 200, 64, 8, 30, 18
    x = lambda v: L + (W - L - R) * v / 100
    out = []
    for i, (n, where, v, _, me) in enumerate(TASKS):
        y = top + i * (bh + gap)
        cls = "m-heed" if me else "m-base"
        out.append(f'<g class="hit" data-tip="{esc(n)}: {v:.1f} · {esc(where)}">'
                   f'<rect x="{L - 190}" y="{y - 4}" width="{W - L + 190}" height="{bh + 8}" fill="transparent"/>'
                   f'<text x="{L - 12}" y="{y + 13}" class="t-lab{" t-strong" if me else ""}" text-anchor="end">{esc(n)}</text>'
                   f'<text x="{L - 12}" y="{y + 27}" class="t-sub" text-anchor="end">{esc(where)}</text>'
                   f'<path class="{cls}" d="{bar(L, y + 2, x(v) - L, bh - 4)}"/>'
                   f'<text x="{x(v) + 8}" y="{y + bh / 2 + 5}" class="t-val{" t-strong" if me else ""}">{v:.1f}</text></g>')
    h = top + len(TASKS) * (bh + gap)
    grid = "".join(f'<line x1="{x(t)}" x2="{x(t)}" y1="0" y2="{h - gap + 4}" class="grid"/>'
                   f'<text x="{x(t)}" y="{h + 10}" class="t-axis" text-anchor="middle">{t}</text>' for t in (0, 25, 50, 75, 100))
    return svg(W, h + 16, grid + "".join(out), "Judged task quality by system, out of 100")


def bar(x, y, w, h, r=4):
    """Bar anchored square on the baseline, rounded at the data end."""
    r = min(r, w / 2, h / 2)
    return f"M{x},{y} H{x + w - r} Q{x + w},{y} {x + w},{y + r} V{y + h - r} Q{x + w},{y + h} {x + w - r},{y + h} H{x} Z"


def dots_real():
    W, L, R, top, rh = 680, 200, 40, 30, 38
    lo, hi = 50, 100
    x = lambda v: L + (W - L - R) * (v - lo) / (hi - lo)
    out = []
    for i, (n, _, a, r, me) in enumerate(TASKS):
        y = top + i * rh
        c = "s-heed" if me else "s-base"
        out.append(f'<g class="hit" data-tip="{esc(n)}: {a:.1f} on all notes, {r:.1f} on real voice notes">'
                   f'<rect x="0" y="{y - 14}" width="{W}" height="28" fill="transparent"/>'
                   f'<text x="{L - 12}" y="{y + 5}" class="t-lab{" t-strong" if me else ""}" text-anchor="end">{esc(n.split(" (")[0])}</text>'
                   f'<line x1="{x(a)}" x2="{x(r)}" y1="{y}" y2="{y}" class="link {c}"/>'
                   f'<circle cx="{x(a)}" cy="{y}" r="6" class="dot-open {c}"/>'
                   f'<circle cx="{x(r)}" cy="{y}" r="6.5" class="dot {c}"/></g>')
    h = top + len(TASKS) * rh
    grid = "".join(f'<line x1="{x(t)}" x2="{x(t)}" y1="{top - 18}" y2="{h - rh + 14}" class="grid"/>'
                   f'<text x="{x(t)}" y="{h - rh + 32}" class="t-axis" text-anchor="middle">{t}</text>' for t in range(lo, hi + 1, 10))
    legend = (f'<circle cx="{L}" cy="8" r="5.5" class="dot-open s-base"/><text x="{L + 12}" y="12" class="t-sub">All 617 notes</text>'
              f'<circle cx="{L + 130}" cy="8" r="6" class="dot s-base"/><text x="{L + 142}" y="12" class="t-sub">The 126 real voice notes</text>')
    return svg(W, h - rh + 40, legend + grid + "".join(out), "Quality on all notes and on real voice notes")


def lines_length():
    W, H, L, R, T, B = 680, 300, 80, 150, 16, 40
    lo, hi = 70, 100
    xs = [L + (W - L - R) * i / (len(LENGTH["bins"]) - 1) for i in range(len(LENGTH["bins"]))]
    y = lambda v: T + (H - T - B) * (hi - v) / (hi - lo)
    g = "".join(f'<line x1="{L}" x2="{W - R}" y1="{y(t)}" y2="{y(t)}" class="grid"/><text x="{L - 8}" y="{y(t) + 4}" class="t-axis" text-anchor="end">{t}</text>' for t in range(lo, hi + 1, 10))
    g += "".join(f'<text x="{xx}" y="{H - B + 22}" class="t-axis" text-anchor="middle">{esc(b)} words</text>' for xx, b in zip(xs, LENGTH["bins"]))
    out = []
    for k, cls in (("Claude Sonnet 5.5", "s-3"), ("Claude Haiku 5.5", "s-2"), ("Heed", "s-heed")):
        v = LENGTH[k]
        d = " ".join(f"{'M' if i == 0 else 'L'}{xx:.1f},{y(val):.1f}" for i, (xx, val) in enumerate(zip(xs, v)))
        out.append(f'<path d="{d}" class="line {cls}"/>')
        out += [f'<g class="hit" data-tip="{esc(k)}, {esc(b)} words: {val:.1f}"><circle cx="{xx}" cy="{y(val)}" r="12" fill="transparent"/><circle cx="{xx}" cy="{y(val)}" r="4.5" class="dot ring {cls}"/></g>'
                for xx, val, b in zip(xs, v, LENGTH["bins"])]
        out.append(f'<text x="{xs[-1] + 12}" y="{y(v[-1]) + 4}" class="t-lab{" t-strong" if k == "Heed" else ""}">{esc(k)}</text>')
    return svg(W, H, g + "".join(out), "Judged quality by note length")


def scatter_search():
    W, H, L, R, T, B = 680, 340, 52, 24, 20, 48
    lx0, lx1, lo, hi = math.log10(0.3), math.log10(600), 0.40, 0.72
    x = lambda ms: L + (W - L - R) * (math.log10(ms) - lx0) / (lx1 - lx0)
    y = lambda v: T + (H - T - B) * (hi - v) / (hi - lo)
    g = "".join(f'<line x1="{L}" x2="{W - R}" y1="{y(t)}" y2="{y(t)}" class="grid"/><text x="{L - 8}" y="{y(t) + 4}" class="t-axis" text-anchor="end">{t:.1f}</text>' for t in (0.4, 0.5, 0.6, 0.7))
    g += "".join(f'<line x1="{x(t)}" x2="{x(t)}" y1="{T}" y2="{H - B}" class="grid"/><text x="{x(t)}" y="{H - B + 18}" class="t-axis" text-anchor="middle">{t:g} ms</text>' for t in (1, 10, 100))
    g += f'<rect x="{x(0.3)}" y="{T}" width="{x(100) - x(0.3)}" height="{H - T - B}" class="zone"/><text x="{x(100) - 6}" y="{H - B - 8}" class="t-sub" text-anchor="end">feels instant (under 100 ms)</text>'
    g += f'<text x="{(L + W - R) / 2}" y="{H - 6}" class="t-sub" text-anchor="middle">Time per search on a mid-range phone (log scale)</text>'
    out = []
    for n, ms, v, me, side in SEARCH:
        c = "s-heed" if me else "s-base"
        tx, anchor = (x(ms) - 12, "end") if side == "left" else (x(ms) + 12, "start")
        out.append(f'<g class="hit" data-tip="{esc(n)}: quality {v:.3f}, {ms:g} ms">'
                   f'<circle cx="{x(ms)}" cy="{y(v)}" r="14" fill="transparent"/>'
                   f'<circle cx="{x(ms)}" cy="{y(v)}" r="{8 if me else 6}" class="dot ring {c}"/>'
                   f'<text x="{tx}" y="{y(v) + 4}" class="t-lab{" t-strong" if me else ""}" text-anchor="{anchor}">{esc(n)}</text></g>')
    return svg(W, H, g + "".join(out), "Search quality against time per search")


def bars_kinds():
    W, L, R, top, gh = 680, 250, 56, 30, 46
    x = lambda v: L + (W - L - R) * v
    out = [f'<rect x="{L}" y="2" width="12" height="10" rx="2" class="m-base"/><text x="{L + 18}" y="11" class="t-sub">Keywords only</text>'
           f'<rect x="{L + 130}" y="2" width="12" height="10" rx="2" class="m-heed"/><text x="{L + 148}" y="11" class="t-sub">Heed</text>']
    for i, (n, a, b) in enumerate(KINDS):
        y = top + i * gh
        out.append(f'<g class="hit" data-tip="{esc(n)}: {a:.2f} → {b:.2f}">'
                   f'<rect x="0" y="{y - 6}" width="{W}" height="{gh - 6}" fill="transparent"/>'
                   f'<text x="{L - 12}" y="{y + 15}" class="t-lab" text-anchor="end">{esc(n)}</text>'
                   f'<path class="m-base" d="{bar(L, y, max(2, x(a) - L), 14)}"/>'
                   f'<path class="m-heed" d="{bar(L, y + 16, x(b) - L, 14)}"/>'
                   f'<text x="{max(x(a), L + 2) + 6}" y="{y + 11}" class="t-val-s">{a:.2f}</text>'
                   f'<text x="{x(b) + 6}" y="{y + 27}" class="t-val-s t-strong">{b:.2f}</text></g>')
    h = top + len(KINDS) * gh
    grid = "".join(f'<line x1="{x(t)}" x2="{x(t)}" y1="{top - 6}" y2="{h - 10}" class="grid"/><text x="{x(t)}" y="{h + 6}" class="t-axis" text-anchor="middle">{t:.2f}</text>' for t in (0, .25, .5, .75, 1))
    return svg(W, h + 12, grid + "".join(out), "Search quality by kind of search")


def svg(w, h, body, label):
    return f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="{esc(label)}" class="chart">{body}</svg>'


def table(head, rows):
    th = "".join(f"<th>{esc(h)}</th>" for h in head)
    tr = "".join("<tr>" + "".join(f"<td>{esc(str(c))}</td>" for c in r) + "</tr>" for r in rows)
    return f'<details class="numbers"><summary>Show the numbers</summary><div class="tscroll"><table><thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table></div></details>'


PLAY_ICON = '<svg width="22" height="22" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M3.6 2.2 13.4 12l-9.8 9.8c-.4-.2-.6-.6-.6-1.1V3.3c0-.5.2-.9.6-1.1zm11 11 2.5 2.5-11 6.3 8.5-8.8zm3.7-3.7 2.9 1.7c.8.5.8 1.2 0 1.7l-2.9 1.7-2.8-2.6 2.8-2.5zM6.1 1.9l11 6.3-2.5 2.5-8.5-8.8z"/></svg>'

# ---------------------------------------------------------------- page
A = ROOT / "_src/assets"


def asset(name):
    return (A / f"{name}.html").read_text(encoding="utf-8")


# The app screens were captured from the old warm design; this maps them to the new palette.
RECOLOR = [
    ("rgba(217, 119, 87, 0.18)", "#FBECDD"),          # Buy bucket
    ("rgba(217, 119, 87,", "rgba(47, 138, 76,"),      # accent glows
    ("#D97757", "#2F8A4C"), ("rgb(185, 90, 61)", "#B4561B"),
    ("rgb(255, 249, 240)", "#FFFFFF"), ("#FFF9F0", "#FFFFFF"), ("rgba(255, 249, 240,", "rgba(255, 255, 255,"),
    ("rgba(42, 36, 32,", "rgba(25, 25, 25,"), ("rgb(42, 36, 32)", "#191919"),
    ("rgba(232, 200, 156, 0.4)", "#EAF5EC"), ("rgba(232, 200, 156, 0.25)", "#F1F1EF"),
    ("rgba(160, 178, 162, 0.3)", "rgba(47, 138, 76, 0.13)"), ("rgb(94, 119, 84)", "#2F8A4C"), ("#5E7754", "#2F8A4C"),
    ("rgba(180, 170, 158, 0.55)", "rgba(150, 150, 150, 0.55)"), ("rgba(120, 108, 94, 0.55)", "rgba(70, 70, 70, 0.5)"),
]


def screen(name):
    s = asset(name)
    for a, b in RECOLOR:
        s = s.replace(a, b)
    return s


def mascot(name, w):
    """A captured Skein mascot, resized. The captures are 5:6 (width:height)."""
    s = asset(name)
    h = round(w * 1.2)
    s = re.sub(r'style="width: [\d.]+px; height: [\d.]+px;"', f'style="width:{w}px;height:{h}px"', s, count=1)
    s = re.sub(r'width="[\d.]+" height="[\d.]+"', f'width="{w}" height="{h}"', s, count=1)
    return s


def sparkle(x, y, size, color, delay=0):
    return (f'<svg class="spark" style="left:{x};top:{y};width:{size}px;height:{size}px;animation-delay:{delay}s" viewBox="0 0 24 24" aria-hidden="true">'
            f'<path d="M12 0 C13 8 16 11 24 12 C16 13 13 16 12 24 C11 16 8 13 0 12 C8 11 11 8 12 0Z" fill="{color}"/></svg>')


CSS = r"""
:root{--bg:#FFFFFF;--soft:#F7F7F5;--soft-2:#F1F1EF;--ink:#191919;--ink-2:#37352F;--ink-3:#787774;--line:#E9E9E7;
--brand:#2F8A4C;--brand-soft:#EAF5EC;--hl:#FFF0A8;--hl-2:#DDF2E2;
--c-heed:#3E9B57;--c-2:#2a78d6;--c-3:#eb6834;--c-base:#D3D1CB;--zone:rgba(62,155,87,.07);
--t-orange:#FBECDD;--t-orange-i:#B4561B;--t-purple:#EFE7F7;--t-purple-i:#6940A5;--t-gray:#EEEEEC;--t-gray-i:#55534E;--t-yellow:#FBF3DB;--t-yellow-i:#8A6A0E;--t-blue:#E7F0FB;--t-blue-i:#1F5DAE;
--leaf:#9FC28F;--leaf-dark:#6F9764;--leaf-light:#B9D4AC;--pot:#C97A55;--pot-shade:#A65F3E;--soil:#3A2618;--bulb:#A8CF97;--bulb-shade:#7FA76F;--blush:#E9A9A0;
--ui:"Inter",system-ui,-apple-system,"Segoe UI",sans-serif;--mono:"JetBrains Mono",ui-monospace,Menlo,monospace;color-scheme:light}
*{box-sizing:border-box}html{scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--ink-2);font:16.5px/1.6 var(--ui);-webkit-font-smoothing:antialiased}
a{color:var(--ink);text-decoration:underline;text-decoration-color:var(--line);text-underline-offset:3px}a:hover{text-decoration-color:var(--ink)}
.wrap{max-width:1080px;margin:0 auto;padding-left:max(20px,env(safe-area-inset-left,0px));padding-right:max(20px,env(safe-area-inset-right,0px))}
nav{position:sticky;top:0;z-index:20;background:rgba(255,255,255,.9);backdrop-filter:blur(10px);border-bottom:1px solid var(--line)}
.nav{display:flex;align-items:center;justify-content:space-between;gap:16px;height:60px}
.brand{display:flex;align-items:center;gap:8px;color:var(--ink);font:750 19px var(--ui);letter-spacing:-.02em;text-decoration:none}
.brand .m{margin-top:-4px}
.links{display:flex;gap:24px;font-size:14.5px}.links a{color:var(--ink-3);text-decoration:none}.links a:hover{color:var(--ink)}
.btn{display:inline-flex;align-items:center;gap:8px;padding:10px 16px;border-radius:8px;font:600 15px var(--ui);background:var(--ink);color:#fff;text-decoration:none;border:1px solid var(--ink)}
.btn:hover{background:#333}.btn.ghost{background:#fff;color:var(--ink);border-color:var(--line)}.btn.ghost:hover{background:var(--soft)}.btn.sm{padding:7px 13px;font-size:14px}
mark{background:linear-gradient(transparent 52%,var(--hl) 52%,var(--hl) 92%,transparent 92%);color:inherit;padding:0 .08em}
mark.g{background:linear-gradient(transparent 52%,var(--hl-2) 52%,var(--hl-2) 92%,transparent 92%)}
h1,h2,h3{color:var(--ink);margin:0;letter-spacing:-.03em;text-wrap:balance}
h1{font-size:clamp(42px,6.4vw,72px);line-height:1.02;font-weight:800}
h2{font-size:clamp(30px,4.2vw,46px);line-height:1.08;font-weight:800}
h3{font-size:19px;line-height:1.3;font-weight:700;letter-spacing:-.015em}
.kicker{display:inline-flex;align-items:center;gap:8px;font:600 13px var(--ui);color:var(--brand);background:var(--brand-soft);padding:5px 11px;border-radius:999px}
.lede{font-size:19px;color:var(--ink-3);max-width:60ch;margin:18px 0 0;line-height:1.55}
section{padding-block:96px;border-top:1px solid var(--line)}
.hero{position:relative;padding-block:64px 72px;display:grid;grid-template-columns:1.02fr .98fr;gap:56px;align-items:center}
.actions{display:flex;gap:12px;flex-wrap:wrap;margin-top:30px;align-items:center}
.play{display:inline-flex;align-items:center;gap:12px;padding:11px 20px;border-radius:10px;background:var(--ink);color:#fff;text-decoration:none}
.play:hover{background:#333}.play small{display:block;font:500 11px var(--ui);opacity:.75;line-height:1.1}.play b{display:block;font:650 17px var(--ui);line-height:1.2}
.facts{display:flex;gap:8px;flex-wrap:wrap;margin-top:26px}
.tag{display:inline-flex;align-items:center;gap:6px;font:550 13px var(--ui);padding:3px 9px;border-radius:6px;white-space:nowrap}
.t-orange{background:var(--t-orange);color:var(--t-orange-i)}.t-purple{background:var(--t-purple);color:var(--t-purple-i)}.t-gray{background:var(--t-gray);color:var(--t-gray-i)}
.t-yellow{background:var(--t-yellow);color:var(--t-yellow-i)}.t-blue{background:var(--t-blue);color:var(--t-blue-i)}.t-green{background:var(--brand-soft);color:var(--brand)}
.stage{position:relative;padding:40px 0 0 0}
.stage .pal{position:absolute;left:-58px;top:-28px;z-index:3;filter:drop-shadow(0 10px 14px rgba(0,0,0,.08))}
.spark{position:absolute;z-index:4;animation:twinkle 2.6s ease-in-out infinite}
@keyframes twinkle{0%,100%{transform:scale(.6) rotate(0);opacity:.5}50%{transform:scale(1) rotate(25deg);opacity:1}}
.demo{position:relative;background:#fff;border:1px solid var(--line);border-radius:16px;padding:22px 22px 18px 22px;box-shadow:0 1px 2px rgba(0,0,0,.04),0 24px 48px -24px rgba(0,0,0,.18)}
.demo-h{display:flex;justify-content:space-between;align-items:center;font:500 12.5px var(--mono);color:var(--ink-3)}
.rec{display:flex;align-items:center;gap:8px}.rec i{width:8px;height:8px;border-radius:50%;background:#E5484D;display:inline-block;animation:blink 1.6s infinite}
@keyframes blink{50%{opacity:.25}}
.wave{display:flex;gap:3px;align-items:center;height:28px;margin-top:12px}.wave b{flex:1;background:var(--c-heed);opacity:.7;border-radius:2px;animation:wv 1.4s ease-in-out infinite}
@keyframes wv{50%{transform:scaleY(.35)}}
.transcript{margin:14px 0 0;padding:14px 16px;background:var(--soft);border-radius:10px;font:14.5px/1.6 var(--mono);color:var(--ink-2)}
.arrow{display:flex;align-items:center;gap:10px;margin:16px 0;font:500 12px var(--mono);color:var(--ink-3)}.arrow::before,.arrow::after{content:"";flex:1;height:1px;background:var(--line)}
.tasks{display:grid;gap:7px}.task{display:flex;align-items:center;gap:12px;padding:10px 12px;border-radius:9px;background:#fff;border:1px solid var(--line)}
.task .box{width:17px;height:17px;border:1.5px solid #C7C6C2;border-radius:4px;flex:none}.task .tx{flex:1;min-width:0;font-weight:560;color:var(--ink)}
.task{animation:pop .5s both}.task:nth-child(2){animation-delay:.12s}.task:nth-child(3){animation-delay:.24s}.task:nth-child(4){animation-delay:.36s}
@keyframes pop{from{opacity:0;transform:translateY(6px)}}
.demo-f{margin-top:14px;font:12px var(--mono);color:var(--ink-3);display:flex;justify-content:space-between;gap:10px;flex-wrap:wrap}
.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}
.stat{padding:22px;border-radius:14px;background:var(--soft)}
.stat .v{font:800 40px/1 var(--ui);letter-spacing:-.035em;color:var(--ink)}.stat .l{margin-top:10px;color:var(--ink-3);font-size:14.5px;line-height:1.45}
.stat .e{font-size:22px;float:right}
.head{max-width:740px;margin-bottom:44px}
.steps{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}
.card{border:1px solid var(--line);border-radius:14px;padding:24px;background:#fff}
.card .e{font-size:26px}.card h3{margin:12px 0 6px}.card p{margin:0;color:var(--ink-3)}
.pipe{margin-top:16px;display:grid;grid-template-columns:repeat(3,1fr);gap:16px}
.pipe>div{padding:16px 18px;border-radius:12px;background:var(--soft)}
.pipe .k{font:600 11.5px var(--mono);letter-spacing:.06em;text-transform:uppercase;color:var(--ink-3)}.pipe .m{font-weight:700;color:var(--ink);margin-top:4px}.pipe .d{font-size:14px;color:var(--ink-3)}
.phones{--cream:#FFFFFF;--ink:#191919;--ink-2:#37352F;--ink-3:#787774;--terra:#2F8A4C;--terra-deep:#23703C;
--font-display:"Inter",system-ui,sans-serif;--font-mono:"JetBrains Mono",ui-monospace,monospace;--font-ui:"Inter",system-ui,sans-serif;
display:grid;grid-template-columns:repeat(3,1fr);gap:28px;align-items:start;justify-items:center}
.phones [style*="--font-display"]{font-weight:750!important;letter-spacing:-.03em;font-style:normal!important}.phones figure{margin:0;text-align:center}.phones figcaption{margin-top:18px;color:var(--ink-3);font-size:15px;max-width:30ch}
.phones figcaption b{display:block;color:#191919;font-size:16.5px;margin-bottom:2px}
@keyframes pulse-ring{0%{transform:scale(.85);opacity:.8}100%{transform:scale(1.25);opacity:0}}
.fig{border:1px solid var(--line);border-radius:16px;padding:28px 28px 20px;margin-top:20px;background:#fff}
.fig h3{font-size:21px}.fig .cap{color:var(--ink-3);margin:6px 0 18px;max-width:72ch}
.cscroll{overflow-x:auto;-webkit-overflow-scrolling:touch}.swipe{display:none;font:500 11.5px var(--mono);color:var(--ink-3);margin:-8px 0 8px}
.chart{display:block;width:100%;min-width:560px;height:auto;font-family:var(--ui)}
.grid{stroke:var(--soft-2);stroke-width:1}.zone{fill:var(--zone)}
.t-lab{fill:var(--ink);font-size:13.5px}.t-sub{fill:var(--ink-3);font-size:11.5px}.t-axis{fill:var(--ink-3);font:11px var(--mono)}
.t-val{fill:var(--ink-2);font:600 13px var(--mono)}.t-val-s{fill:var(--ink-3);font:500 11.5px var(--mono)}.t-strong{fill:var(--ink);font-weight:700}
.m-heed{fill:var(--c-heed)}.m-base{fill:var(--c-base)}
.dot.s-heed{fill:var(--c-heed)}.dot.s-base{fill:var(--c-base)}.dot.s-2{fill:var(--c-2)}.dot.s-3{fill:var(--c-3)}
.ring{stroke:#fff;stroke-width:2}
.dot-open{fill:#fff;stroke-width:2.5}.dot-open.s-heed{stroke:var(--c-heed)}.dot-open.s-base{stroke:var(--c-base)}
.link{stroke-width:2.5}.link.s-heed{stroke:var(--c-heed)}.link.s-base{stroke:var(--c-base)}
.line{fill:none;stroke-width:2.5;stroke-linejoin:round}.line.s-heed{stroke:var(--c-heed)}.line.s-2{stroke:var(--c-2)}.line.s-3{stroke:var(--c-3)}
.hit:hover .t-lab{text-decoration:underline}
#tip{position:fixed;pointer-events:none;z-index:50;background:var(--ink);color:#fff;font:500 12.5px var(--ui);padding:7px 10px;border-radius:7px;max-width:280px;opacity:0;transition:opacity .1s}
details.numbers{margin-top:14px;font-size:14px}details.numbers summary{cursor:pointer;color:var(--ink-3);font:500 13px var(--ui)}
.tscroll{overflow-x:auto}table{border-collapse:collapse;width:100%;margin-top:10px;font-size:14px}th,td{text-align:left;padding:8px 10px;border-bottom:1px solid var(--line)}th{font-weight:600;color:var(--ink-3)}
.callout{display:flex;gap:14px;padding:18px 20px;border-radius:12px;background:var(--soft);margin-top:20px}.callout .e{font-size:22px;line-height:1.3}
.callout h4{margin:0 0 6px;color:var(--ink);font-size:16px}.callout ul{margin:0;padding-left:18px;color:var(--ink-2)}.callout li{margin:4px 0}
.judge{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-top:20px}
.judge>div{padding:20px;border:1px solid var(--line);border-radius:14px;background:#fff}.judge .n{font-size:24px}
.judge h3{font-size:16.5px;margin:10px 0 6px}.judge p{margin:0;font-size:14.5px;color:var(--ink-3)}
.checks{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-top:14px}
.check{padding:18px 20px;border-radius:14px;background:var(--brand-soft)}.check .v{font:800 28px var(--ui);letter-spacing:-.02em;color:var(--brand)}.check .l{color:var(--ink-2);font-size:14.5px;margin-top:2px}
.sub-h{font-size:28px;margin-top:64px}
.priv{display:grid;grid-template-columns:1fr 1fr;gap:48px;align-items:center}
.ticks{list-style:none;padding:0;margin:0;display:grid;gap:10px}.ticks li{display:flex;gap:12px;padding:14px 16px;border-radius:10px;background:var(--soft);color:var(--ink)}
.ticks li::before{content:"✓";color:var(--brand);font-weight:800}
.faq{display:grid;gap:8px;max-width:800px}.faq details{border-bottom:1px solid var(--line);padding:14px 4px}
.faq summary{cursor:pointer;font-weight:650;font-size:17px;color:var(--ink);list-style:none}.faq summary::-webkit-details-marker{display:none}
.faq summary::before{content:"▸";display:inline-block;width:20px;color:var(--ink-3);transition:transform .15s}.faq details[open] summary::before{transform:rotate(90deg)}
.faq p{margin:8px 0 0 20px;color:var(--ink-3)}
.cta{text-align:center;position:relative}.cta .lede{margin:16px auto 0}.cta .actions{justify-content:center}.cta .pal{display:flex;justify-content:center;margin-bottom:10px}
footer{border-top:1px solid var(--line);padding-block:32px 48px;color:var(--ink-3);font-size:14px}
.foot{display:flex;justify-content:space-between;gap:20px;flex-wrap:wrap;align-items:center}.foot div{display:flex;gap:20px;flex-wrap:wrap}.foot a{color:var(--ink-3);text-decoration:none}.foot a:hover{color:var(--ink)}
@media (max-width:900px){.hero{grid-template-columns:1fr;gap:72px}.links{display:none}.stats{grid-template-columns:1fr 1fr}
.steps,.pipe,.judge,.checks,.priv,.phones{grid-template-columns:1fr}section{padding-block:72px}.stage{padding-top:120px}.stage .pal{left:0;top:-20px}}
@media (max-width:620px){.swipe{display:block}.fig{padding:20px 16px 14px}}
@media (max-width:480px){.stats{grid-template-columns:1fr}.nav .btn{display:none}}
"""

TASK_TAG = {"Buy": "t-orange", "Watch": "t-purple", "General": "t-gray", "Ideas": "t-yellow", "Work": "t-blue"}

FAQ = [
    ("Is it really free?", "Yes, completely. No price, no subscription, no ads, no in-app purchases, no account."),
    ("Does it really run on the phone?", "Yes. Three small models ship inside the app: IBM's Granite Speech (470M) for speech, a 0.6B Qwen3 model fine-tuned for Heed for tasks, and Google's EmbeddingGemma (300M) for search. Heed has no internet permission, so Android won't let it go online. Check Settings → Apps → Heed → Permissions."),
    ("Do I need to download anything after installing?", "No. The models are part of the install, so Heed works the moment it opens, in airplane mode too. The cost is size: the download from Google Play is about 1.4 GB, and Heed then takes about 2.8 GB on your phone, because it copies the models once into its own storage."),
    ("Which phones does it run on?", "Android 10 or newer, with 6 GB of RAM or more. Heed only works while it's sorting a note: on a mid-range phone a 17-second note takes about 5 seconds. During those seconds it loads one model at a time (at most about 1.5 GB), and it frees that memory after 90 seconds of quiet. Nothing runs in the background between notes."),
    ("What if I lose my phone?", "Your notes live only on your phone. Settings → Export backup saves a file wherever you like; Restore from backup brings it all back on a new phone."),
    ("Can I add my own buckets?", "Yes. Heed starts with General, Buy, Watch, Ideas, Work and Journal. Add your own, such as Trips or Recipes, and new notes are sorted into them too. Any item can carry a reminder: tap the bell."),
    ("Which languages?", "English for now."),
]


def page():
    heed = next(t for t in TASKS if t[4])
    sonnet, mini = TASKS[0], TASKS[-1]
    pct = round(100 * heed[2] / sonnet[2])
    pct_real = round(100 * heed[3] / sonnet[3])
    srch = next(s for s in SEARCH if s[3])
    gain = round(100 * (srch[2] / SEARCH[0][2] - 1))
    chart = lambda c: f'<div class="swipe">Swipe the chart →</div><div class="cscroll">{c}</div>'
    task_rows = [(n, w, f"{a:.1f}", f"{r:.1f}") for n, w, a, r, _ in TASKS]
    tasks = [("Olive oil", "Buy"), ("Eggs", "Buy"), ("Call mom back", "General"), ("Watch Past Lives", "Watch")]
    task_html = "".join(f'<div class="task"><span class="box"></span><span class="tx">{t}</span><span class="tag {TASK_TAG[c]}">{c}</span></div>' for t, c in tasks)
    wave = "".join(f'<b style="height:{h}px;animation-delay:{i * 0.07:.2f}s"></b>' for i, h in enumerate([8, 16, 22, 12, 26, 18, 10, 24, 14, 20, 9, 17, 25, 11, 19, 7, 15, 23, 13, 21]))
    logo = mascot("logo", 26).replace('class="skein-sprout"', 'class="skein-sprout m"', 1)
    faq = "".join(f"<details{' open' if i == 0 else ''}><summary>{esc(a)}</summary><p>{esc(b)}</p></details>" for i, (a, b) in enumerate(FAQ))
    phones = "".join(f'<figure>{screen(k)}<figcaption><b>{t}</b>{d}</figcaption></figure>' for k, t, d in (
        ("phone_home", "Today, at a glance", "Today's items up top, your buckets below. The mic is one thumb away."),
        ("phone_listening", "Just talk", "Speak naturally: ramble, stop, restart. Up to a minute per note."),
        ("phone_onboarding", "Make it yours", "Theme, time format, a morning digest, and the three models doing the work.")))
    favicon = "data:image/svg+xml," + re.sub(r"\s+", " ", '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><path d="M8 18h16l-2 11H10z" fill="#C97A55" stroke="#191919" stroke-width="1.6"/><ellipse cx="16" cy="12" rx="7.5" ry="7" fill="#A8CF97" stroke="#191919" stroke-width="1.6"/><path d="M16 5c0-3 2-4 4-4-1 2-2 3-4 4z" fill="#6F9764"/><circle cx="13.4" cy="12" r="1.2" fill="#191919"/><circle cx="18.6" cy="12" r="1.2" fill="#191919"/></svg>').replace("#", "%23").replace('"', "'")
    return f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Heed — Voice notes to tasks, on your phone</title>
<meta name="description" content="Speak a messy thought; Heed turns it into tasks, buys and ideas. Speech, sorting and search run entirely on your phone, with no internet permission. Free on Android.">
<meta property="og:title" content="Heed — Voice notes to tasks, on your phone">
<meta property="og:description" content="A 0.6B model on your phone that reaches {pct}% of Claude Sonnet at turning voice notes into tasks. Free, offline, private.">
<meta property="og:type" content="website">
<link rel="icon" href="{favicon}">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Instrument+Serif:ital@0;1&family=JetBrains+Mono:wght@500;600&display=swap" rel="stylesheet">
<style>{CSS}
{asset("skein_css")}</style>
</head><body>
<nav><div class="wrap nav">
  <a href="#" class="brand">{logo}Heed</a>
  <div class="links"><a href="#how">How it works</a><a href="#app">The app</a><a href="#quality">Quality</a><a href="#search">Search</a><a href="#privacy">Privacy</a><a href="#faq">FAQ</a></div>
  <a class="btn sm" href="{PLAY}" target="_blank" rel="noopener">Get it free</a>
</div></nav>

<header class="wrap hero">
  <div>
    <span class="kicker">🌱 Voice notes → tasks, fully on-device</span>
    <h1 style="margin-top:20px">Say it once.<br><mark>Heed sorts it.</mark></h1>
    <p class="lede">Ramble a thought the way you'd say it out loud. Heed turns it into clean tasks, things to buy and ideas. Speech, sorting and search all run on your phone. Nothing is uploaded, ever.</p>
    <div class="actions">
      <a class="play" href="{PLAY}" target="_blank" rel="noopener">{PLAY_ICON}<span><small>Free on</small><b>Google Play</b></span></a>
      <a class="btn ghost" href="#quality">See how we measured it</a>
    </div>
    <div class="facts"><span class="tag t-green">Free forever</span><span class="tag t-gray">No ads · no account</span><span class="tag t-blue">Works offline</span><span class="tag t-purple">6 GB+ RAM phones</span></div>
  </div>
  <div class="stage">
    <div class="pal">{mascot("hero", 120)}</div>
    {sparkle("-70px", "100px", 18, "#F2C94C", 0)}{sparkle("40px", "-20px", 12, "#3E9B57", .8)}{sparkle("-30px", "150px", 10, "#2a78d6", 1.4)}{sparkle("96%", "18px", 16, "#F2C94C", .4)}
    <div class="demo" aria-label="Example: a voice note turned into tasks">
      <div class="demo-h"><span class="rec"><i></i>Voice note · 0:12</span><span>on-device</span></div>
      <div class="wave" aria-hidden="true">{wave}</div>
      <p class="transcript">ok so we're out of olive oil and eggs um oh and i have to call mom back and i really want to watch past lives at some point</p>
      <div class="arrow">Heed · about 5 s</div>
      <div class="tasks">{task_html}</div>
      <div class="demo-f"><span>0 bytes sent</span><span>Granite Speech → Qwen3 0.6B</span></div>
    </div>
  </div>
</header>

<div class="wrap" style="padding-bottom:88px">
  <div class="stats">
    <div class="stat"><span class="e">🎯</span><div class="v">{pct}%</div><div class="l">of Claude Sonnet's quality at turning notes into tasks, from a 0.6B model on the phone</div></div>
    <div class="stat"><span class="e">🥊</span><div class="v">+{heed[2] - mini[2]:.0f} pts</div><div class="l">ahead of GPT-5.4 mini, judged blind on the same notes</div></div>
    <div class="stat"><span class="e">🔎</span><div class="v">+{gain}%</div><div class="l">better search than keyword matching, at {srch[1]:.0f} ms a search</div></div>
    <div class="stat"><span class="e">📱</span><div class="v">~5 s</div><div class="l">of work per note. The models unload a minute or two later, and nothing runs in the background</div></div>
  </div>
</div>

<section id="how"><div class="wrap">
  <div class="head"><span class="kicker">How it works</span><h2 style="margin-top:16px">Three steps, <mark class="g">all on your phone.</mark></h2>
  <p class="lede">Tap the mic, or make Heed your phone's assistant and capture from anywhere. Up to a minute per note.</p></div>
  <div class="steps">
    <div class="card"><div class="e">🎙️</div><h3>Say it however it comes out</h3><p>Pauses, "um", changing your mind halfway: the last thing you settle on is what counts.</p></div>
    <div class="card"><div class="e">🗂️</div><h3>Clean, separate items</h3><p>One note becomes several tasks, each in the right bucket. Add a reminder to any of them with one tap.</p></div>
    <div class="card"><div class="e">🔍</div><h3>Search by meaning</h3><p>"That book Anna recommended" or "what did I say last week" finds the note, even in different words.</p></div>
  </div>
  <div class="pipe">
    <div><div class="k">Speech</div><div class="m">Granite Speech 470M</div><div class="d">Voice to text, by IBM</div></div>
    <div><div class="k">Tasks</div><div class="m">Qwen3 0.6B, fine-tuned for Heed</div><div class="d">Text to tasks and buckets</div></div>
    <div><div class="k">Search</div><div class="m">EmbeddingGemma 300M + keywords</div><div class="d">Finds notes by meaning and by date</div></div>
  </div>
</div></section>

<section id="app" style="background:var(--soft)"><div class="wrap">
  <div class="head"><span class="kicker">The app</span><h2 style="margin-top:16px">Designed to get out of the way.</h2></div>
  <div class="phones">{phones}</div>
</div></section>

<section id="quality"><div class="wrap">
  <div class="head"><span class="kicker">📊 Quality</span><h2 style="margin-top:16px">How good is a 0.6B model on a phone? <mark>We measured it.</mark></h2>
  <p class="lede">We gave the same voice notes and the same instructions to Heed and to four cloud AI models, then had an independent AI judge grade every task without knowing which system wrote it.</p></div>
  <div class="fig">
    <h3>Heed reaches {pct}% of Claude Sonnet and beats GPT-5.4 mini</h3>
    <p class="cap">Judged task quality out of 100: how many tasks the speaker could keep as written, counting both wrong items and missed ones. {esc(EVAL_SET)}.</p>
    {chart(bars_tasks())}
    {table(["System", "Runs", "All notes", "Real voice notes"], task_rows)}
  </div>
  <div class="fig">
    <h3>On real voice notes: {pct_real}% of Sonnet</h3>
    <p class="cap">On the 126 real notes Heed scores {heed[3]:.1f}, {pct_real}% of Sonnet. Every model does better on real notes, which are shorter; GPT-5.4 mini gains the most and is level with Heed there.</p>
    {chart(dots_real())}
  </div>
  <div class="fig">
    <h3>Where it still loses: rambling notes</h3>
    <p class="cap">The gap is smallest on short notes and largest on 40–99-word rambles, where a small model starts dropping details. That's what we're working on next.</p>
    {chart(lines_length())}
  </div>

  <h3 class="sub-h">How the grading works</h3>
  <div class="judge">
    <div><div class="n">🧪</div><h3>Same notes, same rules</h3><p>Cloud models got the full written rulebook; Heed learned the rules from examples. None of these notes were used in training.</p></div>
    <div><div class="n">🙈</div><h3>A blind judge</h3><p>Gemini 3.1 Pro grades each task: usable as is, needs an edit, or wrong, plus anything that was missed. No system names shown.</p></div>
    <div><div class="n">🧮</div><h3>One strict score</h3><p>A task that needs an edit counts against the system, because it costs you a tap. Wrong and missed items count too.</p></div>
    <div><div class="n">📜</div><h3>Rules written first</h3><p>"Beats" only when the 95% confidence interval stays above zero, decided before any result came in.</p></div>
  </div>
  <div class="checks">
    <div class="check"><div class="v">96%</div><div class="l">of deliberately planted mistakes caught by the judge</div></div>
    <div class="check"><div class="v">κ 0.84</div><div class="l">agreement between the judge and a person rating blind</div></div>
    <div class="check"><div class="v">Same order</div><div class="l">from a second judge, GPT-5.4: Heed {CHECK[3][1]:.1f}, GPT-5.4 mini {CHECK[4][1]:.1f}</div></div>
  </div>
  <div class="callout"><div class="e">💡</div><div><h4>The honest small print</h4><ul>
    <li>Claude Haiku 5.5 and Gemini 3.5 Flash are better (+10 and +16 points). We don't claim otherwise.</li>
    <li>Cloud models ran with their default settings; GPT-5.4 mini might do better with more reasoning.</li>
    <li>All numbers come from a sealed set of 617 notes that was used once, at the end, with the exact model file the app ships running on a mid-range phone.</li>
  </ul></div></div>
</div></section>

<section id="search"><div class="wrap">
  <div class="head"><span class="kicker">🔎 Search</span><h2 style="margin-top:16px">Search that understands, <mark class="g">timed on a real phone.</mark></h2>
  <p class="lede">We built ten test libraries of about 1,000 notes each and wrote 960 searches in 13 styles, from exact words to "that thing about the car". Every answer was graded, and every design was timed on a mid-range Android phone.</p></div>
  <div class="fig">
    <h3>{gain}% better than keywords, at {srch[1]:.0f} ms a search</h3>
    <p class="cap">Quality is nDCG@10: are the right notes near the top? Higher is better, further left is faster. A re-ranking model made results worse and searches 13× slower, so it's out.</p>
    {chart(scatter_search())}
    {table(["Design", "Time per search (ms)", "Quality (nDCG@10)"], [(n, f"{ms:g}", f"{v:.3f}") for n, ms, v, _, _ in SEARCH])}
  </div>
  <div class="fig">
    <h3>Biggest gains where keywords fail</h3>
    <p class="cap">Different words, vague searches and dates are where meaning beats matching. "Urgent" searches stay weak for every design: they need real due dates, which is next on the list.</p>
    {chart(bars_kinds())}
  </div>
</div></section>

<section id="privacy" style="background:var(--soft)"><div class="wrap priv">
  <div><span class="kicker">🔒 Privacy</span><h2 style="margin-top:16px">Private by construction, not by promise.</h2>
  <p class="lede">Heed doesn't ask for the internet permission, so Android itself keeps it offline. Your voice, transcripts and tasks stay in Heed's private folder on your phone.</p>
  <p style="margin-top:20px"><a href="/privacy">Read the privacy policy →</a></p></div>
  <div style="position:relative">
    <ul class="ticks">
      <li>No internet permission: nothing can be uploaded</li>
      <li>No account, no sign-up, no email</li>
      <li>No analytics, no ads, no trackers</li>
      <li>All three models built in; nothing to download</li>
      <li>Export and restore a backup yourself</li>
    </ul>
  </div>
</div></section>

<section id="faq"><div class="wrap">
  <div class="head"><span class="kicker">FAQ</span><h2 style="margin-top:16px">Questions</h2></div>
  <div class="faq">{faq}</div>
</div></section>

<section class="cta"><div class="wrap" style="max-width:760px">
  <div class="pal">{mascot("party", 130)}</div>
  {sparkle("18%", "40px", 18, "#F2C94C", 0)}{sparkle("78%", "70px", 14, "#3E9B57", .7)}{sparkle("70%", "20px", 10, "#2a78d6", 1.3)}
  <h2>Stop typing. <mark>Start talking.</mark></h2>
  <p class="lede">Completely free. No subscription, no ads, no account.</p>
  <div class="actions"><a class="play" href="{PLAY}" target="_blank" rel="noopener">{PLAY_ICON}<span><small>Free on</small><b>Google Play</b></span></a></div>
</div></section>

<footer><div class="wrap foot">
  <span>© 2026 Heed · Android · English</span>
  <div><a href="#how">How it works</a><a href="#quality">Quality</a><a href="#search">Search</a><a href="/privacy">Privacy policy</a><a href="{PLAY}" target="_blank" rel="noopener">Google Play</a></div>
</div></footer>
<div id="tip" role="tooltip"></div>
<script>
(function(){{var t=document.getElementById('tip');
document.querySelectorAll('.hit').forEach(function(g){{
g.addEventListener('mousemove',function(e){{t.textContent=g.getAttribute('data-tip');t.style.opacity=1;
var x=Math.min(e.clientX+14,innerWidth-t.offsetWidth-8);t.style.left=x+'px';t.style.top=(e.clientY+16)+'px';}});
g.addEventListener('mouseleave',function(){{t.style.opacity=0;}});}});}})();
</script>
</body></html>
"""


PRIV_CSS = r"""
:root{--bg:#FFFFFF;--soft:#F7F7F5;--ink:#191919;--ink-2:#37352F;--ink-3:#787774;--line:#E9E9E7;--brand:#2F8A4C;--brand-soft:#EAF5EC;--ui:"Inter",system-ui,-apple-system,sans-serif;--mono:"JetBrains Mono",ui-monospace,monospace;color-scheme:light}
*{box-sizing:border-box}body{margin:0;background:#fff;color:var(--ink-2);font:16.5px/1.65 var(--ui);-webkit-font-smoothing:antialiased}
a{color:var(--ink);text-decoration:underline;text-decoration-color:var(--line);text-underline-offset:3px}a:hover{text-decoration-color:var(--ink)}
nav.nav{position:sticky;top:0;z-index:10;background:rgba(255,255,255,.92);backdrop-filter:blur(8px);border-bottom:1px solid var(--line)}
.nav-inner{max-width:760px;margin:0 auto;height:60px;display:flex;align-items:center;justify-content:space-between;padding:0 max(20px,env(safe-area-inset-right,0px)) 0 max(20px,env(safe-area-inset-left,0px))}
.logo{display:flex;align-items:center;gap:8px;color:var(--ink);font:750 19px var(--ui);text-decoration:none}.logo-mark{display:none}
.nav-back{font:500 14px var(--ui);color:var(--ink-3);text-decoration:none}.nav-back:hover{color:var(--ink)}
main{max-width:760px;margin:0 auto;padding:52px max(20px,env(safe-area-inset-right,0px)) 80px max(20px,env(safe-area-inset-left,0px))}
.eyebrow{display:inline-flex;font:600 13px var(--ui);color:var(--brand);background:var(--brand-soft);padding:5px 11px;border-radius:999px}
h1,h2,h3{color:var(--ink);letter-spacing:-.025em}h1 em,h2 em{font-style:normal}
main h1{font-size:clamp(36px,5vw,52px);line-height:1.05;font-weight:800;margin:16px 0 8px}
main h2{font-size:26px;font-weight:750;margin:52px 0 12px}main h3{font-size:17px;margin:26px 0 8px}
.meta{font:13px var(--ui);color:var(--ink-3)}
.tldr{margin-top:28px;background:var(--soft);border-radius:14px;padding:22px 24px}.tldr h2{margin:0 0 10px;font-size:19px}.tldr ul{margin:0;padding-left:20px}.tldr li{margin:6px 0}
strong{color:var(--ink)}
.perm-table{width:100%;border-collapse:collapse;margin:16px 0;font-size:15px}.perm-table td,.perm-table th{border-bottom:1px solid var(--line);padding:11px 10px;text-align:left;vertical-align:top}
.perm-table th{font-weight:600;color:var(--ink-3)}.perm-table td:first-child{width:38%}
code{font:12.5px var(--mono);background:var(--soft);padding:2px 6px;border-radius:5px;color:#C0392B;word-break:break-word}
.callout{margin:18px 0;padding:14px 18px;background:var(--soft);border-radius:10px}
hr{border:0;border-top:1px solid var(--line);margin:52px 0 20px}
body>footer{max-width:760px;margin:0 auto;padding:16px 20px 40px;display:flex;justify-content:space-between;font-size:13px;color:var(--ink-3)}body>footer a{color:var(--ink-3)}
"""


def restyle_privacy():
    p = ROOT / "privacy.html"
    s = p.read_text(encoding="utf-8")
    a = s.index('<link href="https://fonts.googleapis.com/css2')
    b = s.index("</style>") + len("</style>")
    fonts = '<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500&display=swap" rel="stylesheet">'
    s = s[:a] + fonts + "\n<style>" + PRIV_CSS + asset("skein_css") + "</style>" + s[b:]
    if 'class="logo-mark"' in s:
        s = s.replace('<span class="logo-mark">H</span>', mascot("logo", 28))
    s = s.replace("fetching the Geist and Instrument Serif typefaces", "fetching the Inter and JetBrains Mono typefaces")
    p.write_text(s, encoding="utf-8")


if __name__ == "__main__":
    (ROOT / "index.html").write_text(page(), encoding="utf-8")
    restyle_privacy()
    print("built", (ROOT / "index.html").stat().st_size, "bytes")
