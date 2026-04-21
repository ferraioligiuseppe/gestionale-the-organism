# -*- coding: utf-8 -*-
"""
Pannello gestione utenti - SOLO ADMIN.
Permette ad admin di aggiungere, modificare, disattivare utenti e assegnare ruoli.
"""
from __future__ import annotations
import streamlit as st
import datetime


RUOLI_DISPONIBILI = ["clinico", "segreteria", "vision", "osteo", "admin"]
RUOLI_DESCRIZIONI = {
    "admin":      "Accesso completo + gestione utenti",
    "clinico":    "Valutazioni, test, relazioni, questionari",
    "segreteria": "Pazienti, sedute, questionari (no valutazioni cliniche)",
    "vision":     "Optometria, VVF, lenti a contatto",
    "osteo":      "Sezione osteopatia",
}


def _pwd_hash(pw: str) -> str:
    import base64, hashlib, secrets as _sec
    salt = _sec.token_bytes(16)
    salt_b64 = base64.b64encode(salt).decode()
    dk = hashlib.pbkdf2_hmac("sha256", pw.encode(), salt, 260000, dklen=32)
    hash_b64 = base64.b64encode(dk).decode()
    return f"pbkdf2_sha256$260000${salt_b64}${hash_b64}"


def _get_ruoli_utente(conn, user_id: int) -> list:
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT r.name FROM auth_user_roles ur
            JOIN auth_roles r ON r.id = ur.role_id
            WHERE ur.user_id = %s ORDER BY r.name
        """, (user_id,))
        return [row[0] if not isinstance(row, dict) else row["name"]
                for row in (cur.fetchall() or [])]
    except Exception:
        return []


def _get_role_id(conn, role_name: str):
    cur = conn.cursor()
    cur.execute("SELECT id FROM auth_roles WHERE name = %s", (role_name,))
    row = cur.fetchone()
    if row:
        return int(row["id"] if isinstance(row, dict) else row[0])
    # Crea ruolo se non esiste
    cur.execute("INSERT INTO auth_roles(name) VALUES (%s) RETURNING id", (role_name,))
    conn.commit()
    row = cur.fetchone()
    return int(row["id"] if isinstance(row, dict) else row[0])


def render_gestione_utenti(conn, is_admin) -> None:
    """Entry point - blocca accesso se non admin."""

    # CONTROLLO ADMIN - doppio livello
    if not is_admin:
        st.error("Accesso negato. Questa sezione e' riservata agli amministratori.")
        st.stop()
        return

    st.title("Gestione Utenti")
    st.caption("Solo gli amministratori possono accedere a questa sezione.")

    tab_lista, tab_nuovo = st.tabs(["Utenti registrati", "Aggiungi utente"])

    with tab_lista:
        _render_lista_utenti(conn)

    with tab_nuovo:
        _render_form_nuovo_utente(conn)


def _render_lista_utenti(conn) -> None:
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT u.id, u.username, u.email, u.is_active,
                   u.created_at, u.last_login_at, u.display_name
            FROM auth_users u
            ORDER BY u.username
        """)
        utenti = cur.fetchall() or []
    except Exception as e:
        st.error(f"Errore caricamento utenti: {e}")
        return

    if not utenti:
        st.info("Nessun utente registrato.")
        return

    st.caption(f"{len(utenti)} utenti totali")

    for u in utenti:
        if isinstance(u, dict):
            uid       = int(u.get("id"))
            username  = u.get("username", "")
            email     = u.get("email", "") or ""
            attivo    = u.get("is_active", True)
            created   = u.get("created_at", "")
            last_log  = u.get("last_login_at", "")
            disp_name = u.get("display_name", "") or ""
        else:
            uid, username, email, attivo = int(u[0]), u[1], u[2] or "", u[3]
            created, last_log = u[4], u[5]
            disp_name = u[6] if len(u)>6 else ""

        ruoli = _get_ruoli_utente(conn, uid)
        ruoli_str = ", ".join(ruoli) if ruoli else "nessun ruolo"
        stato_ico = "verde" if attivo else "rosso"
        stato_txt = "Attivo" if attivo else "Disattivato"

        label = f"{'[ON]' if attivo else '[OFF]'}  {username}  |  {ruoli_str}"

        with st.expander(label, expanded=False):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**Username:** {username}")
                st.markdown(f"**Nome documenti:** {disp_name or '— non impostato —'}")
                st.markdown(f"**Email:** {email or '—'}")
                st.markdown(f"**Stato:** {stato_txt}")
                if created:
                    st.caption(f"Creato: {str(created)[:10]}")
                if last_log:
                    st.caption(f"Ultimo accesso: {str(last_log)[:16]}")

            with col2:
                st.markdown("**Ruoli attuali:**")
                for r in ruoli:
                    desc = RUOLI_DESCRIZIONI.get(r, "")
                    st.markdown(f"- **{r}**: {desc}")

            st.markdown("---")

            # Modifica display_name
            st.markdown("**Nome per documenti:**")
            new_display = st.text_input(
                "Nome visualizzato",
                value=disp_name,
                key=f"disp_{uid}",
                placeholder="Dott. Mario Rossi - Optometrista",
                label_visibility="collapsed"
            )

            # Modifica ruoli
            st.markdown("**Modifica ruoli:**")
            nuovi_ruoli = st.multiselect(
                "Ruoli assegnati",
                options=RUOLI_DISPONIBILI,
                default=ruoli,
                key=f"ruoli_{uid}",
                help="Seleziona uno o piu' ruoli per questo utente"
            )

            # Reset password
            st.markdown("**Reset password:**")
            new_pw = st.text_input(
                "Nuova password (lascia vuoto per non cambiare)",
                type="password",
                key=f"pw_{uid}"
            )

            col_a, col_b, col_c = st.columns(3)

            with col_a:
                if st.button("Salva modifiche", key=f"save_{uid}", type="primary"):
                    _salva_modifiche_utente(conn, uid, username, nuovi_ruoli, new_pw,
                                             new_display=st.session_state.get(f"disp_{uid}",""))

            with col_b:
                if attivo:
                    if st.button("Disattiva utente", key=f"deact_{uid}"):
                        _set_attivo(conn, uid, False)
                        st.success(f"Utente {username} disattivato.")
                        st.rerun()
                else:
                    if st.button("Riattiva utente", key=f"react_{uid}"):
                        _set_attivo(conn, uid, True)
                        st.success(f"Utente {username} riattivato.")
                        st.rerun()

            with col_c:
                # Protezione: non eliminare se stesso
                me = st.session_state.get("user", {})
                if me.get("username") != username:
                    if st.button("Elimina utente", key=f"del_{uid}"):
                        st.session_state[f"confirm_del_{uid}"] = True

            # Conferma eliminazione
            if st.session_state.get(f"confirm_del_{uid}"):
                st.warning(f"Sei sicuro di voler eliminare **{username}**? Questa azione non e' reversibile.")
                col_x, col_y = st.columns(2)
                with col_x:
                    if st.button("Si, elimina", key=f"yes_del_{uid}"):
                        _elimina_utente(conn, uid)
                        st.success(f"Utente {username} eliminato.")
                        st.session_state.pop(f"confirm_del_{uid}", None)
                        st.rerun()
                with col_y:
                    if st.button("Annulla", key=f"no_del_{uid}"):
                        st.session_state.pop(f"confirm_del_{uid}", None)
                        st.rerun()


