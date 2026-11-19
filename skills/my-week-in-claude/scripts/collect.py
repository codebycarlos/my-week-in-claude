#!/usr/bin/env python3
"""Measure a week of Claude Code and Cowork use from the local session logs.

Writes stats.json (counts, shares per model and per place work was written to, firsts), prompts.json (every
prompt you typed that led to real work) and signals.json (habits for the five ideas).
Nothing leaves the machine.
"""
import argparse, collections, datetime as dt, glob, json, os, pathlib, re, sys

# Where a prompt's work ended up. Every connector Claude wrote to (Slack, Gmail, HubSpot...) is a
# place of its own, named after the app.
CATS = {
    "answer": "Looked into, answered in the chat",
    "code": "Code committed or pushed",
    "documents": "Documents and files written",
    "pages": "Pages and mock-ups published",
}
COWORK_INTERNAL = {"workspace", "cowork", "cowork-onboarding", "mcp-registry", "plugins", "scheduled-tasks", "skills",
                   "visualize", "computer-use", "Claude in Chrome"}
SKIP_PREFIXES = ("<command", "<local-command", "<bash-input", "<bash-stdout", "<bash-stderr", "<task-notification", "<system-reminder",
                 "[Request interrupted", "Caveat:")


VERBS = {"get", "list", "search", "read", "fetch", "find", "query", "create", "update", "delete", "send", "add",
         "set", "post", "save", "upload", "download", "edit", "write", "move", "remove", "mark", "apply", "run"}


def connector(tool):
    """The app a connector tool belongs to, or None for Claude's own internal servers."""
    server, name = tool.split("__")[1], tool.split("__")[-1]
    if re.fullmatch(r"[0-9a-fA-F-]{30,}", server):
        # Cowork names a connector's server by an id, so take the app from the tool's own prefix.
        first = re.split(r"[_-]", name)[0].lower()
        return first.title() if first and first not in VERBS | {"dispatch"} else None
    if server.startswith("ccd_") or server in COWORK_INTERNAL: return None
    server = re.sub(r"^(claude_ai_|plugin_[^_]+_)", "", server).replace("_", " ")
    return server.title() if server.islower() else server


WRITES = re.compile(r"(^|[_-])(send|save|create|update|post|publish|reply|draft|add|upload|edit|write|delete|set|merge|comment|schedule|move|duplicate)", re.I)
GIT_WRITE = re.compile(r"\bgit (commit|push)\b|\bgh (pr|issue|release) (create|edit|merge|comment|review|close)\b|\bgh api\b.*(-X|--method) ?(POST|PATCH|PUT)")
DOCUMENT = re.compile(r"\.(md|txt|docx?|pdf|csv|xlsx?|pptx?|html?|rtf|png|jpe?g|gif|svg|webp)$", re.I)
SCRATCH = re.compile(r"^(/private)?/tmp/|/\.claude/")


def output(tools):
    """Where one API call wrote something: a connector's app, "code", "documents" or "pages".
    None when it only read, searched or ran commands."""
    for n, inp in tools:
        if n.endswith("__bash"): n = "Bash"
        if n.startswith("mcp__") and connector(n) and WRITES.search(n.split("__")[-1]): return connector(n)
        if n == "Artifact" and inp.get("action", "publish") == "publish" or n == "DesignSync": return "pages"
        if n == "Bash" and GIT_WRITE.search(str(inp.get("command", ""))): return "code"
        if n in ("Edit", "Write", "MultiEdit", "NotebookEdit"):
            path = str(inp.get("file_path") or inp.get("notebook_path") or "")
            if path and not SCRATCH.search(path): return "documents" if DOCUMENT.search(path) else "code"
    return None


def apps_used(tools):
    """Every app one API call read from or wrote to: connectors, the web and GitHub."""
    found = []
    for n, inp in tools:
        if n.startswith("mcp__") and connector(n): found.append(connector(n))
        elif n in ("WebSearch", "WebFetch"): found.append("Web")
        elif n in ("Bash", "mcp__workspace__bash") and re.search(r"\bgh ", str(inp.get("command", ""))): found.append("GitHub")
    return found


