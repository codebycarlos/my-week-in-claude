#!/usr/bin/env python3
"""Edit mode for the card: a page on this machine, opened in the browser, where the person changes the
card and sends what they want back to Claude.

  edit.py <work dir>                  serve the editor and open it (run in the background)
  edit.py <work dir> --wait           block until the person sends changes, then print them as JSON
  edit.py <work dir> --publish        save cards.json as the next version, which the open page loads
  edit.py <work dir> --fail "why"     tell the page the next version could not be made

The work dir holds stats.json, prompts.json and cards.json. Every version goes in versions/, with the
feedback sent on it, so the person can look back at any of them, compare two, and carry on from one.
"""
import argparse, copy, glob, html as H, http.server, json, os, sys, threading, time, urllib.parse, webbrowser

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import render  # noqa: E402

MAX_EXAMPLES = 10
MAX_PERSONAS = 10
MORE_PERSONAS = 3


def vdir(work): return os.path.join(work, "versions")
def vpath(work, n): return os.path.join(vdir(work), f"v{n}.json")
def fbpath(work, n): return os.path.join(vdir(work), f"v{n}.feedback.json")
def wpath(work, name): return os.path.join(work, name)


def versions(work):
    return sorted(int(os.path.basename(f)[1:-5]) for f in glob.glob(os.path.join(vdir(work), "v*.json"))
                  if not f.endswith(".feedback.json"))


def load(path): return json.load(open(path, encoding="utf-8"))