def _salva_modifiche_utente(conn, uid: int, username: str,
                            nuovi_ruoli: list, new_pw: str,
                            new_display: str = "") -> None:
    try:
        cur = conn.cursor()

        # Aggiorna ruoli: rimuovi tutti e riaggiungi
        cur.execute("DELETE FROM auth_user_roles WHERE user_id = %s", (uid,))
        for r in nuovi_ruoli:
            rid = _get_role_id(conn, r)
            cur.execute(
                "INSERT INTO auth_user_roles(user_id, role_id) VALUES (%s,%s) "
                "ON CONFLICT DO NOTHING",
                (uid, rid)
            )

        # Aggiorna display_name
        if new_display.strip():
            cur.execute(
                "UPDATE auth_users SET display_name=%s WHERE id=%s",
                (new_display.strip(), uid)
            )

        # Aggiorna password se inserita
        if new_pw.strip():
            if len(new_pw) < 8:
                st.error("La password deve avere almeno 8 caratteri.")
                conn.rollback()
                return
            ph = _pwd_hash(new_pw)
            cur.execute(
                "UPDATE auth_users SET password_hash=%s, must_change_password=FALSE "
                "WHERE id=%s",
                (ph, uid)
            )

        conn.commit()
        st.success(f"Utente {username} aggiornato.")
        st.rerun()

    except Exception as e:
        try: conn.rollback()
        except Exception: pass
        st.error(f"Errore: {e}")


