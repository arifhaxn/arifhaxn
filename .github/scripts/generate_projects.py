#!/usr/bin/env python3
"""
Generate an animated, theme-matched projects panel (projects.svg).

Reads projects.json (user curated) + live GitHub data merged by the workflow.
One SVG, 2-column grid of mini terminal cards. Add/remove/reorder projects by
editing projects.json — the README never changes.

Theme: matches the profile banner (navy #0A101F, cyan #22D3EE, violet #A78BFA,
emerald #10B981, mono font, dotted leaders, pulsing dots, animated accents).
"""
import json, base64, os, sys, math, html
from datetime import datetime, timezone

# ---------------- themes ----------------
THEMES = {
    "dark": {
        "BG": "#0A101F", "PANEL": "#0C1426", "PANEL_BAR": "#0B1222",
        "CYAN": "#22D3EE", "VIOLET": "#A78BFA", "VIOLET2": "#7C3AED",
        "EMERALD": "#10B981", "TEXT": "#F8FAFC", "MUTED": "#94A3B8",
        "DIM": "#475569",
        "STROKE": "rgba(34,211,238,0.28)", "STROKE_HI": "rgba(34,211,238,0.5)",
        "STROKE_LO": "rgba(34,211,238,0.22)", "BARLINE": "rgba(255,255,255,0.08)",
        "RING_BG": "rgba(148,163,184,0.15)", "PILL_BG": "rgba(124,58,237,0.28)",
        "PILL_STROKE": "rgba(167,139,250,0.5)", "MONO_TX": "#EDE9FE",
    },
    "light": {
        "BG": "#F8FAFC", "PANEL": "#FFFFFF", "PANEL_BAR": "#F1F5F9",
        "CYAN": "#0891B2", "VIOLET": "#7C3AED", "VIOLET2": "#7C3AED",
        "EMERALD": "#059669", "TEXT": "#0F172A", "MUTED": "#475569",
        "DIM": "#94A3B8",
        "STROKE": "rgba(8,145,178,0.30)", "STROKE_HI": "rgba(8,145,178,0.55)",
        "STROKE_LO": "rgba(8,145,178,0.20)", "BARLINE": "rgba(0,0,0,0.08)",
        "RING_BG": "rgba(100,116,139,0.20)", "PILL_BG": "rgba(124,58,237,0.12)",
        "PILL_STROKE": "rgba(124,58,237,0.4)", "MONO_TX": "#FFFFFF",
    },
}

# active palette — set by set_theme(); defaults to dark
BG = PANEL = PANEL_BAR = CYAN = VIOLET = VIOLET2 = EMERALD = TEXT = MUTED = DIM = None
STROKE = STROKE_HI = STROKE_LO = BARLINE = RING_BG = PILL_BG = PILL_STROKE = MONO_TX = None
DONUT_COLORS = []

def set_theme(name):
    t = THEMES[name]
    g = globals()
    for k, v in t.items():
        g[k] = v
    g["DONUT_COLORS"] = [t["VIOLET"], t["CYAN"], t["EMERALD"], "#6366F1", "#64748B", "#94A3B8"]

set_theme("dark")


# ---------------- layout ----------------
W        = 1180
CARD_W   = 578
CARD_H   = 168
GAP      = 14
MARGIN   = 5
FONT     = "ui-monospace,SFMono-Regular,Menlo,Consolas,'Liberation Mono',monospace"

def esc(s): return html.escape(str(s), quote=True)

def rel_time(iso):
    if not iso: return "n/a"
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        d = (datetime.now(timezone.utc) - dt)
        if d.days > 365: return f"{d.days//365}y ago"
        if d.days > 30:  return f"{d.days//30}mo ago"
        if d.days > 0:   return f"{d.days}d ago"
        h = d.seconds // 3600
        return f"{h}h ago" if h else "just now"
    except Exception:
        return "n/a"

def load_logo_b64(path):
    if not path: return None
    for base in ("logos", "."):
        p = os.path.join(base, path)
        if os.path.exists(p):
            ext = os.path.splitext(p)[1].lower()
            mime = {"png":"image/png","svg":"image/svg+xml","jpg":"image/jpeg",
                    "jpeg":"image/jpeg","webp":"image/webp"}.get(ext[1:], "image/png")
            with open(p, "rb") as f:
                return f"data:{mime};base64," + base64.b64encode(f.read()).decode()
    return None

def wrap_text(s, max_chars, max_lines=2):
    words = s.split()
    lines, cur = [], ""
    for w in words:
        if len(cur) + len(w) + 1 <= max_chars:
            cur = (cur + " " + w).strip()
        else:
            lines.append(cur); cur = w
            if len(lines) == max_lines: break
    if cur and len(lines) < max_lines: lines.append(cur)
    if len(lines) == max_lines and words and " ".join(lines).count(" ") + 1 < len(words):
        lines[-1] = lines[-1][:max_chars-1].rstrip() + "…"
    return lines

