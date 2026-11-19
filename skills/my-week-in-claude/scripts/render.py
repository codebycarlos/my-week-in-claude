#!/usr/bin/env python3
"""Render stats.json and prompts.json (from collect.py) and cards.json (written by Claude) into a PNG."""
import argparse, datetime as dt, html, json, os, pathlib, re, shutil, subprocess, sys, tempfile, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "..", "assets")
ICONS = os.path.join(ASSETS, "icons")
# Full-colour icon sets from Iconify, best first: brand logos, then developer and file-type icons
# (the Office apps live in vscode-icons). Each downloads once and is kept in CACHE.
SETS = ["logos@1.2.20", "skill-icons@1.2.4", "devicon@1.2.83", "vscode-icons@1.2.99"]
CACHE = os.path.join(os.path.expanduser("~"), ".cache", "my-week-in-claude")
CHROME = ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "/Applications/Chromium.app/Contents/MacOS/Chromium",
          "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
          r"C:\Program Files\Google\Chrome\Application\chrome.exe", r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
          os.path.join(os.environ.get("LOCALAPPDATA", ""), "Google", "Chrome", "Application", "chrome.exe"),
          r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe", r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
          "google-chrome", "chromium", "chromium-browser", "chrome", "msedge"]
_sets = {}
GLOBE = ('<svg viewBox="0 0 24 24" width=16 height=16 fill="none" stroke="#1a73e8" stroke-width="2"><circle cx="12" cy="12" r="10"/>'
         '<path d="M2 12h20M12 2a15 15 0 0 1 0 20M12 2a15 15 0 0 0 0 20"/></svg>')


def icon_set(spec):
    """One Iconify set, from the cache or the CDN. Empty when offline."""
    if spec not in _sets:
        local = os.path.join(CACHE, spec + ".json")
        if not os.path.exists(local):
            try:
                data = urllib.request.urlopen(f"https://cdn.jsdelivr.net/npm/@iconify-json/{spec}/icons.json", timeout=10).read()
                os.makedirs(CACHE, exist_ok=True); open(local, "wb").write(data)
            except OSError:
                _sets[spec] = {}
                return {}
        _sets[spec] = json.load(open(local, encoding="utf-8"))
    return _sets[spec]


def find_icon(name):
    """An app's full-colour logo as SVG, found from its name ("Slack", "Excel"). A logo too wide for
    a chip (a wordmark) comes back as a letter tile in its main colour, and an unknown app as a grey one."""
    n = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    if n == "web": return GLOBE
    n = re.sub(r"-(com|io|ai|app)$", "", n)
    bare = re.sub(r"^(google|microsoft)-", "", n)
    wanted = list(dict.fromkeys([f"{n}-icon", n, f"{bare}-icon", f"microsoft-{bare}-icon", f"microsoft-{bare}",
                                 f"google-{bare}-icon", f"google-{bare}", bare]))
    colour = "#424a53"
    for spec in SETS:
        data = icon_set(spec)
        aliases = data.get("aliases", {})
        names = {**data.get("icons", {}), **aliases}
        close = [k for k in names if all(w in k.split("-") for w in bare.split("-"))
                 and not re.search(r"wordmark|folder|-dark|monochrome|opened", k)]
        for hit in [w for w in wanted if w in names] + sorted(close, key=lambda k: (not k.endswith("-icon"), len(k))):
            ic = data["icons"][aliases[hit]["parent"] if hit in aliases else hit]
            w, h = ic.get("width", data.get("width", 16)), ic.get("height", data.get("height", 16))
            if w <= 2 * h:
                return f'<svg viewBox="{ic.get("left", 0)} {ic.get("top", 0)} {w} {h}" width=16 height=16>{ic["body"]}</svg>'
            fills = re.findall(r'fill="(#[0-9A-Fa-f]{3}(?:[0-9A-Fa-f]{3})?)"', ic["body"])
            if fills and colour == "#424a53": colour = max(set(fills), key=fills.count)
    shorter = name.rsplit(" ", 1)[0]
    return find_icon(shorter) if shorter != name else tile(colour, name)


