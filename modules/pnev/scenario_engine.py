# -*- coding: utf-8 -*-
"""
modules/pnev/scenario_engine.py

Motore di scenari clinici basato sul metodo Castagnini/FSC.
Legge i dati dell'anamnesi Catagnini (anamnesi_catagnini in pnev_json)
e produce:
  - livello di rischio complessivo (NORMALE / INCERTO / A RISCHIO / ALTO RISCHIO)
  - fattori di rischio attivati (con fonte Castagnini)
  - milestone mancanti o in ritardo rispetto all'età
  - scenario testuale per il clinico
  - indicazioni operative (approfondire / monitorare / trattare subito)

Riferimenti clinici:
  - Castagnini M. — Protocollo esame neuropsicomotorio 0-3 mesi e 0-12 mesi (FSC)
  - Castagnini M. — Fattori di rischio parto/perinatale (doc. 3)
  - Castagnini M. — Statistiche intervento precoce (doc. 4):
      0-3 mesi → 95% recupero | 4-8 mesi → 10% | oltre 9 mesi → raramente
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from datetime import date


# ── Livelli di rischio ────────────────────────────────────────────────────────

LIVELLO_NORMALE      = "NORMALE"
LIVELLO_INCERTO      = "INCERTO"
LIVELLO_A_RISCHIO    = "A RISCHIO"
LIVELLO_ALTO_RISCHIO = "ALTO RISCHIO"

COLORE = {
    LIVELLO_NORMALE:      "green",
    LIVELLO_INCERTO:      "orange",
    LIVELLO_A_RISCHIO:    "red",
    LIVELLO_ALTO_RISCHIO: "darkred",
}

EMOJI = {
    LIVELLO_NORMALE:      "✅",
    LIVELLO_INCERTO:      "⚠️",
    LIVELLO_A_RISCHIO:    "🔴",
    LIVELLO_ALTO_RISCHIO: "🚨",
}


# ── Dataclass risultato ───────────────────────────────────────────────────────

@dataclass
class ScenarioResult:
    livello: str = LIVELLO_NORMALE
    punteggio: int = 0                  # somma fattori di rischio pesati
    fattori_rischio: List[str] = field(default_factory=list)
    milestone_ritardo: List[str] = field(default_factory=list)
    milestone_patologici: List[str] = field(default_factory=list)
    scenario_testo: str = ""
    indicazioni: List[str] = field(default_factory=list)
    urgenza: str = ""                   # "monitorare" / "approfondire" / "trattare subito"
    eta_funzionale_stimata: str = ""    # es. "6-8 settimane"
    note_cliniche: str = ""


# ── Fattori di rischio perinatali (Castagnini doc. 3 e 4) ────────────────────
# peso: 1 = fattore semplice, 2 = fattore importante, 3 = fattore critico

FATTORI_PARTO = [
    # (chiave_in_anam, descrizione, peso)
    ("gemellare",           "Parto gemellare",                          2),
    ("pretermine",          "Parto pretermine (<38 sett.)",             3),
    ("posttermine",         "Parto post-termine (>42 sett.)",           1),
    ("forcipe",             "Uso di forcipe",                           3),
    ("ventosa",             "Uso di ventosa",                           2),
    ("cesareo_urgenza",     "Cesareo d'urgenza",                        2),
    ("distress_fetale",     "Distress fetale al parto",                 3),
    ("cordone",             "Problema di cordone",                      2),
    ("apgar_basso",         "APGAR basso (< 7 al 1° minuto)",           3),
    ("apgar_5_basso",       "APGAR basso (< 7 al 5° minuto)",           3),
    ("liquido_amnio",       "Liquido amniotico tinto/problematico",      2),
    ("ospedalizzazione",    "Ospedalizzazione neonato post-parto",       2),
    ("travaglio_prolungato","Travaglio prolungato (>12h)",               1),
    ("podalica",            "Presentazione podalica o trasversa",        2),
]

FATTORI_GRAVIDANZA = [
    ("ipertensione",        "Ipertensione/preeclampsia in gravidanza",  2),
    ("infezioni",           "Infezioni in gravidanza",                  2),
    ("stress_emotivo",      "Stress emotivo grave in gravidanza",       1),
    ("farmaci",             "Farmaci/sostanze in gravidanza",           2),
    ("movimenti_ridotti",   "Movimenti fetali ridotti",                 2),
    ("pretermine_sett",     "Gestazione < 34 settimane",                3),
]

FATTORI_NEONATALE = [
    ("tono_ipotonico",      "Ipotonia muscolare alla nascita",          3),
    ("tono_ipertonico",     "Ipertonia muscolare alla nascita",         2),
    ("coliche_severe",      "Coliche severe",                          1),
    ("suzione_severa",      "Difficoltà di suzione severa",             2),
    ("pianto_inconsolabile","Pianto inconsolabile",                     1),
    ("pianto_assente",      "Pianto assente/scarso",                    3),
]

FATTORI_SVILUPPO = [
    ("gattonamento_saltato","Gattonamento saltato",                     2),
    ("lateraliz_precoce",   "Lateralizzazione precoce (<12 mesi)",      2),
    ("passi_tardivi",       "Primi passi molto tardivi (>18 mesi)",     2),
]

FATTORI_SENSORIALI = [
    ("contatto_ridotto",    "Contatto oculare ridotto",                 3),
    ("contatto_assente",    "Contatto oculare assente",                 3),
    ("suoni_ipo",           "Iporeattività ai suoni",                   2),
    ("imitazione_assente",  "Imitazione assente",                       2),
    ("parole_tardive",      "Prime parole molto tardive (>18 mesi)",    2),
]

FATTORI_FAMILIARI = [
    ("fam_autismo",         "Familiarità per disturbi autistici",       2),
    ("fam_dsa_adhd",        "Familiarità per DSA/ADHD",                 1),
]


# ── Milestone Castagnini per età (settimane / mesi) ──────────────────────────
# Fonte: Protocollo 0-3 mesi e 0-12 mesi
# (descrizione, età_attesa_mesi, tipo: "raggiunta"/"assente")

MILESTONE_SUPINO = [
    # (chiave, descrizione, mesi_attesi, patol_se_assente_dopo_mesi, patol_sempre)
    ("equilibrio_supino",       "Mantiene equilibrio supino dopo sbilanciamenti",  1.5,  False),
    ("testa_linea_mediana",     "Mantiene testa sulla linea mediana",              1.5,  False),
    ("ruota_testa",             "Ruota liberamente la testa",                       2.5,  False),
    ("arti_sup_liberi",         "Arti superiori liberi (non fissi)",                1.5,  False),
    ("arti_sup_linea_med",      "Arti sup. raggiungono linea mediana",              2.5,  False),
    ("coordinaz_occhio_mano",   "Coordinazione occhio-mano-bocca",                  3.0,  False),
    ("arti_inf_liberi",         "Arti inferiori liberamente estesi",                1.5,  False),
    ("mano_bocca",              "Porta le mani alla bocca",                         3.0,  False),
]

MILESTONE_PRONO = [
    ("mantiene_prono",          "Mantiene posizione prona",                         1.5,  False),
    ("appoggio_avambracci",     "Appoggio simmetrico su avambracci",                2.0,  False),
    ("appoggio_gomiti_90",      "Appoggio sui gomiti a 90°",                        3.0,  False),
    ("solleva_testa_prono",     "Solleva la testa da terra (prono)",                2.0,  False),
]

MILESTONE_COMUNICAZIONE = [
    ("fissa_osservatore",       "Fissa chi lo osserva",                             1.5,  False),
    ("sorriso_sociale",         "Sorriso sociale",                                   2.0,  False),
    ("emette_suoni",            "Emette suoni gutturali/lallazione",                 2.0,  False),
    ("segue_oggetto",           "Segue oggetto in movimento",                        2.5,  False),
]

SEGNI_SEMPRE_PATOLOGICI = [
    "Reclinazione del capo fissa",
    "Estrema rotazione del capo fissa",
    "Tronco asimmetrico fisso",
    "Bacino sollevato fisso",
    "Arti superiori rigidamente estesi e reiettati",
    "Arti inferiori estesi rigidamente e fissi",
    "Piedi in inversione fissi",
]


# ── Motore principale ─────────────────────────────────────────────────────────

def _eta_mesi(data_nascita: Optional[str]) -> Optional[float]:
    """Calcola l'età in mesi dalla data di nascita (formato ISO yyyy-mm-dd)."""
    if not data_nascita:
        return None
    try:
        dn = date.fromisoformat(str(data_nascita).strip())
        oggi = date.today()
        delta = oggi - dn
        return round(delta.days / 30.44, 1)
    except Exception:
        return None


