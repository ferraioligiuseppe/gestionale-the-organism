# -*- coding: utf-8 -*-
"""
providers/pnev_visiva.py
Provider che estrae dati strutturati da:
  - pnev_json (anamnesi PNEV, questionari, Catagnini, scenario)
  - visita_json (VVF batteria visiva, test vocali, optometria comportamentale)

I dati vengono trasformati in testo leggibile per l'AI che genera la relazione.
"""
from __future__ import annotations
import json
import datetime as dt
from typing import Any, Dict, List, Optional

from .utils import table_exists, fetch_rows_by_period


# ─────────────────────────────────────────────────────────────────────────────
# UTILS LOCALI
# ─────────────────────────────────────────────────────────────────────────────

def _safe_json(raw) -> dict:
    if not raw:
        return {}
    if isinstance(raw, dict):
        return raw
    try:
        return json.loads(raw)
    except Exception:
        return {}

def _fmt(val, unit="", default="nd") -> str:
    if val is None or val == "" or val == 0 or val == "—":
        return default
    return f"{val}{unit}"

def _ris_ds(ds_val, inverso=True) -> str:
    """Converte DS in interpretazione testuale."""
    if ds_val is None:
        return ""
    d = -float(ds_val) if inverso else float(ds_val)
    if d >= 1.0:   return "(ottimale)"
    if d >= 0.0:   return "(nella norma)"
    if d >= -1.0:  return "(1 DS sotto norma)"
    if d >= -2.0:  return "(2 DS sotto norma — significativo)"
    return "(3+ DS sotto norma — clinicamente rilevante)"


# ─────────────────────────────────────────────────────────────────────────────
# ESTRAZIONE PNEV JSON → testo strutturato
# ─────────────────────────────────────────────────────────────────────────────

