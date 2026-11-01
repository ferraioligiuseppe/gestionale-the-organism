"""
Motore di somiglianza fenotipica PNEV ↔ sindromi genetiche (HPO).

Strumento di ORIENTAMENTO all'invio al genetista: non ha valore diagnostico.

Metodo (livello 2 dell'Atlante PNEV):
  - ogni termine HPO ha un contenuto informativo IC = -ln(frazione di sindromi che lo contengono);
  - per ogni segno PRESENTE nel paziente si cerca, in ogni sindrome, l'antenato comune più
    informativo (somiglianza di Resnik), pesato per la frequenza del segno nella sindrome;
  - i segni ASSENTI (esclusi esplicitamente) penalizzano le sindromi in cui sono frequenti;
  - il punteggio è normalizzato (0-1) e confrontato con profili casuali della stessa
    dimensione per ottenere un valore p empirico.

Livello 3 (apprendimento): i casi dello Studio con diagnosi genetica confermata aggiornano le
frequenze dei segni con una media bayesiana:
    f_post = (f_letteratura * M + osservati) / (M + n_casi),  con M = PRIOR_WEIGHT.
"""
from __future__ import annotations

import gzip
import json
import math
import os
import random
from array import array
from functools import lru_cache

import numpy as np

DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "hpo_genetica.json.gz")
PRIOR_WEIGHT = 5.0      # "peso" della letteratura, in numero di casi equivalenti
UNKNOWN_FREQ = 0.5      # frequenza usata quando la letteratura non la riporta
ABSENT_WEIGHT = 0.5     # quanto pesa un segno assente ma frequente nella sindrome
W_PAZ = 0.7             # peso direzione paziente -> sindrome (quanto la sindrome spiega i segni del paziente)
W_SIN = 0.3             # peso direzione sindrome -> paziente (quanto il paziente ha i segni tipici della sindrome)


def _g(f: float) -> float:
    """Peso di frequenza: un segno raro nella sindrome conta comunque, uno costante conta pieno."""
    return 0.3 + 0.7 * f


