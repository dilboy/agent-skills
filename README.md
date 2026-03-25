# Agent Skills

A collection of OpenClaw skills for personal automation and productivity.

## Skills

| Skill | Description | Status |
|-------|-------------|--------|
| [last-words](./last-words) | Auto-deliver final messages to loved ones after 30 days of inactivity | ✅ Ready |

## Installation

Each skill can be installed independently. See individual skill README for details.

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
└── [future-skills]/     # More skills coming...
```

## Contributing

Feel free to submit issues or PRs for new skills or improvements.

## License

MIT - See individual skill LICENSE files for details.
