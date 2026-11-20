# My week in Claude

Spotify Wrapped for Claude. Your week as one shareable card, with real prompts from each kind of work, anonymised and cleaned of anything private.

![An example "My week in Claude" card](skills/my-week-in-claude/examples/my-week-in-claude.png)

The same card as a PDF: [my-week-in-claude.pdf](skills/my-week-in-claude/examples/my-week-in-claude.pdf)

## Install and use

In Claude Code, in a terminal or the desktop app's Code tab:

1. Ask Claude: "Install the my-week-in-claude plugin from github.com/codebycarlos/my-week-in-claude"
2. Start a new session, which loads the plugin.
3. Ask: "Show me my week in Claude"

It checks with you before it starts, and a run takes about 5 minutes.

In a terminal you can skip the new session. Ask Claude: "Install the my-week-in-claude plugin from
github.com/codebycarlos/my-week-in-claude, then read its SKILL.md from where it was installed and
follow it". This doesn't work in the desktop app, which only loads a new plugin in a new session.

To install it yourself instead of asking Claude, run:

```sh
claude plugin marketplace add codebycarlos/my-week-in-claude
claude plugin install my-week-in-claude@my-week-in-claude
```

It doesn't run in Cowork or in a chat on claude.ai, since only Claude Code can read your session
logs. Your Cowork work still counts.

## Updates

In Claude Code, turn on auto-update under `/plugin`, then Marketplaces, or ask Claude to update
the my-week-in-claude plugin.

## What you get

- **A card, as an image and a PDF.** Both are saved in a new folder in `Downloads/my-week-in-claude`.
  The image shows up in a post or a message; in the PDF, readers can select and copy your prompts.
- **A persona.** Claude writes three, based on how you worked, and you pick one or go without.
- **New this week.** Skills, connectors and features you used for the first time.
- **A section per kind of work.** Its share of the week, the apps it touched, and your own prompts,
  most reusable first.
- **Models and thinking level.** Your share of each, in your sessions and in subagents.
- **Five ideas.** Claude also suggests five ways to work better, based on your week:
  a skill for something you keep repeating, a connector you have but don't use, and so on.
- **A final check, in edit mode.** Claude opens the card in your browser. Flick between personas, vote on
  them or ask for more, or turn the persona off. Give each prompt a thumbs up or down, leave Claude a
  note on it, ask for one to be anonymised further, remove or add prompts, or hide a whole section. Go back to any earlier
  version, or slide between two to see what changed. Claude makes the changes and draws the card
  again.

## How it works

![The seven steps: welcome, measure, pick and redact the examples, pick a persona, render, five ideas, final check](images/how-it-works.png)

## Privacy

Nothing is uploaded or posted anywhere.

- **What Claude reads:** the Claude Code session logs on your machine, Cowork's included. It also
  searches the document apps it can reach, such as Notion or Google Drive, for any AI policy that
  applies to you.
- **What Claude redacts:** colleagues' names become roles, company and product names become
  `[my company]` and `[our app]`, and pasted text, links and keys come out. Your name shows as first
  name and initial.
- **What you check:** you review the card before it goes anywhere.


## Licence

MIT
