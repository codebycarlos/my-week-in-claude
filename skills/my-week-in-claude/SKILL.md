---
name: my-week-in-claude
description: Makes "My week in Claude", a shareable image and PDF of a person's last week with Claude, with real prompts and five private ideas. Use for "my week in Claude", a weekly recap or usage wrapped.
---

# My week in Claude

Make one page a person can share with anyone, as an image and a PDF, so readers pick up ideas from how they use Claude.
The reader can be anyone, and so can the author. Two
things matter above everything else:

- **Useful.** A reader should come away with something new to try, in the author's own words.
- **Safe.** Nothing on the image can embarrass the author, a colleague or the company.

The image and the PDF hold the same page, and "the image" below means both. The PDF lets
readers select and copy the prompts. The image shows shares of the week, never totals, so nobody compares how much anyone used. The
person also gets five ideas for working better, in the chat only. `examples/` holds a finished
image and PDF, and the `stats.json` and `cards.json` it was made from.

Everything is read from the Claude Code session logs on this machine, Cowork's included. Nothing
is uploaded anywhere else.

## Welcome

This skill runs only in Claude Code, in a terminal or the desktop app's Code tab. Anywhere else,
such as Cowork or a chat on claude.ai, skip the welcome: say in one line that it runs in Claude
Code, where their Cowork work is counted too, tell them to ask for "my week in Claude" there, and
stop.

Before anything else, ask with the question tool whether to go ahead, with this welcome as the
question, copied exactly.

> Ready to see your week in Claude? It's like Spotify Wrapped for your last week with Claude. You get an
> image and a PDF to share, with a section for each kind of work and your own prompts as examples anyone could
> copy, plus five ideas for working better that stay in this chat. I read your week from the
> session logs on this machine, take out names and private details, and follow any AI policy that
> applies to you. Nothing is posted anywhere. It takes about 5 minutes, and uses about as many
> tokens as a longish conversation. (v1.0.18)

The options are "Start" and "Not now". Wait for "Start" before anything else, the checks below
included.

## Get everything set up

The scripts need Python 3.9 or newer and nothing else from Python. Rendering needs Google Chrome
or Chromium, which draws the image and the PDF in the background, and an internet connection for the fonts and
app icons.

Check with `python3 --version`, and look for Chrome or Chromium. To the person, this step is
"Getting everything set up": never name Python, Chrome or any other tool in your updates or task
list unless one is missing. If something is missing, tell the person what it is and what it is for, and offer to install it
with the question tool. Install only
after they say yes, with the usual tool for their system (Homebrew on a Mac, `winget` on Windows,
the package manager on Linux). If they would rather not, stop and say what they need.

## Keep them posted

If you keep a task list, name its steps by this file's headings, such as "Get everything set up"
and "Check relevant AI policies", and never assume the person works for a company. Mark a step in
progress when it starts and done when it finishes. The policy check starts together with
measuring, so both are in progress at once.

Before each step from here on, give the person one short, light line saying what you are doing,
so the wait feels like part of the fun. Write your own each time, in the spirit of these:

- Setting up: "Getting everything set up."
- Measuring: "Reading your week. This is the long bit."
- Writing the card: "Sorting your prompts into piles. Some piles are taller than others."
- Redacting: "Taking the names out. Your colleagues will never know they were here."
- Persona: "Working out who you were this week."
- Rendering: "Drawing your image. Nearly there."

Tease the work or the tools, never the person, and never how much they used Claude. One line
each, and nothing that reveals a prompt before the final check.

## Ground rules for the run

- **Keep the working files private.** `prompts.json` holds every prompt in full. Make the work
  folder a new temporary folder (`python3 -c "import tempfile; print(tempfile.mkdtemp())"`),
  never inside a project or a synced folder, and delete it once the person is happy with the
  image, without mentioning it.
- **Run the scripts from this skill's folder.** That is `${CLAUDE_SKILL_DIR}`. If you read this
  file straight from disk and that shows as written, it is the folder holding this file, and
  `collect.py` works out the session itself when `--session` is left out.

## 1. Measure