def prompt_text(msg):
    c = msg.get("content")
    if isinstance(c, str): return c
    if isinstance(c, list):
        return " ".join(x.get("text", "") for x in c if isinstance(x, dict) and x.get("type") == "text")
    return ""


def is_typed_prompt(d, text):
    if d.get("isMeta") or d.get("toolUseResult") or d.get("tool_use_result") or d.get("isSidechain"): return False
    t = text.lstrip()
    return bool(t) and not t.startswith(SKIP_PREFIXES) and "This session is being continued" not in t


def model_name(m):
    hit = re.search(r"claude-([a-z]+)-(\d+)-(\d+)", m or "")
    return f"{hit.group(1).title()} {hit.group(2)}.{hit.group(3)}" if hit else "Other model"


BUILTIN = {"Agent": "Subagents", "Task": "Subagents", "Workflow": "Workflows", "Artifact": "Artifacts",
           "WebSearch": "Web search", "WebFetch": "Reading web pages", "NotebookEdit": "Notebooks",
           "ScheduleWakeup": "Loops", "CronCreate": "Scheduled tasks", "Monitor": "Monitoring commands",
           "EnterWorktree": "Worktrees", "EnterPlanMode": "Plan mode", "PublishPlugin": "Publishing plugins"}


def own_skill(name, skill_dirs):
    """A skill the person installed or wrote, by its display name. Built-in skills Claude loads for
    itself (workflow-authoring, claude-api) return None: they mean nothing to a reader."""
    if ":" in name:
        plugin, skill = name.split(":", 1)
        if plugin == "anthropic-skills": return None
        return skill if skill == plugin else name
    return name if any(os.path.isdir(os.path.join(d, name)) for d in skill_dirs) else None


def features(name, inp, skill_dirs):
    """What a tool call shows the person knows how to use: a connector, a skill or a built-in feature."""
    if name.startswith("mcp__"):
        return [("Connector", connector(name))] if connector(name) else []
    if name == "Skill" and inp.get("skill"):
        skill = own_skill(inp["skill"], skill_dirs)
        return [("Skill", skill)] if skill else []
    if name in BUILTIN:
        return [("Feature", BUILTIN[name])]
    return []


def slash_skills(text, skill_dirs):
    """Skills started with a slash command: plugin skills (plugin:skill) and the person's own."""
    out = []
    for name in re.findall(r"<command-name>/?([^<\s]+)</command-name>", text):
        skill = own_skill(name, skill_dirs)
        if skill: out.append(("Skill", skill))
    return out


def note(example, key, ts, prompt):
    if prompt and (key not in example or ts < example[key][0]): example[key] = (ts, prompt)


def clean(text):
    text = re.sub(r"<pasted_content[^>]*>.*?</pasted_content[^>]*>", "[pasted]", text, flags=re.S)
    return " ".join(text.split())


CORRECTION = re.compile(r"^(no\b|nope|wrong|that'?s not|not what|why did you|why didn'?t you|you didn'?t|you forgot|"
                        r"stop\b|undo|revert|i said|i told you|again\?)", re.I)
GO_AHEAD = re.compile(r"^((y|yes|yep|yeah|ok|okay|sure|go|go ahead|go for it|do it|continue|proceed|carry on|sounds good|lgtm|please|thanks|thank you)[.!, ]*)+$", re.I)


def signals(sig, text):
    """Habits worth a tip: corrections, bare go-aheads, pasted text and openings typed again and again."""
    plain = re.sub(r"<pasted_content[^>]*>.*?</pasted_content[^>]*>", " ", text, flags=re.S)
    flat = " ".join(plain.split())
    if GO_AHEAD.match(flat): sig["go_ahead"] += 1
    if CORRECTION.match(flat): sig["corrections"].append(flat)
    for block in re.findall(r"<pasted_content[^>]*>(.*?)</pasted_content[^>]*>", text, flags=re.S):
        sig["pastes"].append(" ".join(block.split())[:300])
    words = re.findall(r"[a-z']+", flat.lower())
    if len(words) >= 5: sig["openings"][" ".join(words[:5])] += 1


