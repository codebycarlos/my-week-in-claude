---
name: my-week-in-claude
description: Makes "My week in Claude", a shareable image of a person's last week with Claude, with real prompts and five private ideas. Use for "my week in Claude", a weekly recap or usage wrapped.
---

# My week in Claude

Make one image a person can share with anyone, so readers pick up ideas from how they use Claude.
The reader can be anyone, and so can the author. Two
things matter above everything else:

- **Useful.** A reader should come away with something new to try, in the author's own words.
- **Safe.** Nothing on the image can embarrass the author, a colleague or the company.

The image shows shares of the week, never totals, so nobody compares how much anyone used. The
person also gets five ideas for working better, in the chat only. `examples/` holds a finished
image and the `stats.json` and `cards.json` it was made from.

Everything is read from the Claude Code session logs on this machine, Cowork's included. Nothing
is uploaded anywhere else.

## Welcome

This skill runs only in Claude Code, in a terminal or the desktop app's Code tab. Anywhere else,
such as Cowork or a chat on claude.ai, skip the welcome: say in one line that it runs in Claude
Code, where their Cowork work is counted too, tell them to ask for "my week in Claude" there, and
stop.

Before anything else, ask with the question tool whether to go ahead, with this welcome as the
question, copied exactly.

> Ready to see your week in Claude? It's like Spotify Wrapped for your last week with Claude. You get one
> image to share, with a card for each kind of work and your own prompts as examples anyone could
> copy, plus five ideas for working better that stay in this chat. I read your week from the
> session logs on this machine, take out names and private details, and follow any AI policy that
> applies to you. Nothing is posted anywhere. It takes up to 5 minutes, and uses about as many
> tokens as a longish conversation. (v1.0.8)

The options are "Start" and "Not now". Wait for "Start" before anything else, the checks below
included.

## Get everything set up

The scripts need Python 3.9 or newer and nothing else from Python. Rendering needs Google Chrome
or Chromium, which draws the image in the background, and an internet connection for the fonts and
app icons.

Check with `python3 --version`, and look for Chrome or Chromium. To the person, this step is
"Getting everything set up": never name Python, Chrome or any other tool in your updates or task
list unless one is missing. If something is missing, tell the person what it is and what it is for, and offer to install it
with the question tool. Install only
after they say yes, with the usual tool for their system (Homebrew on a Mac, `winget` on Windows,
the package manager on Linux). If they would rather not, stop and say what they need.

## Keep them posted

If you keep a task list, name its steps by this file's headings, such as "Get everything set up"
and "Check relevant AI policies", and never assume the person works for a company.

Before each step from here on, give the person one short, light line saying what you are doing,
so the wait feels like part of the fun. Write your own each time, in the spirit of these:

- Setting up: "Getting everything set up."
- Measuring: "Reading your week. This is the long bit."
- Writing the cards: "Sorting your prompts into piles. Some piles are taller than others."
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
- **Run the scripts from this skill's folder.** That is `${CLAUDE_SKILL_DIR}`.

## 1. Measure

```sh
python3 "${CLAUDE_SKILL_DIR}/scripts/collect.py" --session ${CLAUDE_SESSION_ID} --out <work dir>
```

`--session` makes it count only the sessions of the account this conversation runs in, when the
machine has more than one. `--days N` changes the window (default 7). `CLAUDE_CONFIG_DIR` is
honoured.

It writes three files:

| File | Holds |
|------|-------|
| `stats.json` | The window, conversation and message counts, the share of the week per model and per place the work went (`places`), `new_this_week`, `most_agents_at_once` and `used_ever` |
| `prompts.json` | Every prompt they typed in full, in order within each conversation, with its `id`, `place` (where the work after it went), `wrote` (every place it wrote to), `apps` (every app its work drew on), `session` and `tokens` (how much work followed it). Pasted text shows as `[pasted]` |
| `signals.json` | Habits for the five ideas: corrections, bare go-aheads, pasted text, repeated openings, interruptions, and `compacted`, the number of times a conversation of theirs grew so long Claude had to summarise it to carry on. Never goes on the image |

A prompt's `place` is where the work after it was written most often. Every app Claude wrote to
through a connector is a place of its own, named after the app (Slack, Gmail, HubSpot). The rest
are `code` (code committed, pushed or edited), `documents` (documents, sheets, images and other
files written), `pages` (pages and mock-ups published) and `answer`, where Claude looked things up
or ran checks and wrote nowhere but the chat. A bare go-ahead's work counts towards the prompt
before it. `--cowork <folder>` points at Cowork's sessions if they are somewhere unusual.