Work in parallel where you can. As you run this command, start a subagent on "Check relevant AI
policies", the section after it. Wait for its report before step 2, and mark the policy check done
when it arrives.

```sh
python3 "${CLAUDE_SKILL_DIR}/scripts/collect.py" --session ${CLAUDE_SESSION_ID} --out <work dir>
```

`--session` leaves out sessions from any other Claude account on the machine, so the image covers
only the account this conversation runs in. Trust it, and don't ask the person which account to
cover. `--days N` changes the window (default 7). `CLAUDE_CONFIG_DIR` is
honoured.

It writes three files:

| File | Holds |
|------|-------|
| `stats.json` | The window, conversation and message counts, the share of the week per model and per place the work went (`places`), `new_this_week`, `most_agents_at_once` and `used_ever` |
| `prompts.json` | Every prompt they typed in full (runs started by a script or a schedule, such as `claude -p`, and messages from other agents are left out), in order within each conversation, with its `id`, `place` (where the work after it went), `wrote` (every place it wrote to), `apps` (every app its work drew on), `session` and `tokens` (how much work followed it). Pasted text shows as `[pasted]` |
| `signals.json` | Habits for the five ideas: corrections, bare go-aheads, pasted text, repeated openings, interruptions, and `compacted`, the number of times a conversation of theirs grew so long Claude had to summarise it to carry on. Never goes on the image |

A prompt's `place` is where the work after it was written most often. Every app Claude wrote to
through a connector is a place of its own, named after the app (Slack, Gmail, HubSpot). The rest
are `code` (code committed, pushed or edited), `documents` (documents, sheets, images and other
files written), `pages` (pages and mock-ups published) and `answer`, where Claude looked things up
or ran checks and wrote nowhere but the chat. A bare go-ahead's work counts towards the prompt
before it. `--cowork <folder>` points at Cowork's sessions if they are somewhere unusual.

### Check relevant AI policies

Look for any AI policy that applies to the person, and apply it to everything on the image in
step 2. Search the document apps you
can reach (Notion, Confluence, Google Drive, SharePoint) for "AI policy" or "AI use", and read
what you find, pages it links to included. Keep the title and link of each policy you check the
prompts against. If you find none, carry on without one and warn the person at the end.

Leave out any prompt that shows a use the policy rules out or limits, such as:

- customer content, personal or health data, or confidential figures given to Claude
- secrets or security findings pasted in
- an AI tool the policy has not approved

Follow the policy's rules on what may be shared, too. In step 6, show the prompts you left out
for the policy in a table, one row each: what the prompt was about, and why the policy rules it
out, naming the rule.

## 2. Write and redact the card

Read all of `prompts.json`, in parts if it is too long for one read, and write `cards.json` in the shape of `examples/cards.json`: `name`, `cards` (each with `title`,
`places`, `moved` and `examples`), `personas`, `persona` and `firsts`. The image is one card, and
each entry in `cards` is a section on it. This step takes the most judgement.

- **One section per place the work went**, largest first. Merge two places into one section when they
  are the same work to a reader. Drop one under 1% unless it has a striking example.
- **`places`** lists the places a section covers, spelt exactly as in `stats.json`. A section's share is
  the work after every prompt filed on it. `render.py` stops on a place it does not know.
- **`moved`** lists the `id` of each prompt whose output was meant for another section but never
  reached it, and its work moves with it. A Slack message drafted in the chat for the person to
  paste has the place `answer`, and belongs in the Slack section. Read the text to decide, and give a
  section for such prompts an empty `places`.
- **Title each section in everyday words**, starting with an -ing verb and saying what was made and
  where: "Drafting tickets in Linear", "Looking into things and answering questions".
- **Call writing "drafting".** For documents, tickets, messages and code, the title says
  "Drafting": "Drafting Notion pages", never "Writing pages in Notion". People rework, review and
  own what goes out, and the image must not suggest Claude did that work for them.
- **Put each example in the section that holds its prompt**, by its `place` or by `moved`.
- **Pick two to five examples per section** that show a reader something they had not thought to ask
  Claude. Skip routine prompts ("yes", "try again").
- **Order them by how reusable they are.** First the prompt a colleague could use in many
  situations, last the one tied to a single event.
