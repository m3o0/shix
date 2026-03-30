# shix

Find and run shell commands using natural language — powered by your own shell history.

shix searches your shell history to suggest relevant commands based on what you describe. No cloud, no API keys, just your local history.

## Install

```bash
pip install shix
```

## Usage

```bash
# Describe what you want to do
shix ask "docker compose restart"
shix ask "git push"
shix ask "activate virtual environment"

# Show more results
shix ask "git" --top 15
```

An interactive TUI opens where you can:

- **Arrow keys** to navigate between suggestions
- **Enter** or **click** to copy a command to clipboard
- **Mouse hover** to highlight a suggestion
- **Scroll** through many results
- **Esc** or **q** to quit

## Options

| Flag | Short | Description |
|------|-------|-------------|
| `--top N` | `-t` | Number of suggestions (default: 5) |
| `--history N` | `-n` | Limit history lines (0 = all, default: 0) |
| `--version` | `-v` | Show version |

## How it works

1. Reads your shell history (`~/.zsh_history`, `~/.bash_history`, or PowerShell history on Windows)
2. Matches your query against history using fuzzy search
3. Displays results in an interactive TUI for quick selection

## Supported shells

- **zsh** (macOS/Linux)
- **bash** (macOS/Linux)
- **PowerShell** (Windows)

## License

MIT
