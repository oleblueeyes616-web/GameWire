#!/usr/bin/env python3
"""GameWire: pulls gaming news RSS/Atom feeds and writes site/index.html.
Standard library only. Edit FEEDS to add or remove sources."""
import html, re, urllib.request, xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

FEEDS = {
    "IGN": "https://feeds.ign.com/ign/games-all",
    "GameSpot": "https://www.gamespot.com/feeds/news/",
    "PC Gamer": "https://www.pcgamer.com/rss/",
    "Eurogamer": "https://www.eurogamer.net/feed",
    "Rock Paper Shotgun": "https://www.rockpapershotgun.com/feed",
    "Polygon": "https://www.polygon.com/rss/index.xml",
    "VGC": "https://www.videogameschronicle.com/feed/",
}
COLORS = {  # accent color per source
    "IGN": "#ff3b5c", "GameSpot": "#ffb020", "PC Gamer": "#22d3ee",
    "Eurogamer": "#4ade80", "Rock Paper Shotgun": "#f472b6",
    "Polygon": "#a78bfa", "VGC": "#60a5fa",
}
MAX_ITEMS = 72
SNIPPET = 170


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (GameWire news aggregator)"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return r.read()


def clean(t):
    t = re.sub(r"<[^>]+>", " ", html.unescape(t or ""))
    return re.sub(r"\s+", " ", t).strip()


def short(t, n=SNIPPET):
    if len(t) <= n:
        return t
    return t[:n].rsplit(" ", 1)[0].rstrip(".,;:") + "…"


def parse_date(s):
    if not s:
        return None
    try:
        d = parsedate_to_datetime(s)
    except Exception:
        try:
            d = datetime.fromisoformat(s.strip().replace("Z", "+00:00"))
        except Exception:
            return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def local(tag):
    return tag.rsplit("}", 1)[-1]


def parse(xml, source):
    out = []
    for el in ET.fromstring(xml).iter():
        if local(el.tag) not in ("item", "entry"):
            continue
        f = {}
        for c in el:
            n = local(c.tag)
            if n == "link":
                if c.get("href"):
                    if c.get("rel") in (None, "alternate"):
                        f.setdefault("link", c.get("href"))
                elif c.text:
                    f.setdefault("link", c.text.strip())
            elif n in ("title", "description", "summary", "pubDate", "published", "updated"):
                f.setdefault(n, c.text or "")
        date = parse_date(f.get("pubDate") or f.get("published") or f.get("updated"))
        title, link = clean(f.get("title")), f.get("link", "")
        if not (title and link.startswith(("http://", "https://")) and date):
            continue
        out.append({"title": title, "link": link, "date": date, "source": source,
                    "summary": short(clean(f.get("description") or f.get("summary")))})
    return out


def card(i, idx, now):
    e = html.escape
    color = COLORS.get(i["source"], "#a78bfa")
    hero = idx == 0
    new = '<span class="new">NEW</span>' if (now - i["date"]).total_seconds() < 10800 else ""
    top = '<span class="top">★ TOP STORY</span>' if hero else ""
    delay = min(idx * 45, 700)
    return (
        f'<article class="card{" hero" if hero else ""}" data-src="{e(i["source"])}" '
        f'style="--c:{color};animation-delay:{delay}ms">'
        f'<div class="meta"><span class="src">{e(i["source"])}</span>{top}{new}'
        f'<time datetime="{i["date"].isoformat()}"></time></div>'
        f'<h2><a href="{e(i["link"])}" target="_blank" rel="noopener noreferrer">{e(i["title"])}</a></h2>'
        f'<p>{e(i["summary"])}</p>'
        f'<a class="go" href="{e(i["link"])}" target="_blank" rel="noopener noreferrer">Read on {e(i["source"])} →</a>'
        f'</article>'
    )


def main():
    items, seen = [], set()
    for name, url in FEEDS.items():
        try:
            got = parse(fetch(url), name)
            print(f"ok   {name}: {len(got)} items")
            items += got
        except Exception as e:
            print(f"FAIL {name}: {e}")  # one broken feed never stops the build
    now = datetime.now(timezone.utc)
    items = [i for i in items if i["date"] <= now]
    items.sort(key=lambda i: i["date"], reverse=True)
    uniq = []
    for i in items:
        key = i["link"].split("?")[0]
        if key not in seen:
            seen.add(key)
            uniq.append(i)
    uniq = uniq[:MAX_ITEMS]

    cards = "\n".join(card(i, n, now) for n, i in enumerate(uniq))
    tick = "".join(
        f'<a href="{html.escape(i["link"])}" target="_blank" rel="noopener noreferrer">'
        f'<b style="color:{COLORS.get(i["source"], "#a78bfa")}">{html.escape(i["source"])}</b> '
        f'{html.escape(i["title"])}</a>' for i in uniq[:12])
    chips = "".join(
        f'<button class="chip" data-src="{html.escape(s)}" style="--c:{COLORS.get(s, "#a78bfa")}">'
        f'{html.escape(s)}</button>' for s in FEEDS)
    page = (TEMPLATE.replace("%%CARDS%%", cards or '<p class="empty">No stories right now. Check back soon.</p>')
            .replace("%%CHIPS%%", chips).replace("%%TICK%%", tick)
            .replace("%%UPDATED%%", now.isoformat()))
    out = Path("site")
    out.mkdir(exist_ok=True)
    (out / "index.html").write_text(page, encoding="utf-8")
    print(f"wrote {len(uniq)} stories")


