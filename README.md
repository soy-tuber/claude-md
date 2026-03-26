# CLAUDE.md — Production-Ready Claude Code Config

Real-world `CLAUDE.md` used daily with Claude Code on an RTX 5090 + WSL2 environment.  
Includes memory.db (FTS5) for persistent knowledge, 3-model LLM pipeline, and strict production rules.

本番環境で毎日使っているClaude Code設定ファイルです。

## Quick Start

### 1. Place CLAUDE.md / CLAUDE.mdを配置

```bash
# Global (applies to all projects / 全プロジェクト共通)
mkdir -p ~/.claude
cp CLAUDE.md ~/.claude/CLAUDE.md

# Or per-project (project-specific / プロジェクト単位)
cp CLAUDE.md /path/to/your/project/CLAUDE.md
```

### 2. Create memory.db / memory.dbを作成

```bash
sqlite3 ~/.claude/memory.db < setup.sql
```

### 3. Customize / カスタマイズ

Edit `CLAUDE.md` to match your environment:
自分の環境に合わせて `CLAUDE.md` を編集：

- OS, GPU, Python version / OS、GPU、Pythonバージョン
- Model names (Nemotron, Gemini, etc.) / モデル名
- Port assignment rules / ポート割り当てルール
- Your own pipeline strategy / 自分のパイプライン戦略

## Architecture / アーキテクチャ

```
~/.claude/
├── CLAUDE.md      ← Claude Code reads this on every session
└── memory.db      ← Persistent knowledge (FTS5 full-text search)
    ├── memories   ← Projects, workflows, tips
    ├── services   ← Running services & ports
    ├── rules      ← Discovered rules & constraints
    ├── sessions   ← Session history
    └── memory_fts ← Cross-table search (FTS5 virtual table)
```

## Key Ideas / 設計思想

**memory.db for persistent knowledge / 永続知識にmemory.db**
- Claude Code forgets everything between sessions. memory.db solves this.
- Claude Codeはセッション間で全て忘れる。memory.dbで解決。

**3-Model Pipeline / 3モデル分業**
- Local LLM (Nemotron) → Free API (Gemini) → Paid API (Claude)
- Heavy lifting on cheap/free models, architecture decisions on Claude.
- 力仕事は安い/無料モデルに、設計判断はClaudeに。

**"Do only what you're asked" / 「頼まれたことだけやれ」**
- The most important rule. Prevents Claude from over-engineering.
- 最も重要なルール。Claudeの過剰エンジニアリングを防ぐ。

## License

MIT