def _val(d: dict, *keys, default="") -> Any:
    """Naviga dizionari annidati in modo sicuro."""
    obj = d
    for k in keys:
        if not isinstance(obj, dict):
            return default
        obj = obj.get(k, default)
    return obj if obj is not None else default


def calcola_scenario(
    pnev_json: Dict[str, Any],
    data_nascita: Optional[str] = None,
    eta_mesi_override: Optional[float] = None,
) -> ScenarioResult:
    """
    Calcola lo scenario clinico dal pnev_json del paziente.

    Args:
        pnev_json: dict caricato da pnev_load()
        data_nascita: stringa ISO (yyyy-mm-dd) — per calcolo età
        eta_mesi_override: se fornita, usa questa età invece di calcolarla

    Returns:
        ScenarioResult con livello, fattori, milestone, scenario testuale
    """
    result = ScenarioResult()
    cat = pnev_json.get("anamnesi_catagnini", {}) if isinstance(pnev_json, dict) else {}
    if not isinstance(cat, dict):
        cat = {}

    eta = eta_mesi_override
    if eta is None:
        eta = _eta_mesi(data_nascita)

    # ── 1. Fattori di rischio perinatali ─────────────────────────────────────
    punteggio = 0
    fattori = []

    grav = cat.get("gravidanza", {}) or {}
    parto = cat.get("parto", {}) or {}
    neo = cat.get("neonatale", {}) or {}
    sm = cat.get("sviluppo_motorio", {}) or {}
    ss = cat.get("sviluppo_sensoriale", {}) or {}
    sf = cat.get("storia_familiare", {}) or {}
    als = cat.get("alimentazione_sonno", {}) or {}

    # Gravidanza
    comp_g = grav.get("complicanze", {}) or {}
    if comp_g.get("ipertensione"):
        fattori.append("Ipertensione/preeclampsia in gravidanza"); punteggio += 2
    if comp_g.get("infezioni"):
        fattori.append("Infezioni in gravidanza"); punteggio += 2
    if comp_g.get("stress_emotivo"):
        fattori.append("Stress emotivo grave in gravidanza"); punteggio += 1
    if comp_g.get("farmaci"):
        fattori.append("Farmaci/sostanze in gravidanza"); punteggio += 2
    if grav.get("movimenti_fetali") == "ridotti":
        fattori.append("Movimenti fetali ridotti"); punteggio += 2
    sett = grav.get("settimane_numero")
    if sett and int(sett) < 34:
        fattori.append(f"Grande prematurità ({sett} sett. — alto rischio)"); punteggio += 4
    elif "pre-termine" in str(grav.get("settimane", "")):
        fattori.append("Parto pretermine"); punteggio += 3
    if grav.get("tipo") == "gemellare":
        fattori.append("Gravidanza gemellare"); punteggio += 2

    # Parto
    comp_p = parto.get("complicanze", {}) or {}
    strm = parto.get("strumenti", {}) or {}
    if strm.get("forcipe"):
        fattori.append("Uso di forcipe al parto"); punteggio += 3
    if strm.get("ventosa"):
        fattori.append("Uso di ventosa al parto"); punteggio += 2
    if parto.get("tipo") == "cesareo d'urgenza":
        fattori.append("Cesareo d'urgenza"); punteggio += 2
    if comp_p.get("distress_fetale"):
        fattori.append("Distress fetale al parto"); punteggio += 3
    if comp_p.get("cordone"):
        fattori.append("Problemi di cordone al parto"); punteggio += 2
    apgar1 = parto.get("apgar_1")
    if apgar1 is not None and int(apgar1) < 7:
        fattori.append(f"APGAR basso al 1° minuto ({apgar1})"); punteggio += 3
    apgar5 = parto.get("apgar_5")
    if apgar5 is not None and int(apgar5) < 7:
        fattori.append(f"APGAR basso al 5° minuto ({apgar5})"); punteggio += 3
    if parto.get("ospedalizzazione_neonato") == "sì":
        mot = parto.get("ospedalizzazione_motivo", "")
        fattori.append(f"Ospedalizzazione neonato{' — ' + mot if mot else ''}"); punteggio += 2
    if "prolungato" in str(parto.get("durata_travaglio", "")):
        fattori.append("Travaglio prolungato (>12h)"); punteggio += 1
    if parto.get("presentazione") in ("podalica", "trasversa"):
        fattori.append(f"Presentazione {parto.get('presentazione')}"); punteggio += 2

    # Periodo neonatale
    if neo.get("tono_nascita") == "ipotonico":
        fattori.append("Ipotonia muscolare alla nascita"); punteggio += 3
    if neo.get("tono_nascita") == "ipertonico":
        fattori.append("Ipertonia muscolare alla nascita"); punteggio += 2
    if neo.get("difficolta_suzione") == "severa":
        fattori.append("Difficoltà di suzione severa"); punteggio += 2
    if neo.get("pianto") == "inconsolabile":
        fattori.append("Pianto inconsolabile neonatale"); punteggio += 1
    if neo.get("pianto") == "scarso/assente":
        fattori.append("Pianto scarso o assente (segnale importante)"); punteggio += 3
    if neo.get("coliche") == "severe":
        fattori.append("Coliche severe"); punteggio += 1

    # Riflessi neonatali anomali
    rifl = neo.get("riflessi", {}) or {}
    rifl_anom = {
        "moro":       ("Riflesso di Moro anomalo", 3),
        "suzione":    ("Riflesso di suzione anomalo", 2),
        "prensione":  ("Riflesso di prensione anomalo", 2),
        "babinski":   ("Babinski anomalo", 1),
        "galant":     ("Riflesso di Galant anomalo", 2),
        "tonic_neck": ("RTLN anomalo (collo tonico)", 2),
    }
    for k, (desc, peso) in rifl_anom.items():
        if rifl.get(k) in ("assente", "asimmetrico"):
            fattori.append(f"{desc} ({rifl.get(k)})"); punteggio += peso

    # Sviluppo motorio
    if sm.get("gattonamento_fatto") in ("no", "saltato"):
        fattori.append(f"Gattonamento {sm.get('gattonamento_fatto')}"); punteggio += 2
    if sm.get("lateralizzazione_precoce") not in ("", "no", "non osservata"):
        fattori.append(f"Lateralizzazione precoce: {sm.get('lateralizzazione_precoce')}"); punteggio += 2
    if sm.get("primi_passi_mesi") and int(sm.get("primi_passi_mesi", 0)) > 18:
        fattori.append(f"Primi passi molto tardivi ({sm.get('primi_passi_mesi')} mesi)"); punteggio += 2

    # Sviluppo sensoriale/comunicativo
    if ss.get("contatto_oculare") == "assente":
        fattori.append("Contatto oculare assente"); punteggio += 3
    elif ss.get("contatto_oculare") == "ridotto":
        fattori.append("Contatto oculare ridotto"); punteggio += 2
    if ss.get("risposta_suoni") == "iporeattivo":
        fattori.append("Iporeattività ai suoni"); punteggio += 2
    if ss.get("imitazione") == "assente":
        fattori.append("Assenza di imitazione"); punteggio += 2
    pm = ss.get("prime_parole_mesi")
    if pm and int(pm) > 18:
        fattori.append(f"Prime parole molto tardive ({pm} mesi)"); punteggio += 2

    # Familiarità
    if sf.get("familiarita_autismo") == "sì":
        fattori.append("Familiarità per disturbi autistici"); punteggio += 2
    if sf.get("familiarita_dsa_adhd") == "sì":
        fattori.append("Familiarità per DSA/ADHD"); punteggio += 1

    result.fattori_rischio = fattori
    result.punteggio = punteggio

    # ── 2. Milestone mancanti / in ritardo (se età disponibile) ──────────────
    ritardi = []
    if eta is not None:
        # controllo capo
        capo = sm.get("controllo_capo_mesi")
        if capo and float(capo) > eta and eta > 3:
            ritardi.append(f"Controllo capo non ancora raggiunto (atteso entro 3 mesi, età attuale {eta:.0f} mesi)")
        # gattonamento
        gat_mesi = sm.get("gattonamento_mesi")
        if sm.get("gattonamento_fatto") == "sì" and gat_mesi:
            if float(gat_mesi) > 11:
                ritardi.append(f"Gattonamento tardivo ({gat_mesi} mesi — atteso 7-10 mesi)")
        # seduta
        sed = sm.get("stazione_seduta_mesi")
        if sed and float(sed) > 9 and eta > 9:
            ritardi.append(f"Stazione seduta tardiva ({sed} mesi — atteso entro 8 mesi)")
        # primi passi
        pp = sm.get("primi_passi_mesi")
        if pp and float(pp) > 15 and eta > 15:
            ritardi.append(f"Deambulazione tardiva ({pp} mesi — atteso 12-15 mesi)")
        # sorriso sociale
        sor = ss.get("sorriso_sociale_mesi")
        if sor and float(sor) > 3 and eta > 3:
            ritardi.append(f"Sorriso sociale tardivo ({sor} mesi — atteso entro 2 mesi)")
        # prime parole
        ppm = ss.get("prime_parole_mesi")
        if ppm and float(ppm) > 15 and eta > 15:
            ritardi.append(f"Prime parole tardive ({ppm} mesi — atteso 10-12 mesi)")
        # risposta al nome
        nom = ss.get("risposta_nome_mesi")
        if nom and float(nom) > 12 and eta > 12:
            ritardi.append(f"Risposta al nome tardiva ({nom} mesi — atteso entro 9 mesi)")

    result.milestone_ritardo = ritardi

    # ── 3. Livello di rischio ─────────────────────────────────────────────────
    n_fattori = len(fattori)
    n_ritardi = len(ritardi)

    # Fattori critici (peso ≥ 3) — qualsiasi numero > 0 porta almeno a "incerto"
    n_critici = sum(1 for f in fattori if any(
        kw in f for kw in (
            "forcipe", "APGAR basso", "Distress fetale", "Ipotonia", "Grande prematurità",
            "Moro", "oculare assente", "scarso o assente", "ALTO RISCHIO"
        )
    ))

    if punteggio == 0 and n_ritardi == 0:
        result.livello = LIVELLO_NORMALE
    elif punteggio <= 2 and n_critici == 0 and n_ritardi == 0:
        result.livello = LIVELLO_INCERTO
    elif punteggio <= 4 and n_critici == 0:
        result.livello = LIVELLO_INCERTO
    elif punteggio <= 6 and n_critici <= 1 and n_ritardi <= 1:
        result.livello = LIVELLO_A_RISCHIO
    else:
        result.livello = LIVELLO_ALTO_RISCHIO

    # Override se fattori critici multipli
    if n_critici >= 2:
        result.livello = LIVELLO_ALTO_RISCHIO
    elif n_critici == 1 and punteggio >= 5:
        result.livello = LIVELLO_ALTO_RISCHIO

    # ── 4. Urgenza e indicazioni ──────────────────────────────────────────────
    indicazioni = []

    if eta is not None:
        if eta <= 3:
            finestra = "🚨 Finestra terapeutica OTTIMALE (0-3 mesi): 95% di recupero con intervento precoce (Castagnini)."
            indicazioni.append(finestra)
        elif eta <= 8:
            finestra = "⚠️ Finestra terapeutica ancora utile (4-8 mesi): recupero possibile nel ~10% dei casi senza intervento precoce."
            indicazioni.append(finestra)
        else:
            finestra = "🔴 Intervento tardivo (>9 mesi): recupero limitato — priorità assoluta."
            indicazioni.append(finestra)

    if result.livello == LIVELLO_ALTO_RISCHIO:
        result.urgenza = "trattare subito"
        indicazioni += [
            "Inviare immediatamente a valutazione neuropsicomotoria specialistica (FSC/NPI).",
            "Avviare programma terapeutico FSC senza attendere altra conferma.",
            "Programmare rivalutazione entro 4 settimane.",
            "Coinvolgere i genitori nel programma domiciliare (gestione e manipolazione del bimbo).",
        ]
    elif result.livello == LIVELLO_A_RISCHIO:
        result.urgenza = "approfondire"
        indicazioni += [
            "Completare la valutazione neuropsicomotoria con protocollo N/I/P (Castagnini).",
            "Osservare postura in supino e prono per segni FSC.",
            "Programmare rivalutazione entro 6-8 settimane.",
            "Se al secondo controllo non normalizzato → avviare trattamento.",
        ]
    elif result.livello == LIVELLO_INCERTO:
        result.urgenza = "monitorare"
        indicazioni += [
            "Monitoraggio a 6 settimane con rivalutazione protocollo N/I/P.",
            "Educare i genitori alla gestione/manipolazione corretta del bimbo.",
            "Osservare in particolare: controllo posturale supino/prono, reflessologia primitiva.",
        ]
    else:
        result.urgenza = "follow-up ordinario"
        indicazioni += [
            "Sviluppo nella norma secondo i dati anamnestici.",
            "Rivalutazione di routine al 6° e 12° mese.",
        ]

    result.indicazioni = indicazioni

    # ── 5. Scenario testuale ──────────────────────────────────────────────────
    eta_str = f"{eta:.0f} mesi" if eta is not None else "età non disponibile"

    scenario_parts = []

    if result.livello == LIVELLO_ALTO_RISCHIO:
        scenario_parts.append(
            f"Il profilo anamnestico presenta {n_fattori} fattori di rischio "
            f"(punteggio complessivo: {punteggio}) con {n_critici} fattori critici. "
            f"Questo quadro è compatibile con un rischio ALTO di alterazione dello sviluppo "
            f"neuropsicomotorio secondo i criteri FSC (Castagnini). "
        )
        if eta is not None and eta <= 3:
            scenario_parts.append(
                "L'età attuale si trova nella finestra terapeutica ottimale (0-3 mesi): "
                "l'esperienza di Castagnini documenta un recupero nel 95% dei casi con trattamento FSC precoce. "
                "È indicato un intervento immediato."
            )
        elif eta is not None and eta <= 8:
            scenario_parts.append(
                "L'età (4-8 mesi) è ancora nella finestra utile, ma i margini di recupero "
                "si riducono significativamente. Intervento urgente e programma intensivo."
            )
        else:
            scenario_parts.append(
                "L'intervento è tardivo (>9 mesi): le statistiche FSC indicano recupero limitato. "
                "È comunque indicato il massimo impegno terapeutico possibile."
            )

    elif result.livello == LIVELLO_A_RISCHIO:
        scenario_parts.append(
            f"Il profilo anamnestico presenta {n_fattori} fattori di rischio "
            f"(punteggio: {punteggio}). "
            "Secondo il protocollo Castagnini, il bambino va classificato come 'INCERTO' "
            "e trattato come potenzialmente patologico fino a normalizzazione confermata. "
        )
        if n_ritardi > 0:
            scenario_parts.append(
                f"Sono presenti {n_ritardi} milestone in ritardo rispetto all'età cronologica. "
                "Questo rinforza l'indicazione a procedere con valutazione strutturata N/I/P."
            )

    elif result.livello == LIVELLO_INCERTO:
        scenario_parts.append(
            f"Il profilo mostra {n_fattori} fattori di rischio di lieve entità (punteggio: {punteggio}). "
            "In base al criterio FSC, il bambino è da considerarsi 'incerto' e richiede "
            "monitoraggio attivo con rivalutazione a 6 settimane. "
            "Il protocollo Castagnini suggerisce: 'quando incerto si fa prevenzione, "
            "trattando come se fosse patologico fino a che tutto non diventi normale'."
        )
    else:
        scenario_parts.append(
            "Il profilo anamnestico non evidenzia fattori di rischio significativi. "
            "Lo sviluppo riportato dai genitori appare nella norma per l'età. "
            f"Età attuale: {eta_str}. Indicato follow-up di routine."
        )

    if fattori:
        scenario_parts.append(
            "\n\nFattori di rischio rilevati:\n• " + "\n• ".join(fattori)
        )
    if ritardi:
        scenario_parts.append(
            "\n\nMilestone in ritardo:\n• " + "\n• ".join(ritardi)
        )

    result.scenario_testo = "".join(scenario_parts)

    # ── 6. Stima età funzionale approssimata ─────────────────────────────────
    # basata sui riflessi e tappe motorie riferite
    if eta is not None:
        if result.livello == LIVELLO_ALTO_RISCHIO:
            result.eta_funzionale_stimata = f"Possibile ritardo funzionale rispetto all'età cronologica ({eta_str})"
        elif result.livello == LIVELLO_A_RISCHIO:
            result.eta_funzionale_stimata = f"Età funzionale da verificare con protocollo N/I/P (età cronologica: {eta_str})"
        else:
            result.eta_funzionale_stimata = f"Coerente con l'età cronologica ({eta_str})"

    return result