- **Quote, then trim.** Keep the person's words. Cut with `…`, join a follow-up from the same
  `session` with `→` in the section of the first prompt, fix
  typos, and add context in `[square brackets]` where a quote would not make sense alone. Explain
  jargon the same way, or trim it out: a reader who has never used Claude Code should follow
  every line.
- **Each example is `{"text", "apps"}`.** `apps` lists every app its work drew on: the prompt's
  `apps` from `prompts.json`, plus any app the prompt names that the logs cannot see (a browser,
  Windows). The renderer shows their logos after the quote, so a reader sees one prompt pulling
  from Slack, Notion and the web to write one ticket. Name each app as people know it ("Slack", "Excel", "Google Drive"), and the
  renderer finds its logo in [Iconify](https://iconify.design)'s full-colour sets. An app it
  cannot find gets a letter tile: give `{"name": "...", "colour": "#hex"}` to colour it.
- **`name`** is the person's name, which the renderer shortens to first name and initial. Use the
  one you know from the conversation or their account, and ask if you don't.

**`firsts`** fills "New this week": one to five tiles of `{"kind", "name", "detail", "example"}`.

- `kind` is a short label above the name: "New skill", "New connector", "First time" or
  "Personal best".
- Take them from `new_this_week`. Add "Personal best: N agents at once" when
  `most_agents_at_once`, the most started in one go this week, is 5 or more. Leave `firsts` out
  when there is nothing new.
- `detail` says in one short sentence what the thing does.
- `example` is the prompt that led to it. `new_this_week` gives the last prompt typed before the
  first use, which may not show the thing at work, so look nearby in `prompts.json` for a better
  one. Leave it out rather than repeat a section's prompt or force a weak one.

**`personas`** holds three, each `{"name", "line"}`, and **`persona`** is the one the person picks
in step 3, left out when they want none.

The joke lives in their data, not in a punchline added after it. A line that states a fact and then
reaches for a witty kicker is the obvious version, and everyone can see it coming. Find the facts
that are already funny side by side, put the funniest one last, and stop.

The name is "The" and a role the habit earns, one to three words: a job, never an adjective ("The
Incident Commander", "The Second Opinion", not "The Efficient One"). The line talks to them as
"you", under 30 words. Every fact in it is true and comes from their week.

Write them in three passes, and put only the three you keep in the file:

1. **Find the material.** List fifteen or more specific things from their week: a number from
   `stats.json`, a phrase they kept typing, a request few people would make, two requests days
   apart that clash in size or tone. Skip anything true of most people who use Claude.
2. **Draft twenty lines**, at least four in each of these shapes:
   - **Escalation.** Three of their real requests in a row, each sillier than the last, and the
     silliest one ends the line.
   - **Clash.** Two true things side by side that should not sit together: ten agents on an outage,
     then the whole commit history on tabs against spaces.
   - **Their words against their week.** A phrase they typed, next to a request or a count that
     really contradicts it. If the contradiction needs explaining, it is not there.
   - **Deadpan.** One true fact strange enough on its own, told flat, with nothing after it.

   For each line, write the first ending that comes to mind, then throw it away and write another:
   the first one is the one any reader would guess.
3. **Keep three, from three different habits and at least two different shapes.** If you can start a
   subagent, give it the twenty lines and the tests below, and keep the three it picks: a reader who
   did not write them laughs at different ones. Keep a line only if it passes all of these:
   - **Can't guess the end.** Cover the second half. If you could have written it yourself, cut it.
   - **Only them.** If it would fit most people who use Claude, it is a horoscope.
   - **The surprise comes last.** Cut anything after the word that makes it funny.
   - **Kind.** It teases a habit they would laugh at themselves. Nothing about their skill, effort
     or judgement, nothing suggesting Claude did their job, nothing on how much or when they used it.
   - **No stock shapes.** None of these:
     - an object or idea acting like a person ("Jargon has filed a complaint", "That PR has never
       felt so seen", "The bug didn't stand a chance")
     - a pun, or a second meaning of a word already in the line
     - an ending that explains the joke, or rates the person ("Management material", "Iconic")
     - a stock closer ("Are you OK?", "Rough week?", "Say more.", "Who hurt you?")
     - "X isn't a Y, it's a Z", "...is a lifestyle", "main character", "the real MVP", "chef's
       kiss", "living rent free", "somebody has learned", an emoji

   If fewer than three pass, draft more rather than lower the bar.

Two that pass, from `examples/cards.json`. They show the bar, not a template: copy their shape and
the line reads like theirs, not the person's.

- The Incident Commander (escalation): "Ten agents on a failing build. Five on a bug that might not
  exist. The entire commit history on tabs versus spaces."
- The Second Opinion (deadpan): "Before opening your own pull request, you had five agents review it
  from different angles."

### Redact

Go through everything that goes on the image: every example, section titles, the persona, each
`firsts` tile, and the app and model names. A custom connector or a model name can carry a company
or account name.

Take the whole prompt out when it touches:

- someone's performance, pay, hiring, leaving, health or personal life
- feelings, disagreements, or blame aimed at a colleague, team or customer
- private remarks between people, such as pet names or jokes at someone's expense
- who has, needs or was given access to a system
- legal matters, deals, prices or figures not yet public, funding or restructuring
- unfixed security weaknesses
- the author's personal life, or when and how long they work

Replace, and keep the rest:

| Found | Becomes |
|-------|---------|
| A colleague's name | Their role: `[a colleague]`, `[the designer]`, `[my manager]` |
| A customer, user or partner | `[a customer]`, `[a partner]` |
| The author's company or any other organisation | `[my company]`, `[a supplier]` |
| The company's products, features and project names | `[our app]`, `[the new feature]` |
| Terms only the company uses | What they mean: `[company goal]` |
| Links, ticket numbers, file paths, channel names, emails, usernames, phone and account numbers | Removed, or described: `[the team's channel]` |
| Keys, passwords, tokens | Removed, and tell the author |
| Pasted text, or a colleague's words typed in | What it was: `[meeting notes, pasted in]`, `[their message]` |

Third-party tools keep their names (Slack, Figma, Excel), since they say nothing about where the
author works. `render.py` lists every capitalised word that may be a name: check each one.

## 3. Pick the persona

Ask the person to choose one of the three with the question tool, the line as each option's
description, and "No persona" as the last option, which leaves `persona` out of `cards.json`.
They can write their own. They can change their mind in edit mode, in step 6.

## 4. Render

```sh
python3 "${CLAUDE_SKILL_DIR}/scripts/render.py" <work dir>/stats.json <work dir>/cards.json
```

It makes a new folder in `~/Downloads/my-week-in-claude/`, named after the week and the time, so
earlier weeks are kept. The folder holds a PNG and a PDF of the same name. It prints the PNG's
path, then the PDF's, then the folder's last. When you render again in step 6, pass the folder
with `--out` so the run keeps one folder.

It uses Google Chrome or Chromium, and an internet connection for the fonts and app logos. Open
the PNG and read it: every example has its app logos, no quote runs past three lines, and nothing the redaction
should have caught got through.

## 5. Hand over the image, the PDF and five ideas

Put the image in front of the person before anything else:

- **Open it for them.** Run `open <png>` on a Mac, `start "" <png>` on Windows or
  `xdg-open <png>` on Linux, so it appears in their image viewer.
- **Give links they can click**, each on its own line, for the PNG and the PDF: a markdown link
  whose text is the file name and whose target is the full path as a `file://` address, such as
  `[my-week-in-claude-2026-w47-19nov-232511.png](file:///Users/sam/Downloads/my-week-in-claude/my-week-in-claude-2026-w47-19nov-232511/my-week-in-claude-2026-w47-19nov-232511.png)`.
  Say in one line that the image suits a post or a message, and the PDF lets readers copy the
  prompts. If render.py printed no PDF, give the image alone.

Then give five numbered ideas for working better with Claude, in the chat. Each
one names what you saw in their week (a number or a short quote), says what to change, and ends
with a prompt they can paste.

Look for:

- **A procedure they repeat:** the same steps asked for across sessions in `prompts.json`, or an
  opening in `signals.json` typed three times or more. It could be a skill.
- **Text carried in by hand:** `pastes` holding messages, documents, tickets or meeting notes from
  an app Claude could read with a connector. Compare the connectors you can see with `used_ever`.
- **Corrections that repeat:** the same correction twice belongs in their instructions or memory.
- **Long conversations:** `compacted` and `interrupted` suggest a fresh conversation per task, or
  a written plan to start from.
- **Bare go-aheads:** many in `go_ahead` suggest allowing routine actions in settings, or asking
  for the whole job up front.
- **Work done one piece at a time** that several agents could do at once.
- **Something weekly** that could run on a schedule.
- **A feature or skill they have never used** that fits their week, from `used_ever`.

Base every idea on what is in the files, and give fewer than five rather than pad.

## 6. Final check

List every example on the image, section by section. Then give the AI policies:

- **If you found any**, a table of the policies you checked the prompts against, one row each,
  with its title linked to the page. Under it, the table of prompts left out for a policy, if any.
- **If you found none**, a warning on its own line: no AI policy was found in the apps you could
  search, so the prompts were checked only for names and private details, and they should check
  any policy that applies to them before sharing.

Then open edit mode, an optional page on this machine only where they can change the card
themselves. The image and the PDF from step 5 are already final, so the run is finished whether
they use it, close it or ignore it. Run this in the background:

```sh
python3 "${CLAUDE_SKILL_DIR}/scripts/edit.py" <work dir>
```

It opens the page in their browser and prints its address, and it stops by itself once no page has
been open for 10 minutes. Close your reply with the links to the image and the PDF, the edit-mode
link, and one line saying what they can do there: flick between the personas, vote on them or ask for more, turn the persona
off, give each example a thumbs up or down, ask for one to be anonymised further, leave a note on any of them, remove one
or add more (up to 10 a section), hide a whole section, and go back to any earlier version or
compare two side by side. Their changes reach you when they press "Send to Claude", and "I'm happy
with it" finishes. Say that it's optional: they can close it and keep the card as it is, or tell
you in the chat instead.

Wait for them, in the background as well, so the chat stays free:

```sh
python3 "${CLAUDE_SKILL_DIR}/scripts/edit.py" <work dir> --wait
```

It prints what they sent, as JSON. The persona they picked, anything they removed and any section
they hid are already in `cards.json`. Work through `requests`, following step 2's rules and
redacting as before:

- `replace`: swap that example for another prompt in the same section, more like the ones in `liked`.
- `anonymise`: rewrite it so it says less: drop any detail that could point to the person, a
  colleague or the company, keeping the idea a reader could copy.
- `add`: add one more example to the section, following `hint` where there is one.
- `replace_persona`: rewrite that persona in `personas` with step 2's persona method, in the
  direction of any persona in `liked`.
- `more_personas`: write `count` new personas the same way and append them to `personas`.
- `comment` and `comment_persona`: they left a note on it without voting. Do what the note asks.
  Praise ("love the sarcasm here") means keep it and write more like it.

Any request or `liked` entry can carry a `comment`, which is what they wrote about that item. Follow
it, and carry praise across to the rest of the card.

Act on `note` as well. Then run `edit.py <work dir> --publish`, which the open page loads as the
next version, and wait again. If it refuses, fix what it names and publish again.

If you cannot make the next version, run `edit.py <work dir> --fail "<why, in one sentence>"`. The
page shows the reason with their changes still in place, so they can try again, and you wait
again.

When it prints `closed`, edit mode stopped without "I'm happy with it". Do what its `next` says:
render again as in step 4 if any version came after the first, otherwise one line saying edit mode
has closed.

When what they sent has `done` set, they are happy with it. Render as in step 4, passing the run's
folder with `--out`, open the image as in step 5, and stop the editor, whose process ID is in
`<work dir>/editor.json`. Then close with the links and one line saying that if they want any more
changes, they can just ask and you'll make them.

If edit mode cannot open a browser, ask with the question tool instead whether they are happy with
it: "Happy with it" or "Change something", with the links to the image and the PDF just above the
question. Make what they ask for in `cards.json`, render again as in step 4, show it as in step 5,
and ask again.
