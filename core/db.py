import sqlite3
import os
import datetime
from contextlib import contextmanager

# Database file path
DB_PATH = "/data/mesh.db"

def init_db():
    """Initialize the database and create tables if they don't exist."""
    try:
        with get_db() as conn:
            conn.execute("""
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
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS clients (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    wg_pubkey TEXT,
                    wg_ip TEXT,
                    ovpn_ip TEXT,
                    created_at INTEGER,
                    cert_pem TEXT,
                    key_pem TEXT
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS mesh_config (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at INTEGER
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS routing_rules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mode TEXT,
                    weights_json TEXT,
                    updated_at INTEGER
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS health_log (
                    node_id INTEGER,
                    timestamp INTEGER,
                    wg_ok BOOLEAN,
                    api_ok BOOLEAN,
                    ping_ok BOOLEAN,
                    latency_ms INTEGER,
                    FOREIGN KEY (node_id) REFERENCES nodes (id)
                )
            """)

            # Insert default routing mode if not exists
            conn.execute("""
                INSERT OR IGNORE INTO routing_rules (mode, weights_json, updated_at)
                VALUES ('weighted', '{}', 0)
            """)

            # Insert default mesh config if not exists
            conn.execute("""
                INSERT OR IGNORE INTO mesh_config (key, value, updated_at)
                VALUES ('join_token', '', 0)
            """)

            print("Database initialized successfully")

    except Exception as e:
        print(f"Error initializing database: {e}")
        raise SystemExit(1)

@contextmanager
def get_db():
    """Context manager for database connections."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def get_node_by_name(name):
    """Get a node by name from the database."""
    with get_db() as conn:
        cursor = conn.execute("SELECT * FROM nodes WHERE name = ?", (name,))
        return cursor.fetchone()

def get_join_token():
    """Get the current join token from mesh_config."""
    with get_db() as conn:
        cursor = conn.execute("SELECT value FROM mesh_config WHERE key = 'join_token'")
        result = cursor.fetchone()
        return result['value'] if result else None

def set_join_token(token):
    """Set the join token in mesh_config."""
    with get_db() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO mesh_config (key, value, updated_at)
            VALUES ('join_token', ?, ?)
        """, (token, int(datetime.datetime.utcnow().timestamp())))