# ── UI Streamlit ──────────────────────────────────────────────────────────────

def render_scenario_ui(
    pnev_json: Dict[str, Any],
    data_nascita: Optional[str] = None,
    eta_mesi_override: Optional[float] = None,
):
    """
    Renderizza lo scenario clinico direttamente in Streamlit.
    Chiamare dalla sezione Valutazione PNEV dopo aver caricato i dati.
    """
    import streamlit as st

    result = calcola_scenario(pnev_json, data_nascita, eta_mesi_override)

    emoji = EMOJI.get(result.livello, "")
    st.markdown(f"## {emoji} Scenario clinico: **{result.livello}**")
    st.caption(f"Punteggio fattori di rischio: {result.punteggio} | Urgenza: {result.urgenza.upper()}")

    # Semaforo visivo
    col_semaph = {
        LIVELLO_NORMALE:      ("green", "🟢"),
        LIVELLO_INCERTO:      ("orange", "🟡"),
        LIVELLO_A_RISCHIO:    ("red", "🔴"),
        LIVELLO_ALTO_RISCHIO: ("darkred", "🚨"),
    }
    colore, em = col_semaph.get(result.livello, ("gray", "⚪"))
    st.markdown(
        f"<div style='background:{colore};color:white;padding:14px 20px;"
        f"border-radius:10px;font-size:1.2rem;font-weight:700;margin:8px 0'>"
        f"{em} {result.livello} — {result.urgenza.upper()}</div>",
        unsafe_allow_html=True,
    )

    # Scenario testuale
    with st.expander("📋 Descrizione scenario", expanded=True):
        for line in result.scenario_testo.split("\n"):
            if line.startswith("•"):
                st.markdown(line)
            elif line.strip():
                st.write(line)

    # Metriche
    c1, c2, c3 = st.columns(3)
    c1.metric("Fattori di rischio", len(result.fattori_rischio))
    c2.metric("Milestone in ritardo", len(result.milestone_ritardo))
    c3.metric("Punteggio rischio", result.punteggio)

    # Fattori di rischio
    if result.fattori_rischio:
        with st.expander(f"⚠️ Fattori di rischio rilevati ({len(result.fattori_rischio)})", expanded=True):
            for f in result.fattori_rischio:
                st.markdown(f"- {f}")

    # Milestone in ritardo
    if result.milestone_ritardo:
        with st.expander(f"⏳ Milestone in ritardo ({len(result.milestone_ritardo)})", expanded=True):
            for m in result.milestone_ritardo:
                st.markdown(f"- {m}")

    # Indicazioni operative
    if result.indicazioni:
        with st.expander("🎯 Indicazioni operative", expanded=True):
            for ind in result.indicazioni:
                if ind.startswith("🚨") or ind.startswith("⚠️") or ind.startswith("🔴"):
                    st.info(ind)
                else:
                    st.markdown(f"- {ind}")

    # Finestra temporale Castagnini
    if result.urgenza in ("trattare subito", "approfondire"):
        st.error(
            "**Statistiche FSC — Castagnini:**\n\n"
            "- Intervento 0-3 mesi → 95% di bambini non necessitano più di terapia\n"
            "- Intervento 4-8 mesi → solo 10% raggiunge piena autonomia\n"
            "- Intervento >9 mesi → recupero raramente raggiunto"
        )

    if result.eta_funzionale_stimata:
        st.caption(f"Stima età funzionale: {result.eta_funzionale_stimata}")
