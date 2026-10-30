# -*- coding: utf-8 -*-
"""
Modulo Esercizi Wordwall
=========================
"""

import re
from urllib.parse import unquote

import streamlit as st
import streamlit.components.v1 as components


def init_wordwall_table(conn) -> None:
    cur = conn.cursor()
    try:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS wordwall_esercizi (
                id              SERIAL PRIMARY KEY,
                paziente_id     INTEGER NOT NULL,
                titolo          TEXT NOT NULL,
                area            TEXT,
                wordwall_url    TEXT NOT NULL,
                note            TEXT,
                attivo          BOOLEAN DEFAULT TRUE,
                data_creazione  TIMESTAMPTZ DEFAULT now()
            )
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_wordwall_paziente
            ON wordwall_esercizi (paziente_id)
            """
        )
        conn.commit()
    except Exception:
        try: conn.rollback()
        except Exception: pass
        raise
    finally:
        cur.close()


def _ensure_schema(conn) -> None:
    if not st.session_state.get("_wordwall_schema_ok"):
        init_wordwall_table(conn)
        st.session_state["_wordwall_schema_ok"] = True


AREE_WORDWALL = [
    "Attenzione", "Funzioni esecutive", "Lettura", "Scrittura", "Linguaggio",
    "Matematica", "Memoria", "Prerequisiti", "Visuo-percettivo", "Altro",
]


def _to_embed_url(url_or_iframe: str) -> str:
    if not url_or_iframe:
        return ""
    raw = url_or_iframe.strip()
    m = re.search(r'src\s*=\s*["\']([^"\']+)["\']', raw, flags=re.IGNORECASE)
    if m:
        raw = m.group(1).strip()
    # Wordwall si lascia aprire dentro un altro sito SOLO con il link «Incorpora» (…/embed/<codice lungo>):
    # il link normale (…/resource/<numero>/…) viene rifiutato, quindi in quel caso non lo incorporo.
    if not re.search(r"/embed/[0-9a-f]{16,}", raw, re.I):
        return ""
    if raw.startswith("http://"):
        raw = "https://" + raw[len("http://"):]
    if raw.startswith("//"):
        raw = "https:" + raw
    return raw


def _insert_esercizio(conn, paziente_id: int, titolo: str, area: str,
                       url: str, note: str) -> None:
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO wordwall_esercizi
                (paziente_id, titolo, area, wordwall_url, note)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (paziente_id, titolo.strip(), (area or "").strip() or None,
             url.strip(), (note or "").strip() or None),
        )
        conn.commit()
    except Exception:
        try: conn.rollback()
        except Exception: pass
        raise
    finally:
        cur.close()


def _list_esercizi(conn, paziente_id: int) -> list:
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT id, titolo, area, wordwall_url, note, attivo, data_creazione
              FROM wordwall_esercizi
             WHERE paziente_id = %s
          ORDER BY attivo DESC, data_creazione DESC
            """,
            (paziente_id,),
        )
        return cur.fetchall()
    except Exception:
        try: conn.rollback()
        except Exception: pass
        raise
    finally:
        cur.close()


def _toggle_attivo(conn, esercizio_id: int, nuovo_stato: bool) -> None:
    cur = conn.cursor()
    try:
        cur.execute(
            "UPDATE wordwall_esercizi SET attivo = %s WHERE id = %s",
            (nuovo_stato, esercizio_id),
        )
        conn.commit()
    except Exception:
        try: conn.rollback()
        except Exception: pass
        raise
    finally:
        cur.close()


def _delete_esercizio(conn, esercizio_id: int) -> None:
    cur = conn.cursor()
    try:
        cur.execute(
            "DELETE FROM wordwall_esercizi WHERE id = %s",
            (esercizio_id,),
        )
        conn.commit()
    except Exception:
        try: conn.rollback()
        except Exception: pass
        raise
    finally:
        cur.close()