def _estrai_pnev(pnev_json: dict) -> dict:
    """Trasforma pnev_json in struttura testuale per l'AI."""
    output = {}

    # ── Anamnesi Castagnini ────────────────────────────────────────────────
    cat = pnev_json.get("anamnesi_castagnini") or pnev_json.get("anamnesi_catagnini") or {}
    if cat:
        sez = []
        grav = cat.get("gravidanza", {})
        if grav:
            sez.append(f"Gravidanza: settimane {_fmt(grav.get('settimane_gestazione'))}, "
                       f"complicanze: {_fmt(grav.get('complicanze','nessuna'))}, "
                       f"stress materno: {_fmt(grav.get('stress_materno','no'))}")
        parto = cat.get("parto", {})
        if parto:
            sez.append(f"Parto: {_fmt(parto.get('tipo_parto'))}, "
                       f"complicanze: {_fmt(parto.get('complicanze','nessuna'))}")
        neo = cat.get("neonatale", {})
        if neo:
            sez.append(f"Periodo neonatale: Apgar {_fmt(neo.get('apgar'))}, "
                       f"allattamento: {_fmt(neo.get('allattamento_tipo'))}")
        sm = cat.get("sviluppo_motorio", {})
        if sm:
            sez.append(f"Sviluppo motorio: striscio {_fmt(sm.get('striscio_mesi'))} mesi, "
                       f"gattonamento {_fmt(sm.get('gattonamento_mesi'))} mesi, "
                       f"deambulazione {_fmt(sm.get('deambulazione_mesi'))} mesi")
        ss = cat.get("sviluppo_sensoriale", {})
        if ss:
            sez.append(f"Sviluppo sensoriale: prime parole {_fmt(ss.get('prime_parole_mesi'))} mesi")
        output["anamnesi_perinatale"] = "; ".join(sez) if sez else "Non compilata"

    # ── Scenario clinico ───────────────────────────────────────────────────
    scenario = pnev_json.get("scenario", {})
    if scenario:
        items = []
        for k, v in scenario.items():
            if isinstance(v, bool) and v:
                items.append(k.replace("_", " "))
            elif isinstance(v, str) and v and v != "—":
                items.append(f"{k.replace('_',' ')}: {v}")
        if items:
            output["scenario_clinico"] = "; ".join(items[:15])

    # ── Questionari PNEV ──────────────────────────────────────────────────
    q = pnev_json.get("questionari", {}) or {}

    # INPPS
    inpps = q.get("inpps_screening_genitori", {})
    if inpps and inpps.get("screening"):
        sc = inpps["screening"]
        pos = inpps.get("positivi", {})
        output["inpps"] = (
            f"INPPS screening: totale positivi {sc.get('totale_positivi',0)} "
            f"(neurologica/scuola {pos.get('neurologica_scuola',0)}, "
            f"nutrizione {pos.get('nutrizione',0)}, "
            f"udito {pos.get('udito_madaule',0)}) "
            f"— cut-off {sc.get('cutoff',7)} — "
            f"{'POSITIVO (possibile immaturità neuromotoria)' if sc.get('flag_possibile_immaturita_neuromotoria') else 'negativo'}"
        )

    # Melillo adulti
    mel_a = q.get("melillo_adulti", {})
    if mel_a and mel_a.get("scoring"):
        sc = mel_a["scoring"]
        output["melillo_adulti"] = (
            f"Melillo Adulti: A(sinistra)={sc.get('tot_a',0)} B(destra)={sc.get('tot_b',0)} "
            f"→ Dominanza {sc.get('dominanza','—')} (diff={sc.get('differenza',0)})"
        )

    # Melillo bambini
    mel_b = q.get("melillo_bambini", {})
    if mel_b and mel_b.get("scoring"):
        sc = mel_b["scoring"]
        output["melillo_bambini"] = (
            f"Melillo Bambini: caratteristiche Destro={sc.get('tot_destro',0)} "
            f"Sinistro={sc.get('tot_sinistro',0)}"
        )

    # Fisher auditivo
    fish = q.get("fisher_auditivo_bambini", {})
    if fish and fish.get("scoring"):
        sc = fish["scoring"]
        output["fisher_auditivo"] = (
            f"Fisher Auditivo: {sc.get('selezionati',0)}/25 problemi, "
            f"punteggio {sc.get('punteggio_pct',0)}% "
            f"{'— SOTTO CUTOFF (72%)' if sc.get('flag_valutazione') else '— nella norma'}"
        )

    # Visione bambini/adulti
    for key_q, label in [("visione_bambini","Visione Bambini"),("visione_adulti","Visione Adulti")]:
        vis = q.get(key_q, {})
        if vis and vis.get("scoring"):
            sc = vis["scoring"]
            tot_s = sc.get("tot_sintomi", sc.get("totale", 0))
            output[key_q] = f"{label}: {tot_s} sintomi selezionati"

    return output


# ─────────────────────────────────────────────────────────────────────────────
# ESTRAZIONE VISITA_JSON → testo strutturato
# ─────────────────────────────────────────────────────────────────────────────