def tile(colour, name):
    return (f'<svg viewBox="0 0 24 24" width=16 height=16><rect x="1" y="1" width="22" height="22" rx="5" fill="{colour}"/>'
            f'<text x="12" y="17" text-anchor="middle" font-family="Poppins,sans-serif" font-weight="700" font-size="14" '
            f'fill="#fff">{html.escape(name[:1].upper())}</text></svg>')


def icon(app):
    """A chip for any app, by name: "Slack", or {"name": "Slack", "colour": "#hex"} to colour a letter tile."""
    app = {"name": app} if isinstance(app, str) else app
    svg = tile(app["colour"], app["name"]) if app.get("colour") else find_icon(app["name"])
    return f"<span class=app>{svg}{html.escape(app['name'])}</span>"


def example(q):
    """One quote, with small logos of the apps its work drew on."""
    q = {"text": q} if isinstance(q, str) else q
    names = [x if isinstance(x, str) else x["name"] for x in q.get("apps", [])]
    via = "".join(f'<span title="{html.escape(n)}">{find_icon(n)}</span>' for n in names)
    return f"<li>“{html.escape(q['text'])}”" + (f"<span class=via>{via}</span>" if via else "") + "</li>"


def short_name(name):
    parts = name.split()
    return parts[0] + (f" {parts[-1][0]}" if len(parts) > 1 else "")


def span(since, until):
    a, b = dt.date.fromisoformat(since), dt.date.fromisoformat(until)
    start = f"{a.day} {a.strftime('%b')}" + ("" if a.year == b.year else f" {a.year}")
    return f"{start} to {b.day} {b.strftime('%b')} {b.year}"


def models_html(m):
    cols = ""
    for g, label in (("main", "My sessions"), ("sub", "Subagents")):
        if not m[g]["rows"]: continue
        rows = "".join(f"<div class=mi><span>{html.escape(r['model'])}"
                       + (f" <i>{html.escape(r['effort'])}</i>" if r["effort"] != "default" else "")
                       + f"</span><b>{r['share']}%</b></div>" for r in m[g]["rows"])
        cols += f"<div class=mcol><div class=mt><span>{label}</span><b>{m[g]['share']}%</b></div><div class=ml>{rows}</div></div>"
    return f"<div class=models><div class=mh>Models and thinking level <span>share of the week</span></div><div class=mcols>{cols}</div></div>"


NOTE = ("A prompt doesn't tell the whole story. Work may often involve multiple rounds of iteration, "
        "human oversight and hands-on collaboration. "
        "Always make the work your own and follow any AI policy that applies to you.")
NAME_SAFE = {"CodeRabbit", "I", "I'm", "I've", "I'll", "OK", "PR", "PRs", "Claude", "AI", "CI", "UI", "PNG", "CSV"}


