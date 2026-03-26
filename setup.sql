-- memory.db setup for Claude Code
-- Run: sqlite3 ~/.claude/memory.db < setup.sql

CREATE TABLE IF NOT EXISTS memories (
    id INTEGER PRIMARY KEY,
    project TEXT NOT NULL,
    category TEXT,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    keywords TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS services (
    id INTEGER PRIMARY KEY,
    port INTEGER NOT NULL UNIQUE,
    app_name TEXT NOT NULL,
    hostname TEXT,
    directory TEXT,
    framework TEXT,
    status TEXT DEFAULT 'active',
    notes TEXT,
    caddy_port INTEGER,
    tags TEXT
);

CREATE TABLE IF NOT EXISTS rules (
    id INTEGER PRIMARY KEY,
    scope TEXT NOT NULL,
    category TEXT NOT NULL,
    rule TEXT NOT NULL,
    severity TEXT DEFAULT 'error',
    keywords TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY,
    session_id TEXT NOT NULL UNIQUE,
    project_path TEXT,
    started_at TEXT,
    summary TEXT,
    key_actions TEXT,
    files_modified TEXT
);

-- FTS5 virtual table for cross-table full-text search
CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(
    source_table,
    source_id,
    text,
    tokenize='unicode61'
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_memories_project ON memories(project);
CREATE INDEX IF NOT EXISTS idx_memories_category ON memories(category);
CREATE INDEX IF NOT EXISTS idx_memories_keywords ON memories(keywords);
CREATE INDEX IF NOT EXISTS idx_services_port ON services(port);
CREATE INDEX IF NOT EXISTS idx_services_status ON services(status);
CREATE INDEX IF NOT EXISTS idx_services_tags ON services(tags);
CREATE INDEX IF NOT EXISTS idx_rules_scope ON rules(scope);
CREATE INDEX IF NOT EXISTS idx_rules_category ON rules(category);
CREATE INDEX IF NOT EXISTS idx_rules_keywords ON rules(keywords);
CREATE INDEX IF NOT EXISTS idx_sessions_project ON sessions(project_path);