def donut_segments(languages, cx, cy, r, begin):
    """Animated donut: each segment draws itself in sequence (SMIL)."""
    total = sum(languages.values()) or 1
    entries = sorted(languages.items(), key=lambda kv: -kv[1])[:4]
    other = total - sum(v for _, v in entries)
    if other > 0: entries.append(("Other", other))
    C = 2 * math.pi * r
    out, legend = [], []
    offset = 0.0
    t = begin
    for i, (lang, v) in enumerate(entries):
        frac = v / total
        seg = frac * C
        col = DONUT_COLORS[i % len(DONUT_COLORS)]
        # draw-in: dasharray fixed, dashoffset animates from seg to 0 within its slot
        out.append(
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{col}" stroke-width="9" '
            f'stroke-dasharray="{seg:.2f} {C - seg:.2f}" stroke-dashoffset="{-offset:.2f}" '
            f'transform="rotate(-90 {cx} {cy})" opacity="0">'
            f'<animate attributeName="opacity" from="0" to="1" dur="0.01s" begin="{t:.2f}s" fill="freeze"/>'
            f'<animate attributeName="stroke-dasharray" from="0 {C:.2f}" to="{seg:.2f} {C - seg:.2f}" '
            f'dur="0.6s" begin="{t:.2f}s" fill="freeze" calcMode="spline" keyTimes="0;1" keySplines="0.3 0 0.2 1"/>'
            f'</circle>')
        legend.append((lang, frac, col))
        offset += seg
        t += 0.18
    return "".join(out), legend