def _estrai_vvf(visita_json: dict) -> dict:
    """Trasforma visita_json (VVF + test vocali + optometria) in struttura per AI."""
    output = {}
    vvf = visita_json.get("valutazione_visiva_funzionale", {})

    if not vvf:
        return output

    # ── S1 Preliminari ────────────────────────────────────────────────────
    s1 = vvf.get("s1", {})
    if s1:
        dom = f"Dominanza: occhio {_fmt(s1.get('dom_occhio'))} mano {_fmt(s1.get('dom_mano'))} piede {_fmt(s1.get('dom_piede'))}"
        ppc = f"PPC rottura {_fmt(s1.get('ppc_rot'),'cm')} recupero {_fmt(s1.get('ppc_rec'),'cm')}"
        ct = f"Cover: lon {_fmt(s1.get('ct_lon'))} vic {_fmt(s1.get('ct_vic'))}"
        stereo = f"Stereopsi anelli {_fmt(s1.get('stereo_anel','\"'))}"
        output["preliminari"] = f"{dom}; {ppc}; {ct}; {stereo}"

    # ── S2 Spaziali OEP ───────────────────────────────────────────────────
    s2 = vvf.get("s2", {})
    if s2:
        oep_items = []
        norme_oep = {
            "#3": ("Foria lon", 1.0, 2.0),
            "#13A": ("Foria vic", 3.0, 3.0),
            "MEM": ("MEM", 0.5, 0.25),
            "#20": ("ARP", 2.0, 0.5),
            "#21": ("ARN", -1.0, 0.5),
        }
        for code, (label, media, ds) in norme_oep.items():
            val = s2.get(code)
            if val and val != 0:
                d = (float(val) - media) / ds
                ris = _ris_ds(-d if code in ("#3","#13A") else d, inverso=False)
                oep_items.append(f"{label}: {val} {ris}")
        if oep_items:
            output["analisi_oep"] = "; ".join(oep_items)

    # ── S3 Oculomotori ────────────────────────────────────────────────────
    s3 = vvf.get("s3", {})
    if s3:
        oculom = []
        # DEM
        dem = s3.get("dem", {})
        if dem.get("tipologia"):
            calc = dem.get("calcoli", dem)
            oculom.append(
                f"DEM: TV={_fmt(calc.get('tv_adj'),'s')} TH={_fmt(calc.get('th_adj'),'s')} "
                f"Ratio={_fmt(calc.get('ratio'))} → Tipologia {calc.get('tipologia','—')}"
            )
        # K-D
        kd = s3.get("kd", {})
        if kd.get("tot_tempo"):
            oculom.append(f"King-Devick: {kd['tot_tempo']:.1f}s totali, {kd.get('tot_errori',0)} errori")
        # NSUCO
        nsuco = s3.get("nsuco", {})
        if nsuco:
            sacc_ab = nsuco.get("saccadi_abilita")
            purs_ab = nsuco.get("pursuit_abilita")
            if sacc_ab: oculom.append(f"NSUCO saccadi abilità {sacc_ab}/5")
            if purs_ab: oculom.append(f"NSUCO pursuit abilità {purs_ab}/5")
        # Groffman
        gr = s3.get("groffman", {})
        if gr.get("totale"):
            oculom.append(f"Groffman: {gr['totale']}/50")
        # VT
        vt = s3.get("visual_tracking", {})
        if vt.get("pct_corr"):
            oculom.append(f"Visual Tracking: {vt['pct_corr']:.0f}%")
        if oculom:
            output["test_oculomotori"] = "; ".join(oculom)

    # ── Test Vocali (DEM/KD da registrazione) ─────────────────────────────
    tv = visita_json.get("test_vocali", {})
    if tv:
        vocali = []
        dem_v = tv.get("dem", {})
        if dem_v.get("calcoli", {}).get("tipologia"):
            c = dem_v["calcoli"]
            vocali.append(
                f"DEM (vocale): TV={_fmt(c.get('tv_adj'),'s')} TH={_fmt(c.get('th_adj'),'s')} "
                f"→ {c.get('tipologia','—')}"
            )
        kd_v = tv.get("kd", {})
        if kd_v.get("tot_tempo"):
            vocali.append(f"K-D (vocale): {kd_v['tot_tempo']:.1f}s / {kd_v.get('tot_errori',0)} err")
        vt_v = tv.get("visual_tracking", {})
        if vt_v.get("calcoli", {}).get("pct"):
            vocali.append(f"VT (vocale): {vt_v['calcoli']['pct']}% accuratezza")
        if vocali:
            output["test_vocali"] = "; ".join(vocali)

    # ── S4 Accomodazione ──────────────────────────────────────────────────
    s4 = vvf.get("s4", {})
    if s4:
        acc = []
        ppa = s4.get("ppa", {})
        if ppa.get("bino_dt"):
            acc.append(f"PPA bino {ppa['bino_dt']:.2f}dt")
        ff = s4.get("focus_flex", {})
        if ff.get("bino"):
            acc.append(f"Focus Flex bino {ff['bino']}cpm")
        fus = s4.get("fusion_flex", {})
        if fus.get("bino"):
            acc.append(f"Fusion Flex {fus['bino']}cpm")
        if acc:
            output["accomodazione"] = "; ".join(acc)

    # ── S5 TVPS-3 ────────────────────────────────────────────────────────
    s5 = vvf.get("s5", {})
    if s5 and s5.get("calcoli", {}).get("std"):
        c = s5["calcoli"]
        output["tvps3"] = (
            f"TVPS-3: standard score {c['std']} ({c.get('classifica','—')}, "
            f"{c.get('percentile','—')}° percentile)"
        )
        # Profilo subtest
        scaled = s5.get("scaled", {})
        subs = []
        nomi = {"disc":"Discriminazione","mem":"Memoria","spaz":"Rel.Spaziali",
                "cost":"Costanza","seq":"Mem.Sequenziale","fig":"Figura-sfondo","chius":"Chiusura"}
        for k, nome in nomi.items():
            sc = scaled.get(k)
            if sc is not None and sc < 7:
                subs.append(f"{nome}={sc} (basso)")
        if subs:
            output["tvps3"] += f". Aree deboli: {', '.join(subs)}"

    # ── S6 Visuo-Spaziali ─────────────────────────────────────────────────
    s6 = vvf.get("s6", {})
    if s6:
        spaz = []
        piaget = s6.get("piaget", {})
        if piaget:
            eta_p = piaget.get("eta", 0)
            superati = [t for t in ["A","B","C","D","E"]
                        if piaget.get(f"{t}_pct", 0) >= 75]
            spaz.append(f"Piaget (età {eta_p}): livelli superati {', '.join(superati) or 'nessuno'}")
        gardner = s6.get("gardner", {})
        if gardner.get("es_tot") is not None:
            spaz.append(f"Gardner: esecuzione {gardner.get('es_tot',0)} errori")
        if spaz:
            output["visuo_spaziali"] = "; ".join(spaz)

    # ── S7 Grosso Motorio ─────────────────────────────────────────────────
    s7 = vvf.get("s7", {})
    if s7:
        gm = []
        suny = s7.get("suny", {})
        if suny.get("livello"):
            gm.append(f"SUNY: livello {suny['livello']}")
        wachs = s7.get("wachs", {})
        if wachs.get("livello"):
            gm.append(f"WACHS: livello {wachs['livello']}")
        if gm:
            output["grosso_motorio"] = "; ".join(gm)

    # ── S8 Visuo-Motoria ──────────────────────────────────────────────────
    s8 = vvf.get("s8", {})
    if s8:
        vm = []
        vmi = s8.get("vmi", {})
        if vmi.get("std"):
            vm.append(f"VMI: std {vmi['std']} ({vmi.get('classifica','—')}, {vmi.get('percentile','—')}° %ile)")
        wold = s8.get("wold", {})
        if wold.get("t1"):
            e_tot = int(wold.get("e1",0)+wold.get("e2",0)+wold.get("e3",0))
            vm.append(f"WOLD: {e_tot} errori totali")
        if vm:
            output["visuo_motoria"] = "; ".join(vm)

    # ── S9 Visuo-Uditiva ──────────────────────────────────────────────────
    s9 = vvf.get("s9", {})
    if s9:
        vu = []
        avit = s9.get("avit", {})
        if avit.get("corretti"):
            vu.append(f"AVIT: {avit['corretti']} corretti")
        vads = s9.get("vads", {})
        if vads.get("tot"):
            vu.append(f"VADS: tot {vads['tot']}")
        monroe = s9.get("monroe", {})
        if monroe.get("punti"):
            vu.append(f"Monroe Visual III: {monroe['punti']} punti")
        getman = s9.get("getman", {})
        if getman.get("punti") is not None:
            vu.append(f"Getman: {getman['punti']}/12 (norma ≥{getman.get('norma',7)})")
        if vu:
            output["visuo_uditiva_memoria"] = "; ".join(vu)

    # ── S10 SVV ───────────────────────────────────────────────────────────
    s10 = vvf.get("s10", {})
    if s10:
        svv = s10.get("svv", {})
        if svv.get("score"):
            output["svv"] = (
                f"SVV score: {svv['score']}/12 "
                f"({'alta probabilità SVV' if svv['score']>=6 else 'possibile SVV' if svv['score']>=3 else 'basso rischio'})"
            )

    # ── Optometria Comportamentale ─────────────────────────────────────────
    optom = visita_json.get("optometria_comportamentale", {})
    if optom:
        opt = []
        ref = optom.get("refrattivo", {}).get("lontano", {})
        if ref.get("sf_od") or ref.get("sf_os"):
            opt.append(f"Rx: OD {_fmt(ref.get('sf_od'),'+.2f')} OS {_fmt(ref.get('sf_os'),'+.2f')}")
        strab = optom.get("strabismo", {})
        if strab.get("deviazione") and strab["deviazione"] != "—":
            opt.append(f"Deviazione: {strab['deviazione']}, stereo: {strab.get('stereoacuita','—')}")
        perf = optom.get("performance", {})
        if perf.get("kd_totale"):
            opt.append(f"K-D (optom): {perf['kd_totale']:.1f}s")
        if perf.get("dem_interpretazione") and perf["dem_interpretazione"] != "—":
            opt.append(f"DEM (optom): {perf['dem_interpretazione']}")
        if opt:
            output["optometria_comportamentale"] = "; ".join(opt)

    return output