def accounts(cowork_root):
    """Each signed-in account's sessions, as {account id: [email, session ids]}, from every config folder and the desktop app."""
    acc = {}
    home = os.path.expanduser("~")
    dirs = {os.path.join(home, ".claude"): os.path.join(home, ".claude.json")}
    for d in glob.glob(os.path.join(home, ".claude-*")) + [os.environ.get("CLAUDE_CONFIG_DIR", "")]:
        if os.path.isdir(d): dirs[os.path.normpath(d)] = os.path.join(d, ".claude.json")
    for d, cfg in dirs.items():
        try: o = json.load(open(cfg, encoding="utf-8")).get("oauthAccount") or {}
        except (OSError, ValueError): continue
        if not o.get("accountUuid"): continue
        ids = acc.setdefault(o["accountUuid"], [o.get("emailAddress") or "this account", set()])[1]
        try:
            for line in open(os.path.join(d, "history.jsonl"), encoding="utf-8", errors="ignore"):
                try: ids.add(json.loads(line).get("sessionId"))
                except ValueError: pass
        except OSError: pass
    app = os.path.join(os.path.dirname(cowork_root), "claude-code-sessions")
    for f in glob.glob(os.path.join(app, "*", "*", "*.json")):
        try: sid = json.load(open(f, encoding="utf-8")).get("cliSessionId")
        except (OSError, ValueError): continue
        acc.setdefault(pathlib.PurePath(os.path.relpath(f, app)).parts[0], ["this account", set()])[1].add(sid)
    for f in glob.glob(os.path.join(cowork_root, "*", "*", "*", "audit.jsonl")):
        parts = pathlib.PurePath(os.path.relpath(f, cowork_root)).parts
        acc.setdefault(parts[0], ["this account", set()])[1].add(parts[2])
    return acc


