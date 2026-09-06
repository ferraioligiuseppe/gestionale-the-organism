# -*- coding: utf-8 -*-
"""
modules/dropbox_upload.py
Upload minimale verso una App Folder Dropbox usando il token salvato nei Secrets
([dropbox] ACCESS_TOKEN). Usato per le registrazioni audio di MAPS-Read.
"""
import base64
import json
import urllib.request
import urllib.error


def _token():
    import streamlit as st
    try:
        return st.secrets.get("dropbox", {}).get("ACCESS_TOKEN")
    except Exception:
        return None


def upload_audio_bytes(data: bytes, dropbox_path: str) -> str | None:
    """Carica i byte audio su Dropbox e ritorna un link diretto (dl.dropboxusercontent.com),
    o None se il token manca o qualcosa fallisce (silenzioso: non deve bloccare il salvataggio)."""
    token = _token()
    if not token or not data:
        return None
    try:
        req = urllib.request.Request(
            "https://content.dropboxapi.com/2/files/upload",
            data=data,
            headers={
                "Authorization": f"Bearer {token}",
                "Dropbox-API-Arg": json.dumps({
                    "path": dropbox_path,
                    "mode": "overwrite",
                    "autorename": False,
                    "mute": True,
                }),
                "Content-Type": "application/octet-stream",
            },
            method="POST",
        )
        urllib.request.urlopen(req, timeout=30).read()

        req2 = urllib.request.Request(
            "https://api.dropboxapi.com/2/sharing/create_shared_link_with_settings",
            data=json.dumps({"path": dropbox_path}).encode("utf-8"),
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            resp = urllib.request.urlopen(req2, timeout=30).read()
            url = json.loads(resp).get("url", "")
        except urllib.error.HTTPError as e:
            # Link già esistente: recuperalo invece di crearne uno nuovo
            body = e.read().decode("utf-8", "ignore")
            if "shared_link_already_exists" in body:
                req3 = urllib.request.Request(
                    "https://api.dropboxapi.com/2/sharing/list_shared_links",
                    data=json.dumps({"path": dropbox_path, "direct_only": True}).encode("utf-8"),
                    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                    method="POST",
                )
                resp = urllib.request.urlopen(req3, timeout=30).read()
                links = json.loads(resp).get("links", [])
                url = links[0]["url"] if links else ""
            else:
                raise
        if not url:
            return None
        # trasforma in link di streaming diretto
        return url.replace("www.dropbox.com", "dl.dropboxusercontent.com").split("?dl=")[0]
    except Exception:
        return None


def upload_audio_base64(b64_data: str, dropbox_path: str) -> str | None:
    try:
        if "," in b64_data:
            b64_data = b64_data.split(",", 1)[1]
        raw = base64.b64decode(b64_data)
        return upload_audio_bytes(raw, dropbox_path)
    except Exception:
        return None
