# Agent Skills

A collection of agent skills for personal automation and productivity.

## Skills

| Skill | Description | Status |
|-------|-------------|--------|
| [last-words](./last-words) | Auto-deliver final messages to loved ones after 30 days of inactivity | ✅ Ready |
| [spot-the-difference](./spot-the-difference) | Create spot-the-difference image pairs with verified answers and batch exports | ✅ Ready (Codex) |

## Installation

Each skill can be installed independently. See its README or SKILL.md for details.

```bash
# Example: Install last-words skill
cd ~/.openclaw/skills
git clone https://github.com/dilboy/agent-skills.git
cp -r agent-skills/last-words .
```

## Structure

```
agent-skills/
├── last-words/          # Final message delivery
│   ├── SKILL.md         # OpenClaw skill definition
│   ├── README.md        # Skill documentation
│   ├── scripts/         # Python scripts
│   └── ...
└── spot-the-difference/ # Image pairs, answer masks, and exports
```

## Contributing

Feel free to submit issues or PRs for new skills or improvements.

## License

MIT - See individual skill LICENSE files for details.