def save(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def rm(path):
    if os.path.exists(path): os.remove(path)


def text(q): return q if isinstance(q, str) else q.get("text", "")


def personas(c): return c.get("personas") or ([c["persona"]] if c.get("persona") else [])


def snapshot(work, cards, label, frm=None):
    """Save cards as the next version and make it the current cards.json."""
    os.makedirs(vdir(work), exist_ok=True)
    n = (versions(work) or [0])[-1] + 1
    cards = {k: v for k, v in cards.items() if k != "_version"}
    save(vpath(work, n), dict(cards, _version={"n": n, "label": label, "made": time.strftime("%H:%M"), "from": frm}))
    save(wpath(work, "cards.json"), cards)
    return n


def check(work, c):
    """Why this cards.json cannot be a version, or None."""
    for card in c.get("cards", []):
        if len(card.get("examples", [])) > MAX_EXAMPLES:
            return f"“{card['title']}” has {len(card['examples'])} examples, and the most is {MAX_EXAMPLES}."
    if len(personas(c)) > MAX_PERSONAS: return f"There are {len(personas(c))} personas, and the most is {MAX_PERSONAS}."
    try: render.build_page(load(wpath(work, "stats.json")), c, render.load_prompts(wpath(work, "stats.json")), edit=True)
    except SystemExit as e: return str(e)
    except Exception as e: return f"The card would not draw: {e}"
    return None


def asks(m, where, requests, liked):
    """Turn one item's marks into requests for Claude, carrying what they wrote about it."""
    said = (m.get("comment") or "").strip()
    w = dict(where, **({"comment": said} if said else {}))
    if m.get("vote") == "down": requests.append({"do": "replace", **w})
    if m.get("anonymise"): requests.append({"do": "anonymise", **w})
    if m.get("vote") == "up": liked.append(w)
    elif said and not m.get("vote") and not m.get("anonymise"): requests.append({"do": "comment", **w})


def apply(work, body):
    """Apply what needs no model (persona, removals, hidden sections), and list what does for Claude."""
    n = int(body["version"])
    c = load(vpath(work, n)); c.pop("_version", None)
    out = copy.deepcopy(c)
    ps = personas(c)
    pick = body.get("persona")
    if pick is None: out.pop("persona", None)
    elif 0 <= int(pick) < len(ps): out["persona"] = ps[int(pick)]
    if ps: out["personas"] = ps

    marks, sections = body.get("items", {}), body.get("sections", {})
    requests, liked = [], []
    votes, said = body.get("personaVotes", {}), body.get("personaComments", {})
    for i in sorted({int(k) for k in [*votes, *said]}):
        if i >= len(ps): continue
        before = len(requests)
        asks({"vote": votes.get(str(i)), "comment": said.get(str(i))},
             {"card": "Persona", "persona_index": i, "text": f"{ps[i]['name']}: {ps[i]['line']}"}, requests, liked)
        for r in requests[before:]: r["do"] += "_persona"
    room = MAX_PERSONAS - len(ps)
    if body.get("morePersonas") and room > 0: requests.append({"do": "more_personas", "count": min(MORE_PERSONAS, room)})

    content = 0
    for ci, card in enumerate(c["cards"]):
        hidden = sections.get(f"card:{ci}", bool(card.get("hidden")))
        if hidden: out["cards"][ci]["hidden"] = True
        else: out["cards"][ci].pop("hidden", None)
        kept = []
        for ei, q in enumerate(card["examples"]):
            m = marks.get(f"ex:{ci}:{ei}", {})
            if m.get("deleted"): continue
            kept.append(q)
            if hidden: continue
            asks(m, {"card": card["title"], "card_index": ci, "example_index": len(kept) - 1, "text": text(q)}, requests, liked)
        out["cards"][ci]["examples"] = kept
        if hidden: continue
        adds = body.get("adds", {}).get(str(ci), [])[:max(0, MAX_EXAMPLES - len(kept))]
        for h in adds:
            requests.append({"do": "add", "card": card["title"], "card_index": ci, **({"hint": h} if h else {})})
        content += len(kept) + len(adds)

    hide_firsts = sections.get("firsts", bool(c.get("firsts_hidden")))
    if hide_firsts: out["firsts_hidden"] = True
    else: out.pop("firsts_hidden", None)
    firsts = []
    for k, x in enumerate(c.get("firsts", [])):
        m = marks.get(f"first:{k}", {})
        if m.get("deleted"): continue
        firsts.append(x)
        if hide_firsts: continue
        asks(m, {"card": "New this week", "first_index": len(firsts) - 1, "text": text(x) if isinstance(x, str) else x.get("name", "")},
             requests, liked)
    if "firsts" in c: out["firsts"] = firsts
    if not hide_firsts: content += len(firsts)
    if not content:
        raise ValueError("There's nothing left to put on the card. Bring back a section or an example first.")

    note = (body.get("note") or "").strip()
    if not requests and not note and not any(l.get("comment") for l in liked):
        latest = snapshot(work, out, "your edits", n) if out != c else n
        return {"latest": latest, "waiting": False, "done": bool(body.get("done"))}, None
    save(wpath(work, "cards.json"), out)
    fb = {"from_version": n, "done": bool(body.get("done")), "persona": (out.get("persona") or {}).get("name"),
          "requests": requests, "liked": liked, "note": note,
          "next": "Edit cards.json for each request, then run edit.py <work dir> --publish, or --fail with the reason"}
    return {"latest": n, "waiting": True}, fb


def why(m):
    """Which piece of feedback a changed item answers."""
    said = (m.get("comment") or "").strip()
    how = "swapped" if m.get("vote") == "down" else "anonymised" if m.get("anonymise") else "rewritten" if said else "changed"
    return {"how": how, **({"said": said} if said else {})}


def match(new, sources):
    """Pair each new item with the feedback that asked for it, in order: Claude rewrites in place and adds at the end."""
    return {i: sources.pop(0) if sources else {"how": "changed"} for i in new}


def diff(prev, cur, fb=None):
    """What changed from one version to the next, keyed the way the editor marks items, with the feedback each change answers."""
    fb = fb or {}
    marks, adds = fb.get("items", {}), fb.get("adds", {})
    ch = {"items": {}, "firsts": {}, "cards": {}, "removed": {}, "persona": None, "newPersonas": {}, "firstsSection": None,
          "note": bool((fb.get("note") or "").strip())}
    before = {card["title"]: (pi, card) for pi, card in enumerate(prev["cards"])}
    for ci, card in enumerate(cur["cards"]):
        if card["title"] not in before: ch["cards"][ci] = "new"; continue
        pi, pc = before[card["title"]]
        if bool(card.get("hidden")) != bool(pc.get("hidden")): ch["cards"][ci] = "hidden" if card.get("hidden") else "back"
        was, now = [text(q) for q in pc["examples"]], [text(q) for q in card["examples"]]
        sources = [why(marks.get(f"ex:{pi}:{ei}", {})) for ei, t in enumerate(was)
                   if t not in now and not marks.get(f"ex:{pi}:{ei}", {}).get("deleted")]
        rewritten = len(sources)
        sources += [{"how": "added", **({"said": h} if h else {})} for h in adds.get(str(pi), [])]
        new = [ei for ei, t in enumerate(now) if t not in was]
        for ei, x in match(new, sources).items(): ch["items"][f"{ci}:{ei}"] = x
        gone = len([t for t in was if t not in now]) - min(rewritten, len(new))
        if gone: ch["removed"][ci] = gone
    key = lambda x: json.dumps(x, sort_keys=True, ensure_ascii=False)
    was, now = [key(x) for x in prev.get("firsts", [])], [key(x) for x in cur.get("firsts", [])]
    sources = [why(marks.get(f"first:{k}", {})) for k, x in enumerate(was) if x not in now and not marks.get(f"first:{k}", {}).get("deleted")]
    ch["firsts"] = match([k for k, x in enumerate(now) if x not in was], sources)
    if bool(cur.get("firsts_hidden")) != bool(prev.get("firsts_hidden")):
        ch["firstsSection"] = "hidden" if cur.get("firsts_hidden") else "back"
    a, b = (prev.get("persona") or {}).get("name"), (cur.get("persona") or {}).get("name")
    if a != b: ch["persona"] = "off" if not b else "changed"
    old, new = [p["name"] for p in personas(prev)], [p["name"] for p in personas(cur)]
    votes, said = fb.get("personaVotes", {}), fb.get("personaComments", {})
    for i, name in enumerate(new):
        if name in old: continue
        if i < len(old) and old[i] not in new: ch["newPersonas"][i] = why({"vote": votes.get(str(i)), "comment": said.get(str(i))})
        else: ch["newPersonas"][i] = {"how": "added" if fb.get("morePersonas") else "changed"}
    ch["count"] = (len(ch["items"]) + len(ch["firsts"]) + len(ch["cards"]) + sum(ch["removed"].values())
                   + bool(ch["persona"]) + len(ch["newPersonas"]) + bool(ch["firstsSection"]))
    return ch


def meta(work, v): return load(vpath(work, v)).get("_version", {})


def page(work, n, latest, embed=None):
    s = load(wpath(work, "stats.json"))
    c = load(vpath(work, n))
    m = c.pop("_version", {})
    out = render.build_page(s, c, render.load_prompts(wpath(work, "stats.json")), edit=True)
    frm = m.get("from")
    changes = None
    if frm and frm != n and os.path.exists(vpath(work, frm)):
        prev = load(vpath(work, frm)); prev.pop("_version", None)
        fb = load(fbpath(work, frm)) if os.path.exists(fbpath(work, frm)) else None
        changes = dict(diff(prev, c, fb), **{"from": frm})
    err = wpath(work, "error.json")
    state = {"version": n, "latest": latest, "embed": embed, "personas": personas(c),
             "persona": next((i for i, p in enumerate(personas(c)) if c.get("persona") and p["name"] == c["persona"]["name"]), None),
             "max": MAX_EXAMPLES, "maxPersonas": MAX_PERSONAS, "more": MORE_PERSONAS, "label": m.get("label", ""),
             "feedback": load(fbpath(work, n)) if os.path.exists(fbpath(work, n)) else None, "changes": changes,
             "error": load(err).get("message") if os.path.exists(err) else None,
             "versions": [{"n": v, **{k: x for k, x in meta(work, v).items() if k != "n"}} for v in versions(work)]}
    ui = open(os.path.join(render.ASSETS, "editor.html"), encoding="utf-8").read()
    js = json.dumps(state, ensure_ascii=False).replace("</", "<\\/")
    return out.replace("</body>", f"<script>window.EDIT={js}</script>{ui}</body>", 1)


def compare(a, b):
    return open(os.path.join(render.ASSETS, "compare.html"), encoding="utf-8").read().replace("{a}", str(a)).replace("{b}", str(b))


def serve(work, no_open, port=0):
    if not versions(work): snapshot(work, load(wpath(work, "cards.json")), "first draft")
    status = {"done": False}
    waiting = lambda: os.path.exists(wpath(work, "feedback.json")) or os.path.exists(wpath(work, "working"))

    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a): pass

        def send(self, code, body, kind="application/json"):
            data = body.encode("utf-8") if isinstance(body, str) else body
            self.send_response(code); self.send_header("Content-Type", kind + "; charset=utf-8")
            self.send_header("Cache-Control", "no-store"); self.send_header("Content-Length", str(len(data)))
            self.end_headers(); self.wfile.write(data)

        def error(self, code, message): self.send(code, json.dumps({"error": message}))

        def do_GET(self):
            u = urllib.parse.urlparse(self.path); vs = versions(work); q = urllib.parse.parse_qs(u.query)
            if u.path == "/favicon.ico": return self.send(204, "")
            if u.path == "/state":
                err = wpath(work, "error.json")
                return self.send(200, json.dumps({"latest": vs[-1], "waiting": waiting(), "done": status["done"],
                                                  "error": load(err).get("message") if os.path.exists(err) else None}))
            try:
                if u.path == "/compare":
                    a, b = int(q.get("a", [0])[0]), int(q.get("b", [0])[0])
                    if a not in vs or b not in vs: return self.send(404, "No such version.", "text/plain")
                    return self.send(200, compare(a, b), "text/html")
                if u.path != "/": return self.send(404, "{}")
                n = int(q.get("v", [vs[-1]])[0])
                if n not in vs: n = vs[-1]
                embed = q.get("embed", [None])[0]
                self.send(200, page(work, n, vs[-1], embed if embed in ("feedback", "changes") else None), "text/html")
            except (Exception, SystemExit) as e:
                self.send(500, f"<!doctype html><body style='font-family:sans-serif;padding:40px'>This version won't draw: "
                               f"{H.escape(str(e))}. Ask Claude in the chat to fix it.</body>", "text/html")

        def do_POST(self):
            if self.headers.get("Origin") not in (None, f"http://127.0.0.1:{port}"): return self.error(403, "Not allowed.")
            try: body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            except ValueError: return self.error(400, "That request didn't make sense.")
            if self.path == "/send":
                if waiting(): return self.error(409, "Claude is still working on the changes you sent.")
                try: result, fb = apply(work, body)
                except ValueError as e: return self.error(400, str(e))
                except Exception as e: return self.error(500, f"Your changes couldn't be saved ({e}).")
                rm(wpath(work, "error.json"))
                save(fbpath(work, int(body["version"])), body)
                if fb: save(wpath(work, "feedback.json"), fb)
                elif result.get("done"):
                    status["done"] = True
                    save(wpath(work, "feedback.json"), {"from_version": result["latest"], "done": True, "requests": [],
                                                        "liked": [], "note": "", "next": "Render cards.json: the person is happy with it"})
                return self.send(200, json.dumps(result))
            if self.path == "/cancel":
                rm(wpath(work, "feedback.json")); rm(wpath(work, "working"))
                return self.send(200, "{}")
            if self.path == "/restore":
                n = int(body["version"])
                if n not in versions(work): return self.error(404, "That version doesn't exist.")
                return self.send(200, json.dumps({"latest": snapshot(work, load(vpath(work, n)), f"back to v{n}", n)}))
            self.error(404, "Not found.")

    srv = http.server.ThreadingHTTPServer(("127.0.0.1", port), Handler)
    port = srv.server_address[1]
    url = f"http://127.0.0.1:{port}/"
    save(wpath(work, "editor.json"), {"url": url, "pid": os.getpid()})
    print(url, flush=True)
    if not no_open: threading.Timer(0.3, lambda: webbrowser.open(url)).start()
    srv.serve_forever()


