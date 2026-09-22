"""
Capa de datos: guarda los sorteos históricos de Euromillones y Eurodreams.

- En local: SQLite normal en loteria.db (junto al script).
- En Streamlit Community Cloud: si están definidos TURSO_DATABASE_URL y
  TURSO_AUTH_TOKEN (en los "Secrets" de la app), usa Turso (libSQL) como
  réplica embebida, para que los datos persistan entre reinicios del
  contenedor. Mismo código de la app en ambos casos.
"""
import os
from pathlib import Path
import pandas as pd

LOCAL_DB_PATH = Path(__file__).parent / "loteria.db"
REPLICA_PATH = "/tmp/loteria_replica.db"  # solo se usa en modo Turso

GAME_CONFIG = {
    "euromillones": {
        "label": "Euromillones",
        "n_main": 5,
        "main_range": (1, 50),
        "n_extra": 2,
        "extra_range": (1, 12),
        "extra_label": "Estrella",
    },
    "eurodreams": {
        "label": "Eurodreams",
        "n_main": 6,
        "main_range": (1, 40),
        "n_extra": 1,
        "extra_range": (1, 5),
        "extra_label": "Sueño",
    },
}

_conn = None
_using_turso = False


def _turso_credentials():
    """Busca las credenciales de Turso en variables de entorno o en st.secrets."""
    url = os.environ.get("TURSO_DATABASE_URL")
    token = os.environ.get("TURSO_AUTH_TOKEN")
    if url and token:
        return url, token
    try:
        import streamlit as st
        url = st.secrets.get("TURSO_DATABASE_URL")
        token = st.secrets.get("TURSO_AUTH_TOKEN")
        if url and token:
            return url, token
    except Exception:
        pass
    return None, None


def get_conn():
    """Devuelve una conexión reutilizable (SQLite local o réplica Turso)."""
    global _conn, _using_turso
    if _conn is not None:
        return _conn

    url, token = _turso_credentials()
    if url and token:
        import libsql
        _conn = libsql.connect(REPLICA_PATH, sync_url=url, auth_token=token)
        _conn.sync()
        _using_turso = True
    else:
        import sqlite3
        _conn = sqlite3.connect(LOCAL_DB_PATH, check_same_thread=False)
        _using_turso = False

    _conn.execute(
        """
        CREATE TABLE IF NOT EXISTS sorteos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            juego TEXT NOT NULL,
            fecha TEXT NOT NULL,
            numeros TEXT NOT NULL,
            extras TEXT NOT NULL
        )
        """
    )
    _conn.commit()
    if _using_turso:
        _conn.sync()
    return _conn


def _sync_if_turso():
    if _using_turso:
        _conn.sync()


def insert_draw(juego: str, fecha: str, numeros: list[int], extras: list[int]) -> bool:
    """Inserta un sorteo. Devuelve False si ya existía (misma fecha+combinación)."""
    conn = get_conn()
    numeros_s = ",".join(str(n) for n in sorted(numeros))
    extras_s = ",".join(str(n) for n in sorted(extras))

    existe = conn.execute(
        "SELECT 1 FROM sorteos WHERE juego=? AND fecha=? AND numeros=? AND extras=?",
        (juego, fecha, numeros_s, extras_s),
    ).fetchone()
    if existe:
        return False

    conn.execute(
        "INSERT INTO sorteos (juego, fecha, numeros, extras) VALUES (?, ?, ?, ?)",
        (juego, fecha, numeros_s, extras_s),
    )
    conn.commit()
    _sync_if_turso()
    return True


def bulk_import(juego: str, df: pd.DataFrame) -> tuple[int, int]:
    """
    Importa un DataFrame con columnas: fecha, numeros (lista o string separada
    por comas/espacios), extras (idem). Devuelve (insertados, duplicados).
    """
    ok, dup = 0, 0
    for _, row in df.iterrows():
        numeros = _parse_number_list(row["numeros"])
        extras = _parse_number_list(row["extras"])
        fecha = str(row["fecha"])[:10]
        if insert_draw(juego, fecha, numeros, extras):
            ok += 1
        else:
            dup += 1
    return ok, dup


def _parse_number_list(value) -> list[int]:
    if isinstance(value, (list, tuple)):
        return [int(v) for v in value]
    s = str(value).replace(";", ",").replace(" ", ",")
    return [int(v) for v in s.split(",") if v.strip() != ""]


def load_draws(juego: str) -> pd.DataFrame:
    conn = get_conn()
    rows = conn.execute(
        "SELECT fecha, numeros, extras FROM sorteos WHERE juego = ? ORDER BY fecha ASC",
        (juego,),
    ).fetchall()
    df = pd.DataFrame(rows, columns=["fecha", "numeros", "extras"])
    if df.empty:
        return df
    df["numeros"] = df["numeros"].apply(lambda s: [int(x) for x in s.split(",")])
    df["extras"] = df["extras"].apply(lambda s: [int(x) for x in s.split(",")])
    df["fecha"] = pd.to_datetime(df["fecha"])
    return df


def delete_last(juego: str) -> bool:
    conn = get_conn()
    row = conn.execute(
        "SELECT id FROM sorteos WHERE juego = ? ORDER BY fecha DESC, id DESC LIMIT 1",
        (juego,),
    ).fetchone()
    if not row:
        return False
    conn.execute("DELETE FROM sorteos WHERE id = ?", (row[0],))
    conn.commit()
    _sync_if_turso()
    return True