def possible_names(cards, firsts=(), persona=None):
    """Words a redaction pass must look at: capitalised ones mid-sentence, any word the system word list
    knows as a proper noun (Sam, priya), and URLs, emails and ticket keys."""
    try: words = [w.strip() for w in open("/usr/share/dict/words", encoding="utf-8", errors="ignore")]
    except OSError: words = []
    proper = {w.lower() for w in words if w[:1].isupper()} - {w for w in words if w[:1].islower()}
    apps = {w for card in cards for q in card["examples"] if isinstance(q, dict)
            for a in q.get("apps", []) if isinstance(a, str) or not a.get("colour")
            if '<rect x="1"' not in find_icon(a if isinstance(a, str) else a["name"])
            for w in (a if isinstance(a, str) else a["name"]).split()}
    texts = [(card["title"], card["title"]) for card in cards]
    texts += [(q if isinstance(q, str) else q["text"], card["title"]) for card in cards for q in card["examples"]]
    texts += [(persona.get(k, ""), "Persona") for k in ("name", "line")] if persona else []
    texts += [(f.get(k, ""), "New this week") for f in firsts for k in ("name", "detail", "example")]
    seen = {}
    for q, where in texts:
        q = re.sub(r"\[[^\]]*\]", "", q or "")
        for m in re.finditer(r"https?://\S+|www\.\S+|\b[\w.+-]+@[\w-]+\.[\w.]+|\b[A-Z][A-Z0-9]+-\d+\b", q):
            seen.setdefault(m.group(0), where)
            q = q.replace(m.group(0), " ")
        for m in re.finditer(r"\b[A-Za-z][A-Za-z']+", q):
            w = m.group(0)
            if w in NAME_SAFE or w in apps: continue
            start = re.search(r"(^|[.?!…→\[“]\s*)$", q[:m.start()]) is not None
            if (w[0].isupper() and not start) or w.lower() in proper:
                seen.setdefault(w, where)
    return seen


