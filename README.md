# CLAUDE.md + GEMINI.md — Shared Config for AI Coding Agents

Real-world config used daily with **Claude Code** and **Gemini CLI** on an RTX 5090 + WSL2 environment.
Both agents share the same `memory.db` (FTS5) for persistent knowledge.

Claude CodeとGemini CLIの両方で毎日使っている設定ファイルです。
両エージェントが同じ `memory.db` を共有しています。

## Architecture / アーキテクチャ

```
~/.claude/
├── CLAUDE.md        ← Claude Code reads this on every session
└── memory.db        ← Shared persistent knowledge (FTS5)
    ├── memories     ← Projects, workflows, tips
    ├── services     ← Running services & ports
    ├── rules        ← Discovered rules & constraints
    ├── sessions     ← Session history
    └── memory_fts   ← Cross-table full-text search

~/.gemini/
└── GEMINI.md        ← Gemini CLI reads this on every session
                        (same content as CLAUDE.md, same memory.db)
```

Both files point to the same `~/.claude/memory.db`. One brain, two agents.
両ファイルは同じ `~/.claude/memory.db` を参照。1つの脳、2つのエージェント。

## Quick Start

### 1. Place config files / 設定ファイルを配置

```bash
# Claude Code
mkdir -p ~/.claude
cp CLAUDE.md ~/.claude/CLAUDE.md

# Gemini CLI (same file)
mkdir -p ~/.gemini
cp CLAUDE.md ~/.gemini/GEMINI.md
```

### 2. Create memory.db / memory.dbを作成

```bash
sqlite3 ~/.claude/memory.db < setup.sql
```

### 3. Customize / カスタマイズ

Edit both files to match your environment:
自分の環境に合わせて編集：

- OS, GPU, Python version / OS、GPU、Pythonバージョン
- Model names / モデル名
- Port assignment rules / ポート割り当てルール
- Your own pipeline strategy / 自分のパイプライン戦略

## Key Ideas / 設計思想

**Shared memory.db / memory.db共有**
- Both Claude Code and Gemini CLI forget everything between sessions. memory.db solves this.
- Claude CodeもGemini CLIもセッション間で全て忘れる。memory.dbで解決。

**3-Model Pipeline / 3モデル分業**
- Local LLM (Nemotron 9B) → Free API (Gemini CLI) → Paid API (Claude Code)
- Heavy lifting on cheap/free models, architecture decisions on Claude.
- 力仕事は安い/無料モデルに、設計判断はClaudeに。

**"Do only what you're asked" / 「頼まれたことだけやれ」**
- The most important rule. Prevents AI agents from over-engineering.
- 最も重要なルール。AIエージェントの過剰エンジニアリングを防ぐ。

## License

MIT