def pct(n, d): return max(1, round(100 * n / d)) if n and d else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--projects", default=os.path.join(os.environ.get("CLAUDE_CONFIG_DIR", os.path.expanduser("~/.claude")), "projects"))
    ap.add_argument("--cowork", default=os.path.expanduser(
        "~/Library/Application Support/Claude/local-agent-mode-sessions" if sys.platform == "darwin" else
        os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~/AppData/Roaming"), "Claude", "local-agent-mode-sessions") if os.name == "nt" else
        "~/.config/Claude/local-agent-mode-sessions"), help="Cowork's session folder")
    ap.add_argument("--history", help="history.jsonl of one account, to count only that account's sessions")
    ap.add_argument("--session", help="this conversation's session id, to leave out other accounts' sessions")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    until = dt.datetime.now().astimezone()
    since = (until - dt.timedelta(days=a.days)).replace(hour=0, minute=0, second=0, microsecond=0)
    since_s = since.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    only = None; others = set()
    if a.history:
        only = set()
        for line in open(a.history, encoding="utf-8", errors="ignore"):
            try: only.add(json.loads(line).get("sessionId"))
            except ValueError: pass
    elif a.session:
        acc = accounts(a.cowork)
        mine = next((v for v in acc.values() if a.session in v[1]), None)
        if mine and len(acc) > 1:
            others = set().union(*(v[1] for v in acc.values() if v is not mine)) - mine[1]
            print(f"Leaving out sessions from accounts other than {mine[0]}, the one this conversation runs in.")

    root = os.path.normpath(a.projects)
    skill_dirs = [os.path.join(os.path.dirname(root), "skills"), os.path.expanduser("~/.claude/skills")]
    seen = set()
    total = 0
    models = {"main": collections.Counter(), "sub": collections.Counter()}
    sessions = {}  # sid -> {"prompts": [(ts, text)], "calls": [(ts, wrote to, apps, tokens)]}
    sent = 0; received = set()
    first_seen = {}; used_now = set(); agents_per_msg = collections.Counter(); earliest = None
    sig = {"interrupted": 0, "compacted": 0, "go_ahead": 0, "corrections": [], "pastes": [],
           "openings": collections.Counter()}
    compacted = set()
    example = {}  # feature, or ("agents", message id) -> (ts, the typed prompt that led to it)

    logs = [(f, rel[1].removesuffix(".jsonl"), "subagents" in rel, False)
            for f in glob.glob(os.path.join(root, "*", "*.jsonl")) + glob.glob(os.path.join(root, "*", "*", "subagents", "**", "*.jsonl"), recursive=True)
            for rel in [pathlib.PurePath(os.path.relpath(f, root)).parts]]
    logs += [(f, os.path.basename(os.path.dirname(f)), False, True)
             for f in glob.glob(os.path.join(a.cowork, "**", "audit.jsonl"), recursive=True)]
    for f, sid, is_sub, cowork in logs:
        counted = sid not in others and (only is None or sid in only or (cowork and bool(a.history)))
        S = sessions.setdefault(sid, {"prompts": [], "calls": []})
        calls = collections.OrderedDict(); last_prompt = None
        for line in open(f, encoding="utf-8", errors="ignore"):
            try: d = json.loads(line)
            except ValueError: continue
            m = d.get("message") or {}
            ts = d.get("timestamp") or d.get("_audit_timestamp") or ""
            if cowork and (d.get("parent_tool_use_id") or d.get("isReplay")): continue
            if ts and (earliest is None or ts < earliest): earliest = ts
            if d.get("type") == "user" and not is_sub and is_typed_prompt(d, prompt_text(m)):
                last_prompt = prompt_text(m)
            if d.get("type") == "user" and not is_sub:
                for ft in slash_skills(prompt_text(m), skill_dirs):
                    if ft not in first_seen or ts < first_seen[ft]: first_seen[ft] = ts
                    if counted and ts >= since_s: used_now.add(ft); note(example, ft, ts, last_prompt)
            if d.get("type") == "assistant":
                for c in m.get("content") or []:
                    if isinstance(c, dict) and c.get("type") == "tool_use":
                        if counted and ts >= since_s and c.get("name") in ("Agent", "Task"):
                            agents_per_msg[m.get("id")] += 1; note(example, ("agents", m.get("id")), ts, last_prompt)
                        for ft in features(c.get("name", ""), c.get("input") or {}, skill_dirs) + (
                                [("Model", model_name(m.get("model")))] if (m.get("model") or "").startswith("claude") else []):
                            if ts and (ft not in first_seen or ts < first_seen[ft]): first_seen[ft] = ts
                            if counted and ts >= since_s: used_now.add(ft); note(example, ft, ts, last_prompt)
            if ts < since_s or not counted: continue
            if d.get("type") == "user" and not is_sub:
                text = prompt_text(m)
                if text.lstrip().startswith("[Request interrupted"): sig["interrupted"] += 1
                if d.get("isCompactSummary"): compacted.add(d.get("uuid"))
                if is_typed_prompt(d, text):
                    sent += 1; S["prompts"].append((ts, text)); signals(sig, text)
            if d.get("type") != "assistant": continue
            if not is_sub and not d.get("isSidechain") and any(
                    isinstance(x, dict) and x.get("type") == "text" and x.get("text", "").strip()
                    for x in m.get("content") or []):
                received.add(m.get("id"))
            k = (m.get("id"), d.get("requestId") or d.get("request_id"))
            e = calls.setdefault(k, {"ts": ts, "u": None, "tools": [], "model": m.get("model"), "effort": d.get("effort")})
            if m.get("usage"): e["u"] = m["usage"]
            if d.get("effort"): e["effort"] = d["effort"]
            for c in m.get("content") or []:
                if isinstance(c, dict) and c.get("type") == "tool_use":
                    e["tools"].append((c.get("name", ""), c.get("input") or {}))
        for k, e in calls.items():
            u = e["u"]
            if not u or k in seen or (e["model"] or "").startswith("<"): continue
            seen.add(k)
            ctx = sum(u.get(x, 0) or 0 for x in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"))
            out = u.get("output_tokens", 0) or 0
            models["sub" if is_sub else "main"][(model_name(e["model"]), e["effort"] or "default")] += ctx + out
            S["calls"].append((e["ts"], output(e["tools"]), apps_used(e["tools"]), ctx + out))
            total += ctx + out

    # Each prompt owns the work up to the next one. Its place is where that work wrote most often,
    # or "answer" when it wrote nowhere. A bare go-ahead's work goes to the prompt before it.
    prompts = []
    for sid, S in sessions.items():
        pr = sorted(S["prompts"]); last = None
        for i, (ts, text) in enumerate(pr):
            end = pr[i + 1][0] if i + 1 < len(pr) else "9"
            wrote = collections.Counter(); apps = collections.Counter(); tot = 0
            for cts, w, used, tok in S["calls"]:
                if ts <= cts < end:
                    tot += tok; apps.update(used)
                    if w: wrote[w] += 1
            text = " ".join(re.sub(r"<pasted_content[^>]*>.*?</pasted_content[^>]*>", "[pasted]", text, flags=re.S).split())
            if (not text or GO_AHEAD.match(text)) and last:
                last["tokens"] += tot; last["wrote"] = sorted(set(last["wrote"]) | set(wrote))
                last["apps"] += [x for x, _ in apps.most_common() if x not in last["apps"]]; continue
            if not text: continue
            last = {"place": wrote.most_common(1)[0][0] if wrote else "answer", "wrote": sorted(wrote),
                    "apps": [x for x, _ in apps.most_common()], "session": sid[:8], "tokens": tot, "text": text}
            prompts.append(last)
    prompts.sort(key=lambda p: (p["place"], p["session"]))
    for i, p in enumerate(prompts): p["id"] = i
    cats = collections.Counter()
    for p in prompts: cats[p["place"]] += p["tokens"]

    mtot = {g: sum(v.values()) for g, v in models.items()}
    top = max(agents_per_msg, key=agents_per_msg.get, default=None)
    stats = {
        "since": since.date().isoformat(), "until": until.date().isoformat(),
        "sessions": sum(1 for S in sessions.values() if S["prompts"]),
        "messages_sent": sent, "messages_received": len(received),
        "tokens": total,
        "places": [{"key": k, "label": CATS.get(k, f"Written to {k}"), "tokens": v, "share": pct(v, total)}
                   for k, v in cats.most_common()],
        # Empty when the logs start inside the window: there is nothing older to compare against.
        "new_this_week": [{"item": f"{k}: {v}", "example": clean(example[(k, v)][1]) if (k, v) in example else None}
                          for (k, v) in sorted(used_now) if first_seen[(k, v)] >= since_s]
                         if earliest and earliest < since_s else [],
        "used_ever": sorted(f"{k}: {v}" for (k, v) in first_seen),
        "most_agents_at_once": max(agents_per_msg.values(), default=0),
        "most_agents_example": clean(example[("agents", top)][1]) if ("agents", top) in example else None,
        "logs_start": (earliest or "")[:10],
        "models": {g: {"share": pct(mtot[g], total),
                       "rows": [{"model": mo, "effort": ef, "share": pct(t, total)}
                                for (mo, ef), t in v.most_common() if pct(t, total) >= 1]}
                   for g, v in models.items()},
    }

    os.makedirs(a.out, exist_ok=True)
    json.dump(stats, open(os.path.join(a.out, "stats.json"), "w", encoding="utf-8"), indent=1)
    with open(os.path.join(a.out, "prompts.json"), "w", encoding="utf-8") as f:
        f.write("[\n" + ",\n".join(json.dumps({k: p[k] for k in ("id", "place", "wrote", "apps", "session", "tokens", "text")}, ensure_ascii=False)
                                     for p in prompts) + "\n]\n")
    # Private working notes for the tips: never published or put on the image.
    sig["compacted"] = len(compacted)
    sig["openings"] = [{"opening": k, "times": v} for k, v in sig["openings"].most_common() if v >= 3]
    json.dump(sig, open(os.path.join(a.out, "signals.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(f"{stats['sessions']} conversations, {sent} messages sent, {len(prompts)} prompts -> {a.out}")
    for c in stats["places"]:
        print(f"  {c['key']:12} {c['share']:3}%")


if __name__ == "__main__":
    main()