def _set_attivo(conn, uid: int, stato: bool) -> None:
    try:
        cur = conn.cursor()
        cur.execute("UPDATE auth_users SET is_active=%s WHERE id=%s", (stato, uid))
        conn.commit()
    except Exception as e:
        try: conn.rollback()
        except Exception: pass
        st.error(f"Errore: {e}")


def _elimina_utente(conn, uid: int) -> None:
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM auth_user_roles WHERE user_id=%s", (uid,))
        cur.execute("DELETE FROM auth_users WHERE id=%s", (uid,))
        conn.commit()
    except Exception as e:
        try: conn.rollback()
        except Exception: pass
        st.error(f"Errore eliminazione: {e}")


def _render_form_nuovo_utente(conn) -> None:
    st.subheader("Aggiungi nuovo utente")
    st.caption("L'utente potra' accedere immediatamente con le credenziali inserite.")

    c1, c2 = st.columns(2)
    with c1:
        username = st.text_input("Username *", key="nu_username",
                                 placeholder="mario.rossi")
    with c2:
        email = st.text_input("Email", key="nu_email",
                              placeholder="mario@studio.it")

    display_name = st.text_input(
        "Nome completo per documenti *",
        key="nu_display_name",
        placeholder="Dott. Mario Rossi - Optometrista",
        help="Questo nome appare su ricette, relazioni e PDF"
    )

    c3, c4 = st.columns(2)
    with c3:
        pw1 = st.text_input("Password *", type="password", key="nu_pw1",
                            help="Minimo 8 caratteri")
    with c4:
        pw2 = st.text_input("Conferma password *", type="password", key="nu_pw2")

    st.markdown("**Ruoli** (seleziona uno o piu')")
    ruoli_sel = st.multiselect(
        "Ruoli",
        options=RUOLI_DISPONIBILI,
        default=["clinico"],
        key="nu_ruoli",
        label_visibility="collapsed"
    )

    st.markdown("---")
    for r in ruoli_sel:
        st.caption(f"**{r}** - {RUOLI_DESCRIZIONI.get(r, '')}")

    must_change = st.checkbox(
        "L'utente deve cambiare la password al primo accesso",
        value=True,
        key="nu_must_change"
    )

    st.markdown("---")
    if st.button("Crea utente", type="primary", key="nu_salva"):
        _crea_utente(conn, username, email, pw1, pw2, ruoli_sel, must_change,
                     display_name=st.session_state.get("nu_display_name",""))


def _crea_utente(conn, username: str, email: str, pw1: str, pw2: str,
                 ruoli: list, must_change: bool, display_name: str = "") -> None:

    # Validazioni
    if not username.strip():
        st.error("Username obbligatorio.")
        return
    if not pw1:
        st.error("Password obbligatoria.")
        return
    if len(pw1) < 8:
        st.error("La password deve avere almeno 8 caratteri.")
        return
    if pw1 != pw2:
        st.error("Le password non coincidono.")
        return
    if not ruoli:
        st.error("Seleziona almeno un ruolo.")
        return

    try:
        cur = conn.cursor()

        # Verifica username unico
        cur.execute("SELECT id FROM auth_users WHERE username=%s",
                    (username.strip().lower(),))
        if cur.fetchone():
            st.error(f"Username '{username}' gia' esistente.")
            return

        ph = _pwd_hash(pw1)
        cur.execute(
            "INSERT INTO auth_users(username, email, password_hash, "
            "is_active, must_change_password) "
            "VALUES (%s,%s,%s,TRUE,%s) RETURNING id",
            (username.strip().lower(),
             email.strip() or None,
             ph, must_change)
        )
        row = cur.fetchone()
        uid = int(row["id"] if isinstance(row, dict) else row[0])

        for r in ruoli:
            rid = _get_role_id(conn, r)
            cur.execute(
                "INSERT INTO auth_user_roles(user_id, role_id) VALUES (%s,%s) "
                "ON CONFLICT DO NOTHING",
                (uid, rid)
            )

        conn.commit()

        st.success(f"Utente **{username}** creato con ruoli: {', '.join(ruoli)}")
        if must_change:
            st.info("Al primo login l'utente dovra' cambiare la password.")

        # Mostra credenziali
        with st.expander("Credenziali da comunicare all'utente"):
            st.code(f"Username: {username.strip().lower()}\nPassword: {pw1}")
            st.caption("Comunica queste credenziali in modo sicuro (non via email in chiaro).")

    except Exception as e:
        try: conn.rollback()
        except Exception: pass
        st.error(f"Errore creazione utente: {e}")
