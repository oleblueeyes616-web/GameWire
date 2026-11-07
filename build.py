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

    cards = "\n".join(
        f'<article class="card" data-src="{html.escape(i["source"])}">'
        f'<div class="meta"><span class="src">{html.escape(i["source"])}</span>'
        f'<time datetime="{i["date"].isoformat()}"></time></div>'
        f'<h2><a href="{html.escape(i["link"])}" target="_blank" rel="noopener noreferrer">{html.escape(i["title"])}</a></h2>'
        f'<p>{html.escape(i["summary"])}</p></article>'
        for i in uniq
    )
    chips = "".join(f'<button class="chip" data-src="{html.escape(s)}">{html.escape(s)}</button>' for s in FEEDS)
    page = TEMPLATE.replace("%%CARDS%%", cards or "<p>No stories right now. Check back soon.</p>") \
                   .replace("%%CHIPS%%", chips).replace("%%UPDATED%%", now.isoformat())
    out = Path("site")
    out.mkdir(exist_ok=True)
    (out / "index.html").write_text(page, encoding="utf-8")
    print(f"wrote {len(uniq)} stories")


TEMPLATE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>GameWire: Gaming News</title>
<style>
:root{--bg:#f4f5f9;--card:#fff;--ink:#14161f;--mut:#5d6378;--acc:#6d28d9;--line:#e0e3ee;color-scheme:light}
@media(prefers-color-scheme:dark){:root{--bg:#0d0f17;--card:#161a26;--ink:#eceefa;--mut:#9aa1bb;--acc:#a78bfa;--line:#252b3d;color-scheme:dark}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.5 system-ui,-apple-system,Segoe UI,sans-serif}
header{padding:28px 20px 12px;max-width:1100px;margin:auto}
h1{margin:0;font-size:2rem;letter-spacing:-.02em}h1 span{color:var(--acc)}
.sub{color:var(--mut);font-size:.9rem;margin-top:4px}
.tools{display:flex;flex-wrap:wrap;gap:8px;margin-top:16px}
input{flex:1 1 220px;padding:10px 14px;border-radius:10px;border:1px solid var(--line);background:var(--card);color:var(--ink);font:inherit}
.chip{padding:8px 12px;border-radius:999px;border:1px solid var(--line);background:var(--card);color:var(--ink);cursor:pointer;font:inherit;font-size:.85rem}
.chip.on{background:var(--acc);border-color:var(--acc);color:#fff}
main{max-width:1100px;margin:auto;padding:8px 20px 48px;display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:16px}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px;display:flex;flex-direction:column;gap:8px}
.card:hover{border-color:var(--acc)}
.meta{display:flex;justify-content:space-between;font-size:.78rem;color:var(--mut)}
.src{color:var(--acc);font-weight:600;text-transform:uppercase;letter-spacing:.05em}
h2{margin:0;font-size:1.05rem;line-height:1.3}h2 a{color:inherit;text-decoration:none}h2 a:hover{text-decoration:underline}
p{margin:0;color:var(--mut);font-size:.9rem}
footer{text-align:center;color:var(--mut);font-size:.8rem;padding:0 20px 32px}
</style></head><body>
<header><h1>Game<span>Wire</span></h1>
<div class="sub">Auto-updated gaming headlines. Last built <time id="upd" datetime="%%UPDATED%%"></time></div>
<div class="tools"><input id="q" type="search" placeholder="Search headlines…">%%CHIPS%%</div></header>
<main id="list">
%%CARDS%%
</main>
<footer>Headlines and short excerpts link to the original publishers. All rights belong to them.</footer>
<script>
const fmt=new Intl.DateTimeFormat(undefined,{month:"short",day:"numeric",hour:"numeric",minute:"2-digit"});
document.querySelectorAll("time").forEach(t=>t.textContent=fmt.format(new Date(t.dateTime)));
const cards=[...document.querySelectorAll(".card")],on=new Set(),q=document.getElementById("q");
function apply(){const s=q.value.toLowerCase();cards.forEach(c=>{
  c.style.display=(!on.size||on.has(c.dataset.src))&&c.textContent.toLowerCase().includes(s)?"":"none"})}
q.addEventListener("input",apply);
document.querySelectorAll(".chip").forEach(b=>b.addEventListener("click",()=>{
  on.has(b.dataset.src)?on.delete(b.dataset.src):on.add(b.dataset.src);b.classList.toggle("on");apply()}));
setTimeout(()=>location.reload(),30*60*1000);
</script></body></html>
"""

if __name__ == "__main__":
    main()