def card(p, x, y, idx):
    b = 0.25 + idx * 0.15          # staggered entrance
    e = []
    a = e.append
    # normalize repo: accept "owner/repo" OR a full github URL
    repo = p.get("repo", "").strip()
    repo = repo.replace("https://github.com/", "").replace("http://github.com/", "")
    repo = repo.rstrip("/")
    href = f"https://github.com/{esc(repo)}"
    a(f'<a href="{href}" target="_blank">')
    a(f'<g opacity="0" transform="translate({x},{y})">')
    a(f'<animate attributeName="opacity" from="0" to="1" dur="0.5s" begin="{b:.2f}s" fill="freeze"/>')

    # card shell — mini terminal
    a(f'<rect width="{CARD_W}" height="{CARD_H}" rx="12" fill="{PANEL}" stroke="{STROKE}">'
      f'<animate attributeName="stroke" values="{STROKE_LO};{STROKE_HI};{STROKE_LO}" '
      f'dur="4.5s" begin="{b+idx*0.7:.2f}s" repeatCount="indefinite"/></rect>')
    a(f'<rect width="{CARD_W}" height="30" rx="12" fill="{PANEL_BAR}"/>')
    a(f'<rect y="18" width="{CARD_W}" height="12" fill="{PANEL_BAR}"/>')
    a(f'<line x1="0" y1="30" x2="{CARD_W}" y2="30" stroke="{BARLINE}"/>')
    a(f'<text x="16" y="19" font-size="10" fill="{MUTED}"><tspan fill="{CYAN}">&#8226;</tspan> {esc(repo)}</text>')

    # activity dot: emerald pulse if pushed within 14 days, dim otherwise
    days = 999
    try:
        dt = datetime.fromisoformat(p.get("pushed_at", "").replace("Z", "+00:00"))
        days = (datetime.now(timezone.utc) - dt).days
    except Exception:
        pass
    if days <= 14:
        a(f'<circle cx="{CARD_W-16}" cy="15" r="3.5" fill="{EMERALD}">'
          f'<animate attributeName="opacity" values="1;0.25;1" dur="1.8s" repeatCount="indefinite"/></circle>')
    else:
        a(f'<circle cx="{CARD_W-16}" cy="15" r="3.5" fill="{DIM}"/>')

    # logo (base64) or fallback monogram — with a gentle vertical float
    logo = p.get("_logo_b64")
    float_anim = (f'<animateTransform attributeName="transform" type="translate" '
                  f'values="0 0; 0 -2.5; 0 0" dur="5s" begin="{b+idx*0.5:.2f}s" '
                  f'repeatCount="indefinite" calcMode="spline" keyTimes="0;0.5;1" '
                  f'keySplines="0.4 0 0.6 1;0.4 0 0.6 1"/>')
    if logo:
        a(f'<g>{float_anim}<image x="16" y="44" width="40" height="40" href="{logo}" preserveAspectRatio="xMidYMid meet"/></g>')
    else:
        initial = esc((p.get("name") or "?")[0].upper())
        a(f'<g>{float_anim}<rect x="16" y="44" width="40" height="40" rx="9" fill="{VIOLET2}" opacity="0.9"/>'
          f'<text x="36" y="71" text-anchor="middle" font-size="20" font-weight="700" fill="{MONO_TX}">{initial}</text></g>')

    # name + blinking cursor
    name = esc(p.get("name", "unnamed"))
    a(f'<text x="68" y="61" font-size="17" font-weight="700" fill="{TEXT}">{name}'
      f'<tspan fill="{CYAN}">_<animate attributeName="opacity" values="1;0;1" dur="1.2s" '
      f'begin="{b+0.4:.2f}s" repeatCount="indefinite"/></tspan></text>')

    # description, wrapped to 2 lines
    for i, line in enumerate(wrap_text(p.get("description", ""), 52)):
        a(f'<text x="68" y="{80 + i * 16}" font-size="11" fill="{MUTED}">{esc(line)}</text>')

    # tag pills
    tx = 68
    for tag in (p.get("tags") or [])[:3]:
        tw = len(tag) * 6.6 + 14
        a(f'<rect x="{tx}" y="118" width="{tw:.0f}" height="17" rx="8.5" fill="{PILL_BG}" stroke="{PILL_STROKE}"/>')
        a(f'<text x="{tx + tw/2:.0f}" y="130" text-anchor="middle" font-size="9.5" fill="{VIOLET}">{esc(tag)}</text>')
        tx += tw + 7

    # bottom row: stars + updated
    stars = p.get("stars", 0)
    a(f'<text x="68" y="155" font-size="11" fill="{MUTED}">'
      f'<tspan fill="{CYAN}">&#9733;</tspan> {stars}'
      f'<tspan fill="{DIM}" dx="14">updated {rel_time(p.get("pushed_at"))}</tspan></text>')

    # language donut, animated draw-in — vertically centered in the card body
    langs = p.get("languages") or {}
    if langs:
        cx, cy, r = CARD_W - 58, CARD_H // 2 + 6, 27
        segs, legend = donut_segments(langs, cx, cy, r, b + 0.3)
        a(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{RING_BG}" stroke-width="9"/>')
        a(segs)
        top = legend[0]
        a(f'<text x="{cx}" y="{cy+4}" text-anchor="middle" font-size="11" font-weight="700" fill="{TEXT}">{top[1]*100:.0f}%</text>')
        # legend: fixed left column, dot then left-aligned text; ends well before the ring
        dot_x = cx - r - 92
        text_x = dot_x + 9
        ly = cy - 22
        for lang, frac, col in legend[:3]:
            a(f'<circle cx="{dot_x}" cy="{ly}" r="3.5" fill="{col}"/>')
            a(f'<text x="{text_x}" y="{ly+4}" font-size="10" fill="{MUTED}">{esc(lang)} {frac*100:.0f}%</text>')
            ly += 18
    a('</g>')
    a('</a>')
    return "".join(e)

def build(projects, theme="dark"):
    rows = math.ceil(len(projects) / 2)
    H = 56 + rows * (CARD_H + GAP) + MARGIN
    gid = f"acc_{theme}"
    s = []
    a = s.append
    a(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
      f'font-family="{FONT}" role="img" aria-label="Projects">')
    a(f'<rect width="{W}" height="{H}" fill="{BG}"/>')
    # animated accent gradient (same as banner)
    a(f'<defs><linearGradient id="{gid}" x1="0" y1="0" x2="1" y2="0">'
      f'<stop offset="0" stop-color="{VIOLET2}"><animate attributeName="stop-color" values="{VIOLET2};{CYAN};{EMERALD};{VIOLET2}" dur="10s" repeatCount="indefinite"/></stop>'
      f'<stop offset="1" stop-color="{EMERALD}"><animate attributeName="stop-color" values="{EMERALD};{VIOLET2};{CYAN};{EMERALD}" dur="10s" repeatCount="indefinite"/></stop>'
      '</linearGradient></defs>')
    # header: matches SYSTEM.INFO styling
    a(f'<text x="{MARGIN+2}" y="18" font-size="11" letter-spacing="2" fill="{CYAN}">PROJECTS.LIST</text>')
    a(f'<text x="{MARGIN+130}" y="18" font-size="10" fill="{DIM}">./projects.sh --all</text>')
    a(f'<line x1="{MARGIN}" y1="28" x2="{W-MARGIN}" y2="28" stroke="url(#{gid})" stroke-width="1.5" opacity="0.7"/>')
    for i, p in enumerate(projects):
        x = MARGIN + (i % 2) * (CARD_W + GAP + 4)
        y = 42 + (i // 2) * (CARD_H + GAP)
        a(card(p, x, y, i))
    a('</svg>')
    return "".join(s)

if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else "merged.json"
    outdir = sys.argv[2] if len(sys.argv) > 2 else "."
    with open(src) as f:
        projects = json.load(f)
    for p in projects:
        p["_logo_b64"] = load_logo_b64(p.get("logo"))
    for theme, fname in (("dark", "projects.svg"), ("light", "projects-light.svg")):
        set_theme(theme)
        svg = build(projects, theme)
        path = os.path.join(outdir, fname)
        with open(path, "w") as f:
            f.write(svg)
        print(f"wrote {path}: {theme}, {len(projects)} projects, {len(svg)//1024}KB")