def write_page(out, page, why):
    """No working browser, as in some chat sandboxes: hand over the page itself."""
    html_out = os.path.splitext(os.path.abspath(out))[0] + ".html"
    open(html_out, "w", encoding="utf-8").write(page)
    print(f"No Chrome, Chromium or Playwright here ({why}), so wrote the page instead: {html_out}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stats"); ap.add_argument("cards")
    ap.add_argument("--out", help="PNG path; defaults to a new file named after the week and time")
    ap.add_argument("--template", default=os.path.join(ASSETS, "template.html"))
    a = ap.parse_args()
    s = json.load(open(a.stats, encoding="utf-8")); c = json.load(open(a.cards, encoding="utf-8"))
    if not a.out:
        year, week, _ = dt.date.fromisoformat(s["until"]).isocalendar()
        stamp = dt.datetime.now().strftime("%d%b-%H%M%S").lower()
        a.out = os.path.join(os.path.expanduser("~/Downloads/my-week-in-claude"), f"my-week-in-claude-{year}-w{week:02d}-{stamp}.png")

    prompts_path = os.path.join(os.path.dirname(os.path.abspath(a.stats)), "prompts.json")
    if not os.path.exists(prompts_path): sys.exit(f"No prompts.json at {prompts_path}: it must sit next to stats.json.")
    prompts = json.load(open(prompts_path, encoding="utf-8"))
    places = {x["key"] for x in s["places"]}
    unknown = [k for card in c["cards"] for k in card.get("places", []) if k not in places]
    if unknown: sys.exit(f"Not a place in stats.json: {', '.join(unknown)}. Use one of: {', '.join(places)}")
    owner = {}
    for i, card in enumerate(c["cards"]):
        for p in prompts:
            if p["place"] in card.get("places", []): owner.setdefault(p["id"], i)
    for i, card in enumerate(c["cards"]):
        for pid in card.get("moved", []): owner[pid] = i
    used = [0] * len(c["cards"])
    for p in prompts:
        if p["id"] in owner: used[owner[p["id"]]] += p["tokens"]
    biggest = max(used, default=1) or 1
    cards = ""
    for card, t in sorted(zip(c["cards"], used), key=lambda x: -x[1]):
        share = round(100 * t / s["tokens"]) if s["tokens"] else 0
        qs = "".join(example(q) for q in card["examples"])
        cards += (f"<div class=card><div class=top><div class=name>{html.escape(card['title'])}</div>"
                  f"<div class=nums><b>{share}%</b></div></div>"
                  f"<div class=track><div class=bar style=\"width:{max(100*t/biggest, 1.5):.1f}%\"></div></div>"
                  f"<ul>{qs}</ul></div>")

    sub = (f"{s['sessions']} conversations · {s['messages_sent']:,} messages sent"
           f" · {s['messages_received']:,} replies")
    persona = c.get("persona")
    persona_html = (f"<div class=persona><span class=pn>{html.escape(persona['name'])}</span>"
                    f"<span class=pl>{html.escape(persona['line'])}</span></div>") if persona else ""
    items = ""
    for x in c.get("firsts", []):
        x = {"name": x} if isinstance(x, str) else x
        items += (f"<div class=first><div class=fl>" + (f"<div class=fk>{html.escape(x['kind'])}</div>" if x.get("kind") else "")
                  + f"<div class=fn>{html.escape(x['name'])}</div></div><div class=fr>"
                  + (f"<div class=fd>{html.escape(x['detail'])}</div>" if x.get("detail") else "")
                  + (f"<div class=fq>“{html.escape(x['example'])}”</div>" if x.get("example") else "") + "</div></div>")
    firsts_html = f"<div class=firsts><div class=mh>New this week</div><div class=fgrid>{items}</div></div>" if items else ""
    logo = re.search(r' d="([^"]+)"', open(os.path.join(ICONS, "claude.svg"), encoding="utf-8").read()).group(1)
    footer = c.get("footer", "See your week: ask Claude “Install the my-week-in-claude plugin and show me my week in Claude”")
    page = open(a.template, encoding="utf-8").read()
    for k, v in {"{name}": f"<h1>{html.escape(short_name(c['name']))}</h1>" if c.get("name") else "",
                 "{logo}": f'<svg viewBox="0 0 24 24" width=20 height=20 fill="#D97757"><path d="{logo}"/></svg>',
                 "{title}": html.escape(c.get("title", "My week in Claude")),
                 "{sub}": sub, "{span}": span(s['since'], s['until']), "{persona}": persona_html, "{firsts}": firsts_html,
                 "{footer}": html.escape(footer), "{note}": html.escape(c.get("note", NOTE)), "{models}": models_html(s["models"]), "{cards}": cards}.items():
        page = page.replace(k, v)

    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    chrome = next((p for p in CHROME if os.path.exists(p) or shutil.which(p)), None)
    if not chrome:
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as pw:
                browser = pw.chromium.launch()
                tab = browser.new_page(viewport={"width": 900, "height": 1000}, device_scale_factor=2)
                tab.set_content(page, wait_until="networkidle")
                tab.locator("#w").screenshot(path=os.path.abspath(a.out))
                browser.close()
        except Exception as e:
            return write_page(a.out, page, str(e).strip().splitlines()[0] if str(e).strip() else type(e).__name__)
    else:
        with tempfile.TemporaryDirectory() as tmp:
            page_path = os.path.join(tmp, "page.html"); open(page_path, "w", encoding="utf-8").write(page)
            uri = pathlib.Path(page_path).as_uri()
            flags = [chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--virtual-time-budget=5000"]
            try:
                if os.path.exists(a.out): os.remove(a.out)
                dom = subprocess.run(flags + ["--window-size=900,4000", "--dump-dom", uri],
                                     capture_output=True, text=True, encoding="utf-8", errors="ignore", timeout=120).stdout or ""
                height = re.search(r"<title>(\d+)</title>", dom)
                if not height: return write_page(a.out, page, f"{chrome} printed no page height")
                subprocess.run(flags + ["--force-device-scale-factor=2", f"--window-size=900,{height.group(1)}",
                                        "--screenshot=" + os.path.abspath(a.out), uri],
                               capture_output=True, timeout=120)
            except subprocess.TimeoutExpired:
                return write_page(a.out, page, f"{chrome} timed out")
            if not os.path.exists(a.out): return write_page(a.out, page, f"{chrome} wrote no PNG")
    names = possible_names(c["cards"], [f for f in c.get("firsts", []) if isinstance(f, dict)], c.get("persona"))
    if names:
        print("Check these for names, customers or anything to redact:")
        for w, t in names.items(): print(f"  {w}  ({t})")
    print(a.out)


if __name__ == "__main__":
    main()