## 2. Write and redact the cards

Read all of `prompts.json`, in parts if it is too long for one read, and write `cards.json` in the shape of `examples/cards.json`: `name`, `cards` (each with `title`,
`places`, `moved` and `examples`), `persona` and `firsts`. This step takes the most judgement.

- **One card per place the work went**, largest first. Merge two places into one card when they
  are the same work to a reader. Drop one under 1% unless it has a striking example.
- **`places`** lists the places a card covers, spelt exactly as in `stats.json`. A card's share is
  the work after every prompt filed on it. `render.py` stops on a place it does not know.
- **`moved`** lists the `id` of each prompt whose output was meant for another card but never
  reached it, and its work moves with it. A Slack message drafted in the chat for the person to
  paste has the place `answer`, and belongs on the Slack card. Read the text to decide, and give a
  card for such prompts an empty `places`.
- **Title each card in everyday words**, starting with an -ing verb and saying what was made and
  where: "Drafting tickets in Linear", "Looking into things and answering questions".
- **Call writing "drafting".** For documents, tickets, messages and code, the title says
  "Drafting": "Drafting Notion pages", never "Writing pages in Notion". People rework, review and
  own what goes out, and the image must not suggest Claude did that work for them.
- **Put each example on the card that holds its prompt**, by its `place` or by `moved`.
- **Pick two to five examples per card** that show a reader something they had not thought to ask
  Claude. Skip routine prompts ("yes", "try again").
- **Order them by how reusable they are.** First the prompt a colleague could use in many
  situations, last the one tied to a single event.
- **Quote, then trim.** Keep the person's words. Cut with `…`, join a follow-up from the same
  `session` with `→` on the card of the first prompt, fix
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
  one. Leave it out rather than repeat a card's prompt or force a weak one.

**`persona`** is `{"name", "line"}`, in the style of Spotify Wrapped ("Shapeshifter: One moment
you're head over heels for an artist. The next, you've moved on. Some say it's erratic. We call it
eclectic.").

- The name is a character: "The" and one or two words.
- The line talks to them as "you" in one or two short sentences, built on something real from
  their week, and ends on a compliment or a dry second beat.
- Tease the habit, never the person, and never how much they used.
- Write three for step 3, each built on a different habit.

### Check relevant AI policies

Look for any AI policy that applies to the person before you pick examples, and apply it to everything on
the image. Search the document apps you
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

### Redact

Go through everything that goes on the image: every example, card titles, the persona, each
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
description. They can write their own.

## 4. Render

```sh
python3 "${CLAUDE_SKILL_DIR}/scripts/render.py" <work dir>/stats.json <work dir>/cards.json
```

It saves a new PNG in `~/Downloads/my-week-in-claude/`, named after the week and the time, so
earlier weeks are kept, and prints its path last. When you render again in step 6, pass that path
with `--out` so the run keeps one image.

It uses Google Chrome or Chromium, and an internet connection for the fonts and app logos. Open
the PNG and read it: every example has its app logos, no quote runs past three lines, and nothing the redaction
should have caught got through.

## 5. Hand over the image and five ideas

Put the image in front of the person before anything else:

- **Open it for them.** Run `open <png>` on a Mac, `start "" <png>` on Windows or
  `xdg-open <png>` on Linux, so it appears in their image viewer.
- **Give a link they can click**, on its own line: a markdown link whose text is the file name and
  whose target is the full path as a `file://` address, such as
  `[my-week-in-claude-2026-w47-19nov-232511.png](file:///Users/sam/Downloads/my-week-in-claude/my-week-in-claude-2026-w47-19nov-232511.png)`.

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
- **A feature or skill they have never used** that fits their cards, from `used_ever`.

Base every idea on what is in the files, and give fewer than five rather than pad.

## 6. Final check

List every example on the image, card by card. Then give the AI policies:

- **If you found any**, a table of the policies you checked the prompts against, one row each,
  with its title linked to the page. Under it, the table of prompts left out for a policy, if any.
- **If you found none**, a warning on its own line: no AI policy was found in the apps you could
  search, so the prompts were checked only for names and private details, and they should check
  any policy that applies to them before sharing.

Then ask with the question tool whether they are
happy with it: "Happy with it" or "Change something". Repeat the link to the image just above the
question, so they know what they are judging.

They may take out a prompt they would rather not share, swap or move one, rename a card or pick
another persona. Edit `cards.json`, run step 4 again, open and show the new image as in step 5, and ask again. The image
is done when they say they are happy.