TEMPLATE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="theme-color" content="#07080f">
<title>GameWire: Live Gaming News</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@700;900&family=Rajdhani:wght@500;600;700&display=swap" rel="stylesheet">
<style>
:root{--bg:#07080f;--panel:#0f1220;--ink:#eef0ff;--mut:#98a0c2;--line:#212844;--a:#8b5cf6;--b:#22d3ee;color-scheme:dark}
*{box-sizing:border-box}
body{margin:0;color:var(--ink);font:500 17px/1.5 "Rajdhani",system-ui,sans-serif;min-height:100vh;background-color:var(--bg);
background-image:radial-gradient(900px 500px at 12% -10%,rgba(139,92,246,.28),transparent 60%),radial-gradient(800px 500px at 92% 0,rgba(34,211,238,.2),transparent 60%),linear-gradient(rgba(255,255,255,.035) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.035) 1px,transparent 1px);
background-size:auto,auto,44px 44px,44px 44px;background-attachment:fixed}
.wrap{max-width:1180px;margin:auto;padding:0 20px}
.topbar{position:sticky;top:0;z-index:5;backdrop-filter:blur(12px);background:rgba(7,8,15,.7);border-bottom:1px solid var(--line)}
.bar{display:flex;align-items:center;justify-content:space-between;height:64px}
.logo{font:900 1.6rem "Orbitron",sans-serif;letter-spacing:.08em}
.logo span{background:linear-gradient(90deg,var(--a),var(--b));-webkit-background-clip:text;background-clip:text;color:transparent;filter:drop-shadow(0 0 12px rgba(139,92,246,.7))}
.live{display:flex;align-items:center;gap:8px;font-size:.85rem;color:var(--mut);letter-spacing:.08em;text-transform:uppercase}
.live i{width:9px;height:9px;border-radius:50%;background:#34d399;box-shadow:0 0 10px #34d399;animation:pulse 1.6s infinite}
.ticker{overflow:hidden;border-bottom:1px solid var(--line);background:rgba(15,18,32,.6);-webkit-mask:linear-gradient(90deg,transparent,#000 6%,#000 94%,transparent);mask:linear-gradient(90deg,transparent,#000 6%,#000 94%,transparent)}
.track{display:flex;gap:44px;width:max-content;padding:9px 0;animation:scroll 90s linear infinite}
.ticker:hover .track{animation-play-state:paused}
.track a{color:var(--ink);text-decoration:none;white-space:nowrap;font-size:.95rem}
.track a:hover{text-decoration:underline}
.track b{font-weight:700;margin-right:6px;text-transform:uppercase;font-size:.8rem;letter-spacing:.06em}
.hello{padding:36px 0 8px}
.hello h1{margin:0;font:900 clamp(1.8rem,5vw,3rem)/1.1 "Orbitron",sans-serif;letter-spacing:-.01em}
.hello h1 em{font-style:normal;background:linear-gradient(90deg,var(--a),var(--b));-webkit-background-clip:text;background-clip:text;color:transparent}
.hello p{margin:10px 0 0;color:var(--mut);font-size:1.1rem}
.tools{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin:20px 0 22px}
input{flex:1 1 240px;padding:11px 16px;border-radius:12px;border:1px solid var(--line);background:rgba(15,18,32,.8);color:var(--ink);font:inherit;outline:none}
input:focus{border-color:var(--b);box-shadow:0 0 0 3px rgba(34,211,238,.18)}
.chip{--c:#8b5cf6;padding:7px 14px;border-radius:999px;border:1px solid var(--c);background:transparent;color:var(--ink);cursor:pointer;font:600 .9rem "Rajdhani",sans-serif;letter-spacing:.03em;transition:.15s}
.chip:hover{box-shadow:0 0 14px -2px var(--c)}
.chip.on{background:var(--c);color:#07080f;box-shadow:0 0 16px -2px var(--c)}
#all{--c:#98a0c2}
#cnt{margin-left:auto;color:var(--mut);font-size:.9rem}
main{display:grid;grid-template-columns:repeat(auto-fill,minmax(310px,1fr));gap:18px;padding-bottom:56px}
.card{--c:#8b5cf6;position:relative;display:flex;flex-direction:column;gap:10px;overflow:hidden;padding:18px 18px 16px 24px;border-radius:16px;border:1px solid var(--line);
background:linear-gradient(180deg,rgba(255,255,255,.05),rgba(255,255,255,.01)),var(--panel);transition:transform .2s,box-shadow .2s,border-color .2s;animation:rise .55s both}
.card::before{content:"";position:absolute;left:0;top:0;bottom:0;width:4px;background:var(--c);box-shadow:0 0 18px var(--c)}
.card:hover{transform:translateY(-4px);border-color:var(--c);box-shadow:0 14px 34px -14px var(--c)}
.meta{display:flex;align-items:center;gap:8px;font-size:.8rem;color:var(--mut);letter-spacing:.05em}
.src{color:var(--c);font-weight:700;text-transform:uppercase}
.meta time{margin-left:auto}
.new,.top{padding:1px 8px;border-radius:6px;font-weight:700;font-size:.7rem;letter-spacing:.1em}
.new{background:#34d399;color:#07120d}
.top{background:linear-gradient(90deg,var(--a),var(--b));color:#07080f}
h2{margin:0;font-size:1.22rem;line-height:1.25;font-weight:700}
h2 a{color:inherit;text-decoration:none}
h2 a:hover{color:var(--c)}
p{margin:0;color:var(--mut);font-size:1rem}
.go{margin-top:auto;padding-top:4px;color:var(--c);text-decoration:none;font-weight:700;font-size:.92rem;letter-spacing:.03em}
.go:hover{text-decoration:underline}
.hero{grid-column:1/-1;padding:28px 28px 24px 32px;background:radial-gradient(600px 260px at 100% 0,color-mix(in srgb,var(--c) 22%,transparent),transparent 70%),linear-gradient(180deg,rgba(255,255,255,.06),rgba(255,255,255,.01)),var(--panel)}
.hero h2{font-size:clamp(1.5rem,3.4vw,2.3rem);line-height:1.15;max-width:900px}
.hero p{font-size:1.12rem;max-width:760px}
.empty{grid-column:1/-1;text-align:center;padding:60px 0}
footer{text-align:center;color:var(--mut);font-size:.85rem;padding:0 20px 36px}
@keyframes scroll{to{transform:translateX(-50%)}}
@keyframes pulse{50%{opacity:.35}}
@keyframes rise{from{opacity:0;transform:translateY(14px)}}
@media(prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
@media(max-width:560px){.hero{padding:22px 20px 20px 26px}#cnt{margin-left:0;width:100%}}
</style></head><body>
<div class="topbar"><div class="wrap bar"><div class="logo">GAME<span>WIRE</span></div>
<div class="live"><i></i>Live &middot; <time id="upd" datetime="%%UPDATED%%"></time></div></div></div>
<div class="ticker"><div class="track">%%TICK%%%%TICK%%</div></div>
<div class="wrap">
<section class="hello"><h1>Everything in gaming, <em>updated all day</em></h1>
<p>Headlines from the biggest gaming outlets, refreshed automatically every 30 minutes.</p></section>
<div class="tools"><input id="q" type="search" placeholder="Search stories…" aria-label="Search stories">
<button class="chip on" id="all">All</button>%%CHIPS%%<span id="cnt"></span></div>
<main id="list">
%%CARDS%%
</main></div>
<footer>Headlines and short excerpts link to the original publishers, who own all rights to their content.</footer>
<script>
const fmt=new Intl.DateTimeFormat(undefined,{month:"short",day:"numeric",hour:"numeric",minute:"2-digit"});
function ago(d){const m=Math.max(0,(Date.now()-d)/6e4);if(m<1)return"just now";if(m<60)return Math.floor(m)+"m ago";const h=m/60;if(h<24)return Math.floor(h)+"h ago";return Math.floor(h/24)+"d ago"}
document.getElementById("upd").textContent="updated "+fmt.format(new Date("%%UPDATED%%"));
document.querySelectorAll(".card time").forEach(t=>{const d=new Date(t.dateTime);t.textContent=ago(d);t.title=fmt.format(d)});
const cards=[...document.querySelectorAll(".card")],q=document.getElementById("q"),cnt=document.getElementById("cnt"),
chips=[...document.querySelectorAll(".chip[data-src]")],all=document.getElementById("all"),on=new Set();
function apply(){const s=q.value.toLowerCase();let n=0;
cards.forEach(c=>{const ok=(!on.size||on.has(c.dataset.src))&&c.textContent.toLowerCase().includes(s);c.style.display=ok?"":"none";if(ok)n++});
cnt.textContent=n+" stories";all.classList.toggle("on",!on.size);chips.forEach(b=>b.classList.toggle("on",on.has(b.dataset.src)))}
q.addEventListener("input",apply);
all.addEventListener("click",()=>{on.clear();apply()});
chips.forEach(b=>b.addEventListener("click",()=>{on.has(b.dataset.src)?on.delete(b.dataset.src):on.add(b.dataset.src);apply()}));
apply();
setTimeout(()=>location.reload(),30*60*1000);
</script></body></html>
"""

if __name__ == "__main__":
    main()