def wait(work, timeout):
    path = wpath(work, "feedback.json")
    end = time.time() + timeout
    while not os.path.exists(path):
        if time.time() > end: sys.exit("No changes sent from the editor in time.")
        time.sleep(1)
    fb = load(path)
    done = os.path.join(work, "feedback"); os.makedirs(done, exist_ok=True)
    os.replace(path, os.path.join(done, f"{len(os.listdir(done)) + 1}.json"))
    if fb["requests"] or fb["note"]: save(wpath(work, "working"), {"from": fb["from_version"]})
    print(json.dumps(fb, ensure_ascii=False, indent=2))


def publish(work, label):
    c = load(wpath(work, "cards.json"))
    why = check(work, c)
    if why: sys.exit(f"Not published: {why} Fix cards.json and publish again, or run --fail to tell the person.")
    frm = load(wpath(work, "working")).get("from") if os.path.exists(wpath(work, "working")) else None
    n = snapshot(work, c, label, frm or (versions(work) or [None])[-1])
    rm(wpath(work, "working")); rm(wpath(work, "error.json"))
    print(f"v{n}")


def fail(work, message):
    save(wpath(work, "error.json"), {"message": message})
    rm(wpath(work, "working")); rm(wpath(work, "feedback.json"))
    print("Told the page.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("work")
    ap.add_argument("--wait", action="store_true", help="block until the person sends changes, then print them")
    ap.add_argument("--timeout", type=int, default=3600, help="seconds --wait waits (default 3600)")
    ap.add_argument("--publish", action="store_true", help="save cards.json as the next version")
    ap.add_argument("--label", default="Claude's changes")
    ap.add_argument("--fail", metavar="WHY", help="tell the page the next version could not be made, and why")
    ap.add_argument("--no-open", action="store_true")
    ap.add_argument("--port", type=int, default=0, help="port to serve on (default: any free one)")
    a = ap.parse_args()
    work = os.path.abspath(a.work)
    if a.wait: return wait(work, a.timeout)
    if a.publish: return publish(work, a.label)
    if a.fail: return fail(work, a.fail)
    serve(work, a.no_open, a.port)


if __name__ == "__main__":
    main()