def _form_nuovo_esercizio(conn, paziente_id: int) -> None:
    with st.expander("➕ Aggiungi un esercizio Wordwall", expanded=False):
        with st.form(key=f"ww_form_new_{paziente_id}", clear_on_submit=True):
            col1, col2 = st.columns([2, 1])
            with col1:
                titolo = st.text_input(
                    "Titolo *",
                    placeholder="es. Abbinamento sinonimi",
                )
            with col2:
                area = st.selectbox("Area", AREE_WORDWALL, index=0)

            url = st.text_input(
                "URL Wordwall *",
                placeholder="https://wordwall.net/it/resource/...  oppure incolla il codice <iframe ...>",
                help=(
                    "Su Wordwall, dalla tua attività, clicca «Condividi» o "
                    "«Incorpora» e incolla qui il link o il codice iframe completo. "
                    "Il modulo lo normalizza in automatico."
                ),
            )

            note = st.text_area(
                "Note (facoltative)",
                placeholder="Indicazioni per il paziente, frequenza consigliata…",
                height=80,
            )

            submitted = st.form_submit_button("💾 Salva esercizio")

        if submitted:
            if not titolo.strip():
                st.error("Il titolo è obbligatorio.")
                return
            if not url.strip():
                st.error("L'URL Wordwall è obbligatorio.")
                return
            if "wordwall.net" not in url.lower():
                st.warning(
                    "L'URL non sembra di Wordwall. Salvo lo stesso, ma "
                    "verifica che sia corretto."
                )
            try:
                _insert_esercizio(conn, paziente_id, titolo, area, url, note)
                st.success("Esercizio salvato ✅")
                st.rerun()
            except Exception as e:
                st.error(f"Errore nel salvataggio: {e}")


PLAYER_HEIGHT_DEFAULT = 600  # px


def _lista_esercizi(conn, paziente_id: int) -> None:
    esercizi = _list_esercizi(conn, paziente_id)

    if not esercizi:
        st.info("Nessun esercizio assegnato a questo paziente.")
        return

    active_player_key = f"ww_active_player_{paziente_id}"
    active_player = st.session_state.get(active_player_key)

    st.markdown(f"**Esercizi assegnati:** {len(esercizi)}")
    st.markdown("---")

    for e in esercizi:
        es_id   = e["id"]
        titolo  = e["titolo"]
        area    = e["area"] or "—"
        url     = e["wordwall_url"]
        note    = e["note"] or ""
        attivo  = bool(e["attivo"])
        data_c  = e["data_creazione"]

        is_playing = (active_player == es_id)
        header_icon = "▶️" if is_playing else ("🟢" if attivo else "⚪")

        with st.expander(
            f"{header_icon} **{titolo}** · {area}",
            expanded=is_playing,
        ):
            colA, colB = st.columns([3, 2])
            with colA:
                st.markdown(f"🔗 [Apri su Wordwall (nuova scheda)]({url})")
                if note:
                    st.caption(note)
                try:
                    st.caption(f"Creato il {data_c.strftime('%d/%m/%Y %H:%M')}")
                except Exception:
                    st.caption(f"Creato il {data_c}")

            with colB:
                if is_playing:
                    if st.button("⏹️ Chiudi player", key=f"ww_stop_{es_id}"):
                        st.session_state[active_player_key] = None
                        st.rerun()
                else:
                    if st.button("▶️ Apri player", key=f"ww_play_{es_id}"):
                        st.session_state[active_player_key] = es_id
                        st.rerun()

                if attivo:
                    if st.button("⏸️ Disattiva", key=f"ww_off_{es_id}"):
                        _toggle_attivo(conn, es_id, False)
                        st.rerun()
                else:
                    if st.button("▶️ Riattiva", key=f"ww_on_{es_id}"):
                        _toggle_attivo(conn, es_id, True)
                        st.rerun()

                conferma_key = f"ww_del_conf_{es_id}"
                if st.session_state.get(conferma_key):
                    st.warning("Confermi l'eliminazione?")
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("Sì, elimina", key=f"ww_del_yes_{es_id}"):
                            if active_player == es_id:
                                st.session_state[active_player_key] = None
                            _delete_esercizio(conn, es_id)
                            st.session_state.pop(conferma_key, None)
                            st.rerun()
                    with c2:
                        if st.button("Annulla", key=f"ww_del_no_{es_id}"):
                            st.session_state.pop(conferma_key, None)
                            st.rerun()
                else:
                    if st.button("🗑️ Elimina", key=f"ww_del_{es_id}"):
                        st.session_state[conferma_key] = True
                        st.rerun()

            if is_playing:
                embed_url = _to_embed_url(url)
                if not embed_url:
                    st.info("Per giocare qui dentro serve il codice **«Incorpora»** di Wordwall: aprilo nella scheda "
                            "**📚 Libreria** e incollalo lì (vale per tutti i pazienti). Intanto usa «Apri su Wordwall».")
                else:
                    st.markdown("")
                    components.iframe(
                        embed_url,
                        height=PLAYER_HEIGHT_DEFAULT,
                        scrolling=True,
                    )
                    st.caption(
                        "Se l'attività non parte qui dentro, usa il link "
                        "«Apri su Wordwall (nuova scheda)»: alcune attività "
                        "hanno restrizioni anti-embed."
                    )


