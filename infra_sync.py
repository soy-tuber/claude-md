#!/usr/bin/env python3
"""
infra_sync.py - systemd + cloudflared config + Caddyfile + ss からインフラ状態を収集し infra.db に書き込む
================================================================================
cron: 5:50 毎日 (morning_briefing 6:00 の直前)
"""

import re
import sqlite3
import subprocess
import yaml
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "infra.db"
CONFIG_YML = Path("/etc/cloudflared/config.yml")
CADDYFILE = Path("/home/soy/active/logger/Caddyfile")


def init_db(conn: sqlite3.Connection):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS services (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            port INTEGER,
            caddy_port INTEGER,
            tunnel_port INTEGER,
            app_name TEXT NOT NULL,
            hostname TEXT,
            directory TEXT,
            framework TEXT,
            systemd_unit TEXT,
            systemd_scope TEXT DEFAULT 'system',
            status TEXT DEFAULT 'unknown',
            is_listening INTEGER DEFAULT 0,
            notes TEXT,
            updated_at TEXT
        )
    """)
    # カラム追加（既存DBとの互換性）
    existing = {row[1] for row in conn.execute("PRAGMA table_info(services)").fetchall()}
    migrations = {
        "tunnel_port": "ALTER TABLE services ADD COLUMN tunnel_port INTEGER",
        "is_listening": "ALTER TABLE services ADD COLUMN is_listening INTEGER DEFAULT 0",
        "systemd_scope": "ALTER TABLE services ADD COLUMN systemd_scope TEXT DEFAULT 'system'",
    }
    for col, sql in migrations.items():
        if col not in existing:
            conn.execute(sql)
    conn.commit()


def get_systemd_services(scope: str = "system") -> list[dict]:
    """systemd サービスからアプリ情報を取得（system / user 両対応）"""
    cmd = ["systemctl", "list-units", "--type=service", "--state=running", "--no-pager", "--plain"]
    if scope == "user":
        cmd.insert(1, "--user")

    result = subprocess.run(cmd, capture_output=True, text=True)

    skip = {
        "console-getty", "containerd", "cron", "dbus", "docker", "getty@tty1",
        "nginx", "polkit", "rsyslog", "snapd", "ssh", "tailscaled",
        "unattended-upgrades", "user@1000", "wsl-pro",
        "at-spi-dbus-bus", "dbus", "pipewire", "pipewire-pulse", "wireplumber",
        "xdg-document-portal", "xdg-desktop-portal", "xdg-desktop-portal-gtk",
    }
    units = []
    for line in result.stdout.splitlines():
        parts = line.split()
        if not parts or not parts[0].endswith(".service"):
            continue
        unit = parts[0].removesuffix(".service")
        if unit in skip or unit.startswith("systemd"):
            continue
        units.append(unit)

    services = []
    for unit in units:
        show_cmd = ["systemctl", "show", f"{unit}.service",
                     "--property=Description,WorkingDirectory,ActiveState,ExecStart"]
        if scope == "user":
            show_cmd.insert(1, "--user")

        info = subprocess.run(show_cmd, capture_output=True, text=True)
        props = {}
        for line in info.stdout.splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                props[k] = v

        desc = props.get("Description", "")
        workdir = props.get("WorkingDirectory", "")
        exec_start = props.get("ExecStart", "")

        # ポート番号: Description → ExecStart の順で探す
        port = None
        m = re.search(r":(\d{4,5})", desc)
        if m:
            port = int(m.group(1))
        if port is None:
            m = re.search(r"(?:--port|--server\.port)\s+(\d{4,5})", exec_start)
            if m:
                port = int(m.group(1))
            else:
                m = re.search(r"(?:--bind|-b)\s+[\d.:]+:(\d{4,5})", exec_start)
                if m:
                    port = int(m.group(1))

        # framework を Description / ExecStart から推定
        framework = None
        haystack = f"{desc} {exec_start}".lower()
        for fw in ("Streamlit", "FastAPI", "Flask", "Gunicorn", "Caddy", "cloudflared"):
            if fw.lower() in haystack:
                framework = fw
                break
        if not framework and "uvicorn" in haystack:
            framework = "FastAPI"

        services.append({
            "systemd_unit": unit,
            "systemd_scope": scope,
            "app_name": unit,
            "description": desc,
            "port": port,
            "directory": workdir.replace(str(Path.home()), "~") if workdir else None,
            "framework": framework,
        })

    return services


def get_tunnel_routes() -> dict[int, str]:
    """config.yml から port → hostname マッピングを取得"""
    if not CONFIG_YML.exists():
        return {}

    with open(CONFIG_YML) as f:
        cfg = yaml.safe_load(f)

    routes = {}
    for rule in cfg.get("ingress", []):
        hostname = rule.get("hostname")
        service = rule.get("service", "")
        m = re.search(r"localhost:(\d+)", service)
        if hostname and m:
            routes[int(m.group(1))] = hostname
    return routes


def get_listening_ports() -> set[int]:
    """ss -tlnp から LISTEN 中のポートを取得"""
    result = subprocess.run(["ss", "-tlnp"], capture_output=True, text=True)
    ports = set()
    for line in result.stdout.splitlines():
        for m in re.finditer(r":(\d{4,5})\s", line):
            ports.add(int(m.group(1)))
    return ports


def get_caddy_map() -> dict[int, int]:
    """Caddyfile をパースして app_port → caddy_port マッピングを取得"""
    mapping = {}
    if not CADDYFILE.exists():
        return mapping

    content = CADDYFILE.read_text()
    # :9535 { ... reverse_proxy localhost:8535 ... }
    for m in re.finditer(
        r":(\d{4,5})\s*\{[^}]*reverse_proxy\s+localhost:(\d{4,5})",
        content, re.DOTALL,
    ):
        caddy_port = int(m.group(1))
        app_port = int(m.group(2))
        mapping[app_port] = caddy_port

    return mapping


def sync():
    conn = sqlite3.connect(str(DB_PATH))
    init_db(conn)

    now = datetime.now().isoformat()

    # 全削除して再構築（毎回最新スナップショット）
    conn.execute("DELETE FROM services")

    # system + user 両方のサービスを取得
    systemd_svcs = get_systemd_services("system") + get_systemd_services("user")
    tunnel_routes = get_tunnel_routes()
    listening = get_listening_ports()
    caddy_map = get_caddy_map()

    # systemd サービスを登録
    seen_ports = set()
    for svc in systemd_svcs:
        port = svc["port"]

        # ポートが無い systemd サービスは tunnel routes から逆引き
        if port is None:
            for p, h in tunnel_routes.items():
                if svc["app_name"].replace("-", "") in h.replace("-", "").replace(".", ""):
                    port = p
                    break

        # caddy 経由の場合
        caddy_port = caddy_map.get(port) if port else None

        # hostname: アプリポート直接 or caddy_port 経由で tunnel に到達
        hostname = tunnel_routes.get(port)
        if not hostname and caddy_port:
            hostname = tunnel_routes.get(caddy_port)

        # tunnel_port: Cloudflare Tunnel が実際に向いているポート
        tunnel_port = None
        if port and port in tunnel_routes:
            tunnel_port = port
        elif caddy_port and caddy_port in tunnel_routes:
            tunnel_port = caddy_port

        is_listening = 1 if (port and port in listening) else 0

        if port:
            status = "active" if is_listening else "stopped"
        else:
            status = "active"  # インフラ系(caddy, cloudflared)

        conn.execute(
            """INSERT INTO services
               (port, caddy_port, tunnel_port, app_name, hostname, directory,
                framework, systemd_unit, systemd_scope, status, is_listening, notes, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (port, caddy_port, tunnel_port, svc["app_name"], hostname, svc["directory"],
             svc["framework"], svc["systemd_unit"], svc["systemd_scope"],
             status, is_listening, svc["description"], now),
        )
        if port:
            seen_ports.add(port)

    # tunnel routes にあるが systemd に無い = 手動起動 or 停止中
    for tport, hostname in tunnel_routes.items():
        # caddy 経由ポートで実体が既に登録済みならスキップ
        if tport in caddy_map.values():
            continue
        # 直接ポートで既に登録済みならスキップ
        if tport in seen_ports:
            continue

        # tport が caddy_port の場合、実体の app_port を逆引き
        app_port = None
        for ap, cp in caddy_map.items():
            if cp == tport:
                app_port = ap
                break
        actual_port = app_port or tport

        if actual_port in seen_ports:
            continue

        is_listening = 1 if actual_port in listening else 0
        status = "active" if is_listening else "stopped"
        app_name = hostname.split(".")[0] if hostname else f"port-{actual_port}"

        conn.execute(
            """INSERT INTO services
               (port, caddy_port, tunnel_port, app_name, hostname, directory,
                framework, systemd_unit, systemd_scope, status, is_listening, notes, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (actual_port, caddy_map.get(actual_port), tport, app_name, hostname,
             None, None, None, None, status, is_listening, "config.yml記載・systemd未登録", now),
        )

    conn.commit()

    count = conn.execute("SELECT COUNT(*) FROM services").fetchone()[0]
    active = conn.execute("SELECT COUNT(*) FROM services WHERE status='active'").fetchone()[0]
    stopped = conn.execute("SELECT COUNT(*) FROM services WHERE status='stopped'").fetchone()[0]
    listening_count = conn.execute("SELECT COUNT(*) FROM services WHERE is_listening=1").fetchone()[0]
    conn.close()

    print(f"[infra_sync] {now}: {count} services ({active} active, {stopped} stopped, {listening_count} listening) → {DB_PATH}")


if __name__ == "__main__":
    sync()
