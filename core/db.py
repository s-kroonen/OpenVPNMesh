import sqlite3
import os
import datetime
from contextlib import contextmanager

DB_PATH = os.environ.get("MESH_DB", "/data/mesh.db")


def init_db():
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS nodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                public_ip TEXT NOT NULL,
                wg_pubkey TEXT,
                wg_ip TEXT,
                api_port INTEGER,
                wg_port INTEGER,
                vpn_port INTEGER,
                priority INTEGER,
                status TEXT,
                last_seen INTEGER,
                joined_at INTEGER
            );

            CREATE TABLE IF NOT EXISTS clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                wg_pubkey TEXT,
                wg_ip TEXT,
                ovpn_ip TEXT,
                created_at INTEGER,
                cert_pem TEXT,
                key_pem TEXT
            );

            CREATE TABLE IF NOT EXISTS mesh_config (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at INTEGER
            );

            CREATE TABLE IF NOT EXISTS routing_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mode TEXT,
                weights_json TEXT,
                updated_at INTEGER
            );

            CREATE TABLE IF NOT EXISTS health_log (
                node_id INTEGER,
                timestamp INTEGER,
                wg_ok BOOLEAN,
                api_ok BOOLEAN,
                ping_ok BOOLEAN,
                latency_ms INTEGER
            );
        """)

        conn.execute(
            "INSERT OR IGNORE INTO routing_rules (mode, weights_json, updated_at) VALUES ('weighted', '{}', 0)"
        )


@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_config(key: str) -> str | None:
    with get_db() as conn:
        row = conn.execute("SELECT value FROM mesh_config WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else None


def set_config(key: str, value: str):
    now = int(datetime.datetime.utcnow().timestamp())
    with get_db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO mesh_config (key, value, updated_at) VALUES (?, ?, ?)",
            (key, value, now),
        )


def get_all_nodes() -> list:
    with get_db() as conn:
        return conn.execute("SELECT * FROM nodes ORDER BY priority DESC").fetchall()


def get_node_by_name(name: str):
    with get_db() as conn:
        return conn.execute("SELECT * FROM nodes WHERE name = ?", (name,)).fetchone()


def get_node_by_id(node_id: int):
    with get_db() as conn:
        return conn.execute("SELECT * FROM nodes WHERE id = ?", (node_id,)).fetchone()


def insert_node(name, public_ip, wg_pubkey, wg_ip, api_port, wg_port, vpn_port, priority, status):
    now = int(datetime.datetime.utcnow().timestamp())
    with get_db() as conn:
        conn.execute(
            """INSERT INTO nodes
               (name, public_ip, wg_pubkey, wg_ip, api_port, wg_port, vpn_port, priority, status, joined_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (name, public_ip, wg_pubkey, wg_ip, api_port, wg_port, vpn_port, priority, status, now),
        )


def update_node_status(name: str, status: str):
    now = int(datetime.datetime.utcnow().timestamp())
    with get_db() as conn:
        conn.execute(
            "UPDATE nodes SET status = ?, last_seen = ? WHERE name = ?",
            (status, now, name),
        )


def get_next_mesh_ip(mesh_subnet: str) -> str:
    import ipaddress
    network = ipaddress.ip_network(mesh_subnet)
    hosts = list(network.hosts())
    with get_db() as conn:
        used = {r["wg_ip"] for r in conn.execute("SELECT wg_ip FROM nodes").fetchall()}
    for host in hosts:
        if str(host) not in used:
            return str(host)
    raise RuntimeError("No free IPs in mesh subnet")


def get_all_clients() -> list:
    with get_db() as conn:
        return conn.execute("SELECT * FROM clients ORDER BY created_at").fetchall()


def get_client_by_id(client_id: int):
    with get_db() as conn:
        return conn.execute("SELECT * FROM clients WHERE id = ?", (client_id,)).fetchone()


def get_routing() -> dict:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM routing_rules ORDER BY id DESC LIMIT 1").fetchone()
        if row:
            return dict(row)
        return {"mode": "weighted", "weights_json": "{}", "updated_at": 0}