class MotoreGenetica:
    def __init__(self, path: str = DATA_PATH):
        with gzip.open(path, "rt", encoding="utf-8") as fh:
            raw = json.load(fh)
        self.versione = raw["version"]
        T = raw["terms"]
        self.hpo = [t[0] for t in T]
        self.idx = {h: i for i, h in enumerate(self.hpo)}
        self.lab_it = [t[1] for t in T]
        self.lab_en = [t[2] for t in T]
        self.parents = [t[3] for t in T]
        self.ic = np.array([t[4] for t in T], dtype=np.float32)
        self.syn = [t[5] for t in T]
        D = raw["diseases"]
        self.N = len(D)
        self.dis_id = [d[0] for d in D]
        self.dis_name = [d[1] for d in D]
        self.dis_genes = [d[2] for d in D]
        self.dis_inh = [d[3] for d in D]
        self.dis_terms = [{t: (UNKNOWN_FREQ if f < 0 else f) for t, f in d[4]} for d in D]
        self.dis_index = {d: i for i, d in enumerate(self.dis_id)}
        # indice inverso: termine -> (sindromi, frequenza massima dei discendenti annotati)
        inv: dict[int, dict[int, float]] = {}
        for di, terms in enumerate(self.dis_terms):
            cl = self.closure(terms)
            for a, f in cl.items():
                inv.setdefault(a, {})[di] = f
        self.inv = {a: (np.array(list(m.keys()), dtype=np.int32), np.array(list(m.values()), dtype=np.float32))
                    for a, m in inv.items()}
        # termini per i profili casuali: estratti come compaiono nelle annotazioni (profili realistici)
        self.pool = [t for terms in self.dis_terms for t in terms if self.ic[t] > 0.5]
        self.overlay: dict[int, dict[int, float]] = {}        # sindromi aggiornate dai casi dello Studio
        self.overlay_n: dict[int, int] = {}

    # ---------------------------------------------------------------- ontologia
    @lru_cache(maxsize=None)
    def ancestors(self, i: int) -> frozenset:
        s = {i}
        for p in self.parents[i]:
            s |= self.ancestors(p)
        return frozenset(s)

    def closure(self, terms: dict[int, float]) -> dict[int, float]:
        cl: dict[int, float] = {}
        for t, f in terms.items():
            for a in self.ancestors(t):
                if cl.get(a, -1) < f:
                    cl[a] = f
        return cl

    def label(self, hpo_id: str) -> str:
        i = self.idx.get(hpo_id)
        if i is None:
            return hpo_id
        t = self.lab_it[i] or self.lab_en[i]
        return t[:1].upper() + t[1:]

    def cerca(self, testo: str, limite: int = 30) -> list[tuple[str, str]]:
        """Ricerca termini per etichetta italiana/inglese, sinonimi o codice."""
        q = testo.strip().lower()
        if not q:
            return []
        out = []
        for i, h in enumerate(self.hpo):
            hay = (self.lab_it[i] + " | " + self.lab_en[i] + " | " + " | ".join(self.syn[i])).lower()
            if q in hay or q == h.lower():
                score = (0 if (self.lab_it[i].lower().startswith(q) or self.lab_en[i].lower().startswith(q)) else 1, len(hay))
                out.append((score, h))
        out.sort()
        return [(h, f"{self.label(h)}  ·  {h}" + (f"  ({self.lab_en[self.idx[h]]})" if self.lab_it[self.idx[h]] else ""))
                for _, h in out[:limite]]

    # ------------------------------------------------------------ apprendimento
    def carica_casi_confermati(self, casi: list[dict]) -> None:
        """
        casi: [{'disease_id': 'OMIM:194050', 'presenti': [...HP...], 'assenti': [...HP...]}, ...]
        Aggiorna le frequenze delle sindromi con i casi dello Studio (media bayesiana).
        """
        per_dis: dict[int, list[tuple[set, set]]] = {}
        for c in casi:
            di = self.dis_index.get(c.get("disease_id"))
            if di is None:
                continue
            pres = {self.idx[h] for h in c.get("presenti", []) if h in self.idx}
            ass = {self.idx[h] for h in c.get("assenti", []) if h in self.idx}
            per_dis.setdefault(di, []).append((pres, ass))
        self.overlay, self.overlay_n = {}, {}
        for di, lst in per_dis.items():
            n = len(lst)
            lit = self.closure(self.dis_terms[di])
            obs: dict[int, int] = {}
            for pres, _ in lst:
                cl = set()
                for t in pres:
                    cl |= self.ancestors(t)
                for a in cl:
                    obs[a] = obs.get(a, 0) + 1
            post = {}
            for a in set(lit) | set(obs):
                post[a] = (lit.get(a, 0.0) * PRIOR_WEIGHT + obs.get(a, 0)) / (PRIOR_WEIGHT + n)
            self.overlay[di] = post
            self.overlay_n[di] = n

    # --------------------------------------------------------------- punteggio
    def _score_all(self, pres: list[int], ass: list[int]) -> np.ndarray:
        tot_ic = float(sum(self.ic[p] for p in pres)) or 1.0
        score = np.zeros(self.N, dtype=np.float32)
        for p in pres:
            best = np.zeros(self.N, dtype=np.float32)
            for a in self.ancestors(p):
                ica = self.ic[a]
                if ica <= 0 or a not in self.inv:
                    continue
                ds, fs = self.inv[a]
                np.maximum.at(best, ds, ica * (0.3 + 0.7 * fs))
            score += best
        score /= tot_ic
        pclos = set()
        for p in pres:
            pclos |= self.ancestors(p)
        memo: dict[int, float] = {}
        def v(t):
            if t not in memo:
                memo[t] = max((float(self.ic[a]) for a in self.ancestors(t) if a in pclos), default=0.0)
            return memo[t]
        rev = np.zeros(self.N, dtype=np.float32)
        for di, terms in enumerate(self.dis_terms):
            num = den = 0.0
            for t, f in terms.items():
                num += f * v(t); den += f * float(self.ic[t])
            rev[di] = num / den if den else 0.0
        score = W_PAZ * score + W_SIN * rev
        for q in ass:
            if q in self.inv:
                ds, fs = self.inv[q]
                np.subtract.at(score, ds, ABSENT_WEIGHT * fs * self.ic[q] / tot_ic)
        for di, cl in self.overlay.items():          # sindromi aggiornate dai casi dello Studio
            score[di] = self._score_one(pres, ass, cl, tot_ic, self._post_terms(di))
        return score

    def _post_terms(self, di: int) -> dict[int, float]:
        """Termini diretti della sindrome con le frequenze aggiornate (per la direzione sindrome->paziente)."""
        cl = self.overlay.get(di)
        if cl is None:
            return self.dis_terms[di]
        return {t: cl.get(t, f) for t, f in self.dis_terms[di].items()}

    def _score_one(self, pres, ass, cl: dict[int, float], tot_ic: float | None = None,
                   dterms: dict[int, float] | None = None) -> float:
        tot_ic = tot_ic or (float(sum(self.ic[p] for p in pres)) or 1.0)
        s = 0.0
        for p in pres:
            b = 0.0
            for a in self.ancestors(p):
                f = cl.get(a)
                if f is not None and self.ic[a] > 0:
                    b = max(b, float(self.ic[a]) * _g(f))
            s += b
        s /= tot_ic
        if dterms:
            pclos = set()
            for p in pres:
                pclos |= self.ancestors(p)
            num = den = 0.0
            for t, f in dterms.items():
                num += f * max((float(self.ic[a]) for a in self.ancestors(t) if a in pclos), default=0.0)
                den += f * float(self.ic[t])
            s = W_PAZ * s + W_SIN * (num / den if den else 0.0)
        for q in ass:
            f = cl.get(q)
            if f:
                s -= ABSENT_WEIGHT * f * float(self.ic[q]) / tot_ic
        return s

    def analizza(self, presenti: list[str], assenti: list[str] | None = None, top: int = 25,
                 n_random: int = 300, seed: int = 7) -> list[dict]:
        """Restituisce la classifica delle sindromi più simili al profilo del paziente."""
        pres = [self.idx[h] for h in presenti if h in self.idx]
        ass = [self.idx[h] for h in (assenti or []) if h in self.idx]
        if not pres:
            return []
        sc = self._score_all(pres, ass)
        order = np.argsort(-sc)[:top]
        rng = random.Random(seed)
        k = len(pres)
        randoms = [list({rng.choice(self.pool) for _ in range(k)}) for _ in range(n_random)]
        out = []
        for rank, di in enumerate(order, 1):
            di = int(di)
            cl = self.overlay.get(di) or self.closure(self.dis_terms[di])
            s = float(sc[di])
            dt = self._post_terms(di)
            null = [self._score_one(r, [], cl, None, dt) for r in randoms]
            p = (1 + sum(1 for x in null if x >= s)) / (n_random + 1)
            # segni del paziente che trovano corrispondenza diretta o tramite un termine più specifico
            match = [h for h in presenti if h in self.idx and self.idx[h] in cl]
            out.append({
                "rank": rank, "disease_id": self.dis_id[di], "nome": self.dis_name[di],
                "geni": self.dis_genes[di], "eredita": self.dis_inh[di],
                "somiglianza": round(max(s, 0.0), 3), "p_value": round(p, 4),
                "segni_corrispondenti": match, "casi_studio": self.overlay_n.get(di, 0),
            })
        return out


    def informativita(self, presenti: list[str]) -> tuple[float, str]:
        """Quanto il profilo è specifico: somma dell'IC dei segni presenti (segni rari = profilo informativo)."""
        tot = float(sum(self.ic[self.idx[h]] for h in presenti if h in self.idx))
        if tot < 8:
            return tot, "bassa: segni comuni a molte sindromi, la classifica orienta poco"
        if tot < 16:
            return tot, "media: la classifica va letta con prudenza"
        return tot, "alta: profilo con segni rari, la classifica è più indicativa"


_MOTORE: MotoreGenetica | None = None


def get_motore() -> MotoreGenetica:
    """Istanza unica (in Streamlit avvolgere con st.cache_resource)."""
    global _MOTORE
    if _MOTORE is None:
        _MOTORE = MotoreGenetica()
    return _MOTORE
