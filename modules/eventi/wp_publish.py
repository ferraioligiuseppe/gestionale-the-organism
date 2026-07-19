# -*- coding: utf-8 -*-
"""Pubblicazione eventi su pnev.it via REST API WordPress (Application Password)."""
import requests
import streamlit as st

WP_BASE = "https://www.pnev.it/wp-json/wp/v2"


def _auth():
    wp = st.secrets.get("wordpress", {})
    user = wp.get("WP_USER")
    pwd = wp.get("WP_APP_PASSWORD")
    if not user or not pwd:
        return None
    return (user, pwd)


def _ensure_columns(conn):
    try:
        conn.rollback()
    except Exception:
        pass
    cur = conn.cursor()
    try:
        cur.execute("ALTER TABLE ev_eventi ADD COLUMN IF NOT EXISTS wp_post_id BIGINT")
        cur.execute("ALTER TABLE ev_eventi ADD COLUMN IF NOT EXISTS wp_url TEXT")
        conn.commit()
    except Exception:
        conn.rollback()


def pubblica_evento(conn, evento: dict, link_pubblico: str) -> tuple[bool, str]:
    """Crea o aggiorna il post WordPress corrispondente all'evento."""
    auth = _auth()
    if not auth:
        return False, "Credenziali WordPress non configurate (secrets [wordpress])."

    _ensure_columns(conn)

    titolo = evento.get("titolo", "Evento PNEV")
    corpo = (evento.get("descrizione") or "") + (
        f'<p><a href="{link_pubblico}" target="_blank">Iscriviti qui</a></p>'
    )
    payload = {"title": titolo, "content": corpo, "status": "publish"}

    wp_post_id = evento.get("wp_post_id")
    try:
        if wp_post_id:
            resp = requests.post(f"{WP_BASE}/posts/{wp_post_id}", data=payload, auth=auth, timeout=15)
        else:
            resp = requests.post(f"{WP_BASE}/posts", data=payload, auth=auth, timeout=15)
        if resp.status_code not in (200, 201):
            return False, f"Errore WordPress ({resp.status_code}): {resp.text[:200]}"
        data = resp.json()
        cur = conn.cursor()
        cur.execute("UPDATE ev_eventi SET wp_post_id=%s, wp_url=%s WHERE id=%s",
                    (data.get("id"), data.get("link"), evento.get("id")))
        conn.commit()
        return True, data.get("link", "")
    except Exception as e:
        return False, f"Errore di connessione: {e}"


def rimuovi_evento(conn, evento: dict) -> tuple[bool, str]:
    """Sposta nel cestino (o elimina) il post WordPress collegato all'evento."""
    auth = _auth()
    if not auth:
        return False, "Credenziali WordPress non configurate (secrets [wordpress])."
    wp_post_id = evento.get("wp_post_id")
    if not wp_post_id:
        return True, "Nessun articolo pubblicato su pnev.it da rimuovere."
    try:
        resp = requests.delete(f"{WP_BASE}/posts/{wp_post_id}", auth=auth, timeout=15)
        if resp.status_code not in (200, 410):
            return False, f"Errore WordPress ({resp.status_code}): {resp.text[:200]}"
        cur = conn.cursor()
        cur.execute("UPDATE ev_eventi SET wp_post_id=NULL, wp_url=NULL WHERE id=%s", (evento.get("id"),))
        conn.commit()
        return True, "Rimosso da pnev.it."
    except Exception as e:
        return False, f"Errore di connessione: {e}"