LIBRERIA_ID = 0   # esercizi salvati in libreria, non ancora assegnati a nessun paziente


def _cambia_url(conn, vecchio: str, nuovo: str) -> None:
    """Sostituisce il link di un esercizio (in libreria e per tutti i pazienti che lo hanno)."""
    cur = conn.cursor()
    try:
        cur.execute("UPDATE wordwall_esercizi SET wordwall_url = %s WHERE wordwall_url = %s", (nuovo, vecchio))
        conn.commit()
    except Exception:
        try: conn.rollback()
        except Exception: pass
    finally:
        try: cur.close()
        except Exception: pass


def _elenco_libreria(conn) -> list:
    """Tutti gli esercizi conosciuti (uno per link), con quanti pazienti li hanno assegnati."""
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT wordwall_url, MIN(titolo) AS titolo, MIN(area) AS area, MIN(note) AS note,
                   COUNT(DISTINCT CASE WHEN paziente_id <> 0 THEN paziente_id END) AS pazienti
            FROM wordwall_esercizi GROUP BY wordwall_url ORDER BY MIN(area), MIN(titolo)
            """
        )
        nomi = [d[0] for d in cur.description]
        return [dict(zip(nomi, list(r))) for r in cur.fetchall()]
    except Exception:
        try: conn.rollback()
        except Exception: pass
        return []
    finally:
        try: cur.close()
        except Exception: pass


_RE_WW = re.compile(r"https?://(?:www\.)?wordwall\.net/(?:[a-z]{2}(?:-[a-z]{2})?/)?(?:resource|embed)/(\d+)(?![0-9a-f])(?:/([\w\-%]+))?", re.I)


def estrai_link_wordwall(testo: str) -> list:
    """Trova tutti i link di attività Wordwall in un testo (anche copiato da una pagina o da un iframe).
    Ritorna [(url_resource, titolo_dal_link)], senza doppioni."""
    visti, out = set(), []
    # codici «Incorpora» (…/embed/<codice lungo>?…): sono quelli che si giocano dentro il gestionale
    for m in re.finditer(r"https?://(?:www\.)?wordwall\.net/(?:[a-z]{2}(?:-[a-z]{2})?/)?embed/([0-9a-f]{16,})[^\s\"'<>]*", testo or "", re.I):
        if m.group(1) in visti:
            continue
        visti.add(m.group(1))
        out.append((m.group(0).replace("&amp;", "&"), f"Attività Wordwall {m.group(1)[:6]}"))
    for m in _RE_WW.finditer(testo or ""):
        rid, slug = m.group(1), m.group(2) or ""
        if rid in visti:
            continue
        visti.add(rid)
        titolo = unquote(slug).replace("-", " ").strip().capitalize() or f"Attività Wordwall {rid}"
        out.append((f"https://wordwall.net/it/resource/{rid}" + (f"/{slug}" if slug else ""), titolo))
    return out


def _leggi_profilo(url: str) -> tuple:
    """Prova a leggere le attività pubbliche dalla pagina profilo Wordwall. Ritorna (lista, errore)."""
    import urllib.request
    if "wordwall.net" not in url:
        return [], "non è un indirizzo di wordwall.net"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (gestionale The Organism)"})
        with urllib.request.urlopen(req, timeout=20) as r:
            html = r.read().decode("utf-8", errors="replace")
    except Exception as e:
        return [], f"Wordwall non ha risposto ({e}). Usa il metodo «incolla i link»."
    trovati = estrai_link_wordwall(html.replace('href="/', 'href="https://wordwall.net/'))
    return trovati, (None if trovati else "nessuna attività pubblica trovata in quella pagina")


def _id_ww(url: str) -> str:
    m = re.search(r"/(?:embed|resource)/([0-9a-f]{16,}|\d+)", url or "", re.I)
    return m.group(1).lower() if m else (url or "")


def _importa(conn, coppie, area) -> int:
    noti_id = {_id_ww(e["wordwall_url"]) for e in _elenco_libreria(conn)}
    n = 0
    for url, titolo in coppie:
        rid = _id_ww(url)
        if rid in noti_id:
            continue
        _insert_esercizio(conn, LIBRERIA_ID, titolo, area, url, "importato")
        noti_id.add(rid); n += 1
    return n


def _sezione_importa(conn) -> None:
    with st.expander("📥 Importa in blocco da Wordwall", expanded=False):
        st.caption("Wordwall non permette ai programmi di entrare nel tuo account: i link li porti tu, in uno di questi due modi. "
                   "Gli esercizi già presenti non vengono duplicati; il titolo si ricava dal link e puoi correggerlo dopo.")
        area = st.selectbox("Area da assegnare agli esercizi importati", AREE_WORDWALL, key="ww_imp_area")
        t1, t2 = st.tabs(["📋 Incolla i link", "👤 Dal profilo pubblico"])
        with t1:
            st.markdown("Su Wordwall apri **Le mie attività**, apri ogni attività e copia **il codice «Incorpora»** "
                        "(Condividi → Incorpora: così si gioca anche dentro il gestionale) oppure l'indirizzo dalla barra del browser "
                        "(si gioca solo su Wordwall). Incollali qui **uno sotto l'altro**: va bene anche un testo misto.")
            testo = st.text_area("Link o testo con i link", height=160, key="ww_imp_testo",
                                 placeholder="https://wordwall.net/it/resource/12345678/abbinamento-sinonimi\nhttps://wordwall.net/it/resource/…")
            trovati = estrai_link_wordwall(testo)
            if testo.strip():
                st.caption(f"Riconosciuti {len(trovati)} esercizi" + (": " + ", ".join(t for _, t in trovati[:6]) + ("…" if len(trovati) > 6 else "") if trovati else ""))
            if st.button(f"📥 Importa {len(trovati)} esercizi", disabled=not trovati, key="ww_imp_ok"):
                n = _importa(conn, trovati, area)
                st.success(f"Importati {n} esercizi nuovi ({len(trovati) - n} erano già in libreria)."); st.rerun()
        with t2:
            st.markdown("Funziona solo se le tue attività sono **pubbliche**. Su Wordwall apri il tuo nome in alto → **Profilo** "
                        "e copia l'indirizzo della pagina (es. `https://wordwall.net/it/teacher/1234567/nome`).")
            url = st.text_input("Indirizzo del profilo Wordwall", key="ww_imp_prof")
            if st.button("🔍 Cerca le attività", disabled=not url.strip(), key="ww_imp_cerca"):
                lista, err = _leggi_profilo(url.strip())
                st.session_state["ww_prof_trovati"] = lista
                if err:
                    st.warning(err)
            lista = st.session_state.get("ww_prof_trovati") or []
            if lista:
                st.caption(f"Trovate {len(lista)} attività: " + ", ".join(t for _, t in lista[:8]) + ("…" if len(lista) > 8 else ""))
                if st.button(f"📥 Importa {len(lista)} attività", key="ww_imp_prof_ok"):
                    n = _importa(conn, lista, area)
                    st.session_state.pop("ww_prof_trovati", None)
                    st.success(f"Importate {n} attività nuove."); st.rerun()


def render_libreria(conn, paziente_id=None) -> None:
    """Libreria di tutti gli esercizi Wordwall: si giocano anche senza paziente."""
    _ensure_schema(conn)
    st.caption("Tutti gli esercizi Wordwall dello Studio, da giocare subito anche senza scegliere un paziente."
               + (" Con il paziente scelto puoi anche **assegnarli** a lui." if paziente_id else ""))
    with st.expander("➕ Aggiungi un esercizio alla libreria", expanded=False):
        with st.form(key="ww_form_lib", clear_on_submit=True):
            c1, c2 = st.columns([2, 1])
            titolo = c1.text_input("Titolo *", placeholder="es. Abbinamento sinonimi")
            area = c2.selectbox("Area", AREE_WORDWALL, index=0)
            url = st.text_input("URL Wordwall *", placeholder="https://wordwall.net/it/resource/...  oppure il codice <iframe ...>")
            note = st.text_input("Note (facoltative)")
            if st.form_submit_button("Salva nella libreria", type="primary"):
                if not titolo.strip() or not url.strip():
                    st.error("Servono titolo e URL.")
                else:
                    _insert_esercizio(conn, LIBRERIA_ID, titolo.strip(), area, url.strip(), note.strip())
                    st.success("Esercizio aggiunto alla libreria."); st.rerun()
    _sezione_importa(conn)
    elenco = _elenco_libreria(conn)
    if not elenco:
        st.info("La libreria è vuota: aggiungi un esercizio o importali in blocco qui sopra."); return
    c1, c2 = st.columns([2, 1])
    cerca = c1.text_input("Cerca", placeholder="titolo o parola…", key="ww_lib_cerca").strip().lower()
    aree = sorted({e.get("area") or "—" for e in elenco})
    area_f = c2.selectbox("Area", ["Tutte"] + aree, key="ww_lib_area")
    vis = [e for e in elenco if (not cerca or cerca in (e.get("titolo") or "").lower() or cerca in (e.get("note") or "").lower())
           and (area_f == "Tutte" or (e.get("area") or "—") == area_f)]
    st.markdown(f"**{len(vis)} esercizi**")
    gia = {e["wordwall_url"] for e in _list_esercizi(conn, paziente_id)} if paziente_id else set()
    attivo = st.session_state.get("ww_lib_play")
    for i, e in enumerate(vis):
        url = e["wordwall_url"]
        with st.expander(f"{'▶️' if attivo == url else '🎮'} **{e.get('titolo')}** · {e.get('area') or '—'}"
                         + (f" · assegnato a {e['pazienti']} paziente" + ("" if e["pazienti"] == 1 else "i") if e.get("pazienti") else ""), expanded=attivo == url):
            a1, a2, a3 = st.columns(3)
            a1.markdown(f"🔗 [Apri su Wordwall]({url})")
            if attivo == url:
                if a2.button("⏹️ Chiudi player", key=f"ww_lib_stop_{i}"):
                    st.session_state["ww_lib_play"] = None; st.rerun()
            elif a2.button("▶️ Gioca qui", key=f"ww_lib_play_{i}"):
                st.session_state["ww_lib_play"] = url; st.rerun()
            if paziente_id:
                if url in gia:
                    a3.caption("✓ già assegnato a questo paziente")
                elif a3.button("➕ Assegna al paziente", key=f"ww_lib_ass_{i}"):
                    _insert_esercizio(conn, paziente_id, e.get("titolo") or "", e.get("area"), url, e.get("note") or "")
                    st.success("Assegnato."); st.rerun()
            if e.get("note"):
                st.caption(e["note"])
            if attivo == url:
                emb = _to_embed_url(url)
                if emb:
                    components.iframe(emb, height=PLAYER_HEIGHT_DEFAULT, scrolling=True)
                else:
                    st.info("Per giocare **qui dentro** serve il codice **«Incorpora»** di Wordwall (il link normale "
                            "Wordwall non lo lascia aprire dentro altri siti). Intanto puoi giocare con **«Apri su Wordwall»**.\n\n"
                            "Su Wordwall apri l'attività → **Condividi** → **Incorpora** → copia il codice e incollalo qui sotto.")
                    cod = st.text_area("Codice «Incorpora»", key=f"ww_lib_emb_{i}", height=80,
                                       placeholder='<iframe style="max-width:100%" src="https://wordwall.net/it/embed/…" …></iframe>')
                    nuovo = _to_embed_url(cod)
                    if cod.strip() and not nuovo:
                        st.warning("Non trovo un link «embed» valido in questo codice: copia proprio il codice della finestra «Incorpora».")
                    if nuovo and st.button("💾 Salva il codice e gioca", key=f"ww_lib_emb_ok_{i}"):
                        _cambia_url(conn, url, nuovo)
                        st.session_state["ww_lib_play"] = nuovo; st.rerun()


def render_wordwall(conn, paziente_id) -> None:
    """Pagina Esercizi Wordwall: libreria per tutti, esercizi assegnati se c'è un paziente."""
    _ensure_schema(conn)
    st.subheader("🎮 Esercizi Wordwall")
    if not paziente_id:
        st.info("**Modalità libera**: puoi giocare con tutti gli esercizi della libreria. "
                "Per assegnarli a un paziente, sceglilo prima in «Pazienti».")
        render_libreria(conn, None); return
    t1, t2 = st.tabs(["🧒 Esercizi del paziente", "📚 Libreria"])
    with t1:
        st.caption("Esercizi assegnati a questo paziente. Apri il player per giocare direttamente nella scheda.")
        _form_nuovo_esercizio(conn, paziente_id)
        st.markdown("")
        _lista_esercizi(conn, paziente_id)
    with t2:
        render_libreria(conn, paziente_id)