# ─────────────────────────────────────────────────────────────────────────────
# DIAGNOSI → testo per AI
# ─────────────────────────────────────────────────────────────────────────────

def _estrai_diagnosi(vvf: dict) -> str:
    """
    Ri-esegue la diagnosi automatica sui dati VVF e ritorna testo.
    Importa la funzione già esistente in ui_valutazione_visiva_funzionale.
    """
    try:
        from modules.pnev.ui_valutazione_visiva_funzionale import _diagnosi
        diag_list = _diagnosi(vvf)
        if not diag_list:
            return "Nessun pattern disfunzionale rilevato."
        lines = []
        for d in diag_list:
            livello = d.get("livello","—")
            titolo = d.get("titolo","—")
            criteri = "; ".join(d.get("criteri",[]))
            note = d.get("note","")
            lines.append(f"[{livello.upper()}] {titolo}: {criteri}. {note}")
        return "\n".join(lines)
    except Exception as e:
        return f"Diagnosi non disponibile: {e}"


# ─────────────────────────────────────────────────────────────────────────────
# PROVIDER PRINCIPALE
# ─────────────────────────────────────────────────────────────────────────────

def load_pnev_dataset(
    conn, paziente_id: int,
    date_from: dt.date, date_to: dt.date,
    include_deleted: bool = False,
) -> Dict[str, Any]:
    """
    Carica e struttura tutti i dati PNEV per un paziente nel periodo dato.
    """
    if not table_exists(conn, "anamnesi"):
        return {"pnev": {"presente": False}}

    rows = fetch_rows_by_period(
        conn, "anamnesi", paziente_id, date_from, date_to,
        include_deleted=include_deleted, limit=10
    )

    valutazioni = []
    for row in rows:
        pnev_raw = row.get("pnev_json") if hasattr(row,"get") else None
        pnev_json = _safe_json(pnev_raw)
        if not pnev_json:
            continue

        dati = _estrai_pnev(pnev_json)
        dati["data"] = str(row.get("data_anamnesi","") if hasattr(row,"get") else "")
        dati["motivo"] = str(row.get("motivo","") if hasattr(row,"get") else "")
        valutazioni.append(dati)

    return {
        "pnev": {
            "presente": bool(valutazioni),
            "n_valutazioni": len(valutazioni),
            "valutazioni": valutazioni,
        }
    }


