# My week in Claude

Spotify Wrapped for Claude. It turns your last week with Claude into one image you can share: a
card per kind of work, with real prompts anyone could copy. Claude takes out names and private
details, and you check every line before you share it. It works in Claude Code and chat.

![An example "My week in Claude" image](skills/my-week-in-claude/examples/my-week-in-claude.png)

## Install

**Claude Code**, in a terminal or the desktop app's Code tab. Ask Claude:

> Install the my-week-in-claude plugin from github.com/codebycarlos/my-week-in-claude and show me my week in Claude

Or run the commands yourself:

```sh
claude plugin marketplace add codebycarlos/my-week-in-claude
claude plugin install my-week-in-claude@my-week-in-claude
```

**Chat**, on claude.ai or in the desktop app:

1. Download [my-week-in-claude.zip](https://github.com/codebycarlos/my-week-in-claude/releases/latest/download/my-week-in-claude.zip).
2. Upload it under Customize, then Skills.
3. Turn on Code execution and "Search and reference chats", under Settings, then Capabilities.

On a Team or Enterprise plan, an owner can add it for everyone under Organization settings, then
Plugins & skills.

Cowork can't run it, since Cowork can't read Claude's session logs. Your Cowork work still counts
when you run it in Claude Code.

## Use

Ask Claude for "my week in Claude". It checks with you before it starts, and a run takes 5 to 15
minutes.

## Updates

In Claude Code, turn on auto-update under `/plugin`, then Marketplaces, or ask Claude to update
the my-week-in-claude plugin.

## What you get

- **A persona.** Claude writes three, based on how you worked, and you pick one.
- **New this week.** Skills, connectors and features you used for the first time.
- **A card per kind of work.** Its share of the week, the apps it touched, and your own prompts,
  most reusable first.
- **Models and thinking level.** Your share of each, in your sessions and in subagents.
- **Five ideas.** After the image, Claude suggests five ways to work better, based on your week:
  a skill for something you keep repeating, a connector you have but don't use, and so on.
- **A final check.** Claude shows every prompt on the image and asks whether you're happy with it.
  Take out a prompt you'd rather not share, swap one or rename a card, and it renders again.

## How it works

![The seven steps: welcome, measure, pick and redact the examples, pick a persona, render, five ideas, final check](images/how-it-works.png)

## Privacy

In Claude Code, your week is read from the session logs on your machine. In chat,
Claude reads your own past chats. Claude also searches the document apps it can reach, such as
Notion or Google Drive, for any AI policy that applies to you. Nothing is uploaded or posted anywhere. Before
rendering, Claude redacts every example: colleagues' names become roles, company and product names
become `[my company]` and `[our app]`, and pasted text, links and keys come out. Your name shows as
first name and initial. You review the image before it goes anywhere.


## Licence

MIT
