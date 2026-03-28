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

# Use a local AI model via Ollama (optional)
shix ask "find all large files" --local
```

An interactive TUI opens where you can:

- **Arrow keys** to navigate between suggestions
- **Enter** or **click** to copy a command to clipboard
- **Mouse hover** to highlight a suggestion
- **Scroll** through many results
- **Esc** or **q** to quit

## Modes

### Offline (default)

Fuzzy keyword search on your shell history. Instant results, no dependencies beyond Python.

```bash
shix ask "docker compose"
```

### Local AI (`--local`)

Sends your sanitized history to a local [Ollama](https://ollama.com) model for smarter, context-aware suggestions.

```bash
# First time setup
ollama pull qwen2.5:7b
ollama serve  # keep running in another terminal

# OR RUN THE OLLAMA APP

# Then use --local
shix ask "find files older than 7 days" --local
```

Requires the optional `httpx` dependency:

```bash
pip install shix[local]
# or just: pip install httpx
```

## Options

| Flag | Short | Description |
|------|-------|-------------|
| `--top N` | `-t` | Number of suggestions (default: 5) |
| `--local` | `-l` | Use local Ollama model |
| `--model NAME` | `-m` | Ollama model to use (default: qwen2.5:7b) |
| `--history N` | `-n` | Limit history lines (0 = all, default: 0) |
| `--version` | `-v` | Show version |

## How it works

1. Reads your shell history (`~/.zsh_history`, `~/.bash_history`, or PowerShell history on Windows)
2. Sanitizes secrets (API keys, passwords, tokens) before processing
3. Matches your query against history using fuzzy search (or sends to Ollama with `--local`)
4. Displays results in an interactive TUI for quick selection

## Supported shells

- **zsh** (macOS/Linux)
- **bash** (macOS/Linux)
- **PowerShell** (Windows)

## License

MIT