def load_visiva_dataset(
    conn, paziente_id: int,
    date_from: dt.date, date_to: dt.date,
    include_deleted: bool = False,
) -> Dict[str, Any]:
    """
    Carica e struttura i dati di valutazione visiva funzionale.
    """
    if not table_exists(conn, "valutazioni_visive"):
        return {"valutazione_visiva": {"presente": False}}

    rows = fetch_rows_by_period(
        conn, "valutazioni_visive", paziente_id, date_from, date_to,
        include_deleted=include_deleted, limit=5
    )

    valutazioni = []
    for row in rows:
        visita_raw = row.get("visita_json") if hasattr(row,"get") else None
        visita_json = _safe_json(visita_raw)
        if not visita_json:
            continue

        dati = _estrai_vvf(visita_json)
        vvf = visita_json.get("valutazione_visiva_funzionale", {})
        dati["diagnosi_automatica"] = _estrai_diagnosi(vvf)
        dati["data"] = str(row.get("data_visita","") if hasattr(row,"get") else "")
        dati["tipo"] = str(row.get("tipo_visita","") if hasattr(row,"get") else "")
        valutazioni.append(dati)

    return {
        "valutazione_visiva": {
            "presente": bool(valutazioni),
            "n_valutazioni": len(valutazioni),
            "valutazioni": valutazioni,
        }
    }
