"""
pei_core.model — documento PEI/PDF/DF/PF indipendente dal database.

Il contenuto è un dict {chiave_campo: valore}, salvato in JSONB.
Le due app (gestionale e TFA Manager) aggiungono solo i propri riferimenti
(paziente_id oppure corsista_id) a livello di tabella.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from zoneinfo import ZoneInfo

from .schema import (SCHEMA_VERSION, ASSI_PDF, ASSI_PER_DIMENSIONE, TIPI_DOCUMENTO,
                     SEZIONI_PEI_PROVVISORIO, campi_flat, schema_per)

TZ = ZoneInfo("Europe/Rome")


@dataclass
class Documento:
    tipo: str                       # PEI | PDF | DF | PF
    contenuto: dict = field(default_factory=dict)
    anno_scolastico: str = ""
    grado: str = "secondaria_II"
    anonimo: bool = False
    stato: str = "bozza"            # bozza | definitivo
    schema_version: str = SCHEMA_VERSION
    id: int | None = None
    aggiornato_il: datetime | None = None

    def __post_init__(self):
        if self.tipo not in TIPI_DOCUMENTO:
            raise ValueError(f"Tipo non valido: {self.tipo}")

    @property
    def titolo(self) -> str:
        return TIPI_DOCUMENTO[self.tipo]

    def to_row(self) -> dict:
        return {
            "tipo": self.tipo,
            "anno_scolastico": self.anno_scolastico,
            "grado": self.grado,
            "anonimo": self.anonimo,
            "stato": self.stato,
            "schema_version": self.schema_version,
            "contenuto": self.contenuto,
        }

    @classmethod
    def from_row(cls, row: dict) -> "Documento":
        return cls(
            id=row.get("id"),
            tipo=row["tipo"],
            contenuto=row.get("contenuto") or {},
            anno_scolastico=row.get("anno_scolastico") or "",
            grado=row.get("grado") or "secondaria_II",
            anonimo=bool(row.get("anonimo")),
            stato=row.get("stato") or "bozza",
            schema_version=row.get("schema_version") or SCHEMA_VERSION,
            aggiornato_il=row.get("aggiornato_il"),
        )

    @property
    def provvisorio(self) -> bool:
        return self.tipo == "PEI" and str(self.contenuto.get("tipo_pei", "")).startswith("provvisorio")

    def sezioni(self) -> list[dict]:
        """Sezioni da mostrare: nel PEI provvisorio solo quelle dell'art. 16 c.3."""
        tutte = schema_per(self.tipo)
        if self.provvisorio:
            return [s for s in tutte if s["id"] in SEZIONI_PEI_PROVVISORIO]
        return tutte

    def completamento(self) -> float:
        """Percentuale di campi compilati (0-100), sulle sezioni visibili."""
        campi = [c for sez in self.sezioni() for c in sez["campi"]]
        pieni = sum(1 for c in campi if self.contenuto.get(c["key"]) not in (None, "", [], False))
        return round(100 * pieni / len(campi), 1) if campi else 0.0


# --------------------------------------------------------------------------
# Precompilazione: sezione 2 del PEI a partire da PF oppure DF + PDF
# --------------------------------------------------------------------------
def precompila_sezione2(pei: Documento, sorgente: Documento) -> Documento:
    if pei.tipo != "PEI":
        raise ValueError("La precompilazione vale solo per un PEI")
    c = pei.contenuto
    if sorgente.tipo == "PF":
        c["pf_disponibile"] = True
        testo = sorgente.contenuto.get("sintesi", "")
    elif sorgente.tipo == "PDF":
        c["pf_disponibile"] = False
        c.setdefault("df_riferimento", sorgente.contenuto.get("df_riferimento", ""))
        righe = []
        for k, etichetta in ASSI_PDF:
            att = sorgente.contenuto.get(f"{k}_attuale", "").strip()
            if att:
                righe.append(f"{etichetta}: {att}")
        sintesi = sorgente.contenuto.get("sintesi", "").strip()
        testo = "\n".join(([sintesi, ""] if sintesi else []) + righe)
    elif sorgente.tipo == "DF":
        c["pf_disponibile"] = False
        c.setdefault("df_riferimento", sorgente.contenuto.get("data_redazione", ""))
        testo = sorgente.contenuto.get("sintesi", "")
    else:
        raise ValueError("Sorgente non valida")
    if not c.get("sintesi_profilo"):
        c["sintesi_profilo"] = testo
    # Sezione 4: bozza delle osservazioni per dimensione dagli assi del PDF
    if sorgente.tipo == "PDF":
        nomi = dict(ASSI_PDF)
        for dim, assi in ASSI_PER_DIMENSIONE.items():
            if c.get(f"oss_{dim}"):
                continue
            pezzi = [f"[{nomi[a]}] {sorgente.contenuto[f'{a}_attuale'].strip()}"
                     for a in assi if str(sorgente.contenuto.get(f"{a}_attuale", "")).strip()]
            if pezzi:
                c[f"oss_{dim}"] = "BOZZA DAL PDF — da rivedere con l'osservazione in classe\n" + "\n".join(pezzi)
    for k in ("soggetto", "anno_scolastico"):
        if not c.get(k) and sorgente.contenuto.get(k):
            c[k] = sorgente.contenuto[k]
    return pei


# --------------------------------------------------------------------------
# Controllo anonimato (TFA Manager: obbligatorio)
# --------------------------------------------------------------------------
RE_CF = re.compile(r"\b[A-Z]{6}\d{2}[A-EHLMPR-T]\d{2}[A-Z]\d{3}[A-Z]\b", re.I)
RE_DATA = re.compile(r"\b\d{1,2}[/.-]\d{1,2}[/.-](19|20)\d{2}\b")
RE_TEL = re.compile(r"\b3\d{2}[\s.]?\d{3}[\s.]?\d{3,4}\b")
RE_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]+\b")
RE_NOME_PROPRIO = re.compile(r"\b[A-Z][a-zàèéìòù]+ [A-Z][a-zàèéìòù]+\b")

# campi in cui le date sono legittime
CAMPI_DATA_OK = {"data_redazione", "data_approvazione", "accertamento",
                 "df_riferimento", "anno_scolastico"}


def controlla_anonimato(doc: Documento) -> list[str]:
    """Restituisce avvisi (non blocca): CF, telefoni, email, date, possibili nomi."""
    avvisi = []
    sogg = str(doc.contenuto.get("soggetto", ""))
    if RE_NOME_PROPRIO.search(sogg):
        avvisi.append("«Studente»: sembra un nome e cognome — usa iniziali o codice.")
    voci = []
    for k, v in doc.contenuto.items():
        if isinstance(v, list):
            for i, riga in enumerate(v):
                if isinstance(riga, dict):
                    voci += [(f"{k}[{i + 1}].{kk}", vv) for kk, vv in riga.items()]
        else:
            voci.append((k, v))
    for k, v in voci:
        if k.startswith("glo[") and k.endswith(".nome") and isinstance(v, str) and RE_NOME_PROPRIO.search(v):
            avvisi.append(f"{k}: nome reale di un componente del GLO — indica solo il ruolo.")
        if not isinstance(v, str) or not v:
            continue
        if RE_CF.search(v):
            avvisi.append(f"{k}: contiene un codice fiscale.")
        if RE_TEL.search(v):
            avvisi.append(f"{k}: contiene un numero di telefono.")
        if RE_EMAIL.search(v):
            avvisi.append(f"{k}: contiene un indirizzo email.")
        if k not in CAMPI_DATA_OK and RE_DATA.search(v):
            avvisi.append(f"{k}: contiene una data (possibile data di nascita).")
    return avvisi


def controlla_percorso(doc: Documento) -> list[str]:
    """Coerenza fra progettazione disciplinare (8.3) e percorso complessivo (art. 10)."""
    if doc.tipo != "PEI":
        return []
    righe = doc.contenuto.get("progettazione_disciplinare") or []
    opz = [str(r.get("opzione", "")) for r in righe if isinstance(r, dict)]
    percorso = doc.contenuto.get("percorso", "")
    avvisi = []
    if any(o.startswith("C") for o in opz):
        if percorso != "differenziato":
            avvisi.append("Almeno una disciplina è C: il percorso complessivo risulta differenziato.")
        avvisi.append("Percorso differenziato: serve la proposta formale del consiglio di classe "
                      "ai genitori, che possono rifiutarla; si consegue l'attestato di credito formativo.")
    elif any(o.startswith("B") for o in opz) and percorso == "ordinario":
        avvisi.append("Ci sono discipline B: il percorso complessivo è personalizzato, non ordinario.")
    return avvisi


def adesso() -> datetime:
    return datetime.now(TZ)
