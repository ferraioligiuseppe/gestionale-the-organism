"""
Genosociogramma — impaginazione, disegno SVG e ripetizioni.

Lavora sul dict restituito da db_genosociogramma.carica_genogramma:
  persone: id, nome, sesso (M/F/?), nascita, morte, causa, padre, madre, indice, note
  unioni:  id, a, b, tipo, anno
  legami:  id, a, b, tipo
Nessuna dipendenza da Streamlit: usato sia dalla UI sia dal PDF.
"""
import math
import re
from datetime import date
from html import escape

H = 20            # mezza dimensione di una figura
SP = 118          # distanza orizzontale tra figure
GEN_H = 170       # distanza verticale tra generazioni

TIPI_LEGAME_LABEL = {"stretto": "stretto", "fusione": "fusionale", "conflitto": "conflitto",
                     "rottura": "rottura", "uni": "unidirezionale"}

INK, MUTED, GEN, PAPER = "#1C2B33", "#56666E", "#6E5498", "#FFFFFF"


# ---------------------------------------------------------------- date
def parse_data(s):
    """'1952' | '12/03/1952' | '1952-03-12' -> dict(y, m, d) oppure None."""
    if not s:
        return None
    s = str(s).strip()
    m = re.fullmatch(r"(\d{4})", s)
    if m:
        return {"y": int(m[1]), "m": None, "d": None}
    m = re.fullmatch(r"(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{4})", s)
    if m:
        return {"y": int(m[3]), "m": int(m[2]), "d": int(m[1])}
    m = re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})", s)
    if m:
        return {"y": int(m[1]), "m": int(m[2]), "d": int(m[3])}
    m = re.search(r"(\d{4})", s)
    return {"y": int(m[1]), "m": None, "d": None} if m else None


def eta(b, e):
    if not b or not e:
        return None
    a = e["y"] - b["y"]
    if b["m"] and e["m"] and (e["m"] < b["m"] or (e["m"] == b["m"] and (e["d"] or 0) < (b["d"] or 0))):
        a -= 1
    return a


def oggi():
    t = date.today()
    return {"y": t.year, "m": t.month, "d": t.day}


def anni_label(p):
    b, d = parse_data(p.get("nascita")), parse_data(p.get("morte"))
    s = str(b["y"]) if b else "?"
    if p.get("morte"):
        s += "–" + (str(d["y"]) if d else "?")
    return s


def eta_figura(p):
    b = parse_data(p.get("nascita"))
    if not b:
        return None
    if p.get("morte"):
        return eta(b, parse_data(p.get("morte")))
    return eta(b, oggi())


# ---------------------------------------------------------------- impaginazione
def coppie(g):
    """Unioni registrate + coppie di genitori senza unione registrata."""
    ids = {p["id"] for p in g["persone"]}
    seen, out = set(), []
    for u in g["unioni"]:
        if u["a"] in ids and u["b"] in ids and u["a"] != u["b"]:
            k = tuple(sorted((u["a"], u["b"])))
            if k not in seen:
                seen.add(k)
                out.append({"a": u["a"], "b": u["b"], "u": u})
    for p in g["persone"]:
        if p.get("padre") in ids and p.get("madre") in ids:
            k = tuple(sorted((p["padre"], p["madre"])))
            if k not in seen:
                seen.add(k)
                out.append({"a": p["padre"], "b": p["madre"], "u": None})
    return out


def impagina(g):
    """Restituisce (pos, coppie, max_gen); pos[id] = dict(x, y, gen)."""
    P = g["persone"]
    by = {p["id"]: p for p in P}

    def genitori(p):
        return [x for x in (p.get("padre"), p.get("madre")) if x and x in by and x != p["id"]]

    G, vis = {}, set()

    def gen(pid):
        if pid in G:
            return G[pid]
        if pid in vis:
            return 0
        vis.add(pid)
        ps = genitori(by[pid])
        G[pid] = 1 + max(gen(x) for x in ps) if ps else 0
        return G[pid]

    for p in P:
        gen(p["id"])
    cp = coppie(g)
    partner = {}
    for c in cp:
        partner.setdefault(c["a"], []).append(c["b"])
        partner.setdefault(c["b"], []).append(c["a"])
    for _ in range(4):  # chi non ha genitori sale alla generazione del partner
        for p in P:
            if not genitori(p):
                for q in partner.get(p["id"], []):
                    G[p["id"]] = max(G[p["id"]], G[q])

    gens = {}
    for p in P:
        gens.setdefault(G[p["id"]], []).append(p)
    ordine = {p["id"]: i for i, p in enumerate(P)}
    X = {}

    def anno_nascita(p):
        b = parse_data(p.get("nascita"))
        return b["y"] if b else 9999

    for gg in sorted(gens):
        lista = gens[gg]

        def key(p):
            ps = [X[x] for x in genitori(p) if x in X]
            return sum(ps) / len(ps) if ps else None

        con_k = sorted([p for p in lista if key(p) is not None], key=lambda p: (key(p), anno_nascita(p)))
        senza_k = sorted([p for p in lista if key(p) is None], key=lambda p: ordine[p["id"]])
        placed, blocchi = set(), []

        def push(p, k):
            if p["id"] in placed:
                return
            if not blocchi or blocchi[-1]["k"] != k or k is None:
                blocchi.append({"k": k, "items": []})
            bl = blocchi[-1]
            bl["items"].append(p)
            placed.add(p["id"])
            primo = len(bl["items"]) == 1 and k is not None
            for q in partner.get(p["id"], []):
                qq = by.get(q)
                if qq and G[q] == gg and q not in placed and not genitori(qq):
                    if primo:
                        bl["items"].insert(0, qq)
                    else:
                        bl["items"].append(qq)
                    placed.add(q)

        for p in con_k:
            push(p, key(p))
        for p in senza_k:
            push(p, None)
        prev = None
        for bl in blocchi:
            w = (len(bl["items"]) - 1) * SP
            if bl["k"] is not None:
                start = bl["k"] - w / 2
            else:
                start = 0 if prev is None else prev + SP
            if prev is not None:
                start = max(start, prev + SP)
            for i, p in enumerate(bl["items"]):
                X[p["id"]] = start + i * SP
            prev = start + w

    min_x = min(X.values()) if X else 0
    pos = {p["id"]: {"x": X[p["id"]] - min_x + 80, "y": G[p["id"]] * GEN_H + 50, "gen": G[p["id"]]} for p in P}
    return pos, cp, max(G.values()) if G else 0


def geometria(g):
    """Calcola tutti gli elementi da disegnare, in coordinate SVG (y verso il basso).
    Usata sia dall'SVG sia dal PDF, così i due disegni coincidono."""
    pos, cp, max_g = impagina(g)
    el = {"segmenti": [], "tratteggi": [], "testi": [], "figure": [], "legami": [], "pos": pos}
    if not pos:
        el["w"], el["h"] = 400, 200
        return el
    mid = {}
    for c in cp:
        p, q = pos.get(c["a"]), pos.get(c["b"])
        if not p or not q:
            continue
        k = tuple(sorted((c["a"], c["b"])))
        tipo = c["u"]["tipo"] if c["u"] else "matrimonio"
        dest = el["tratteggi"] if tipo == "convivenza" else el["segmenti"]
        if p["y"] == q["y"]:
            yl = p["y"] + H + 56
            l, r = min(p["x"], q["x"]), max(p["x"], q["x"])
            mx = (l + r) / 2
            dest += [((p["x"], p["y"] + H), (p["x"], yl)), ((q["x"], q["y"] + H), (q["x"], yl)), ((l, yl), (r, yl))]
            if tipo in ("separazione", "divorzio"):
                el["segmenti"].append(((mx - 4, yl + 8), (mx + 4, yl - 8)))
                if tipo == "divorzio":
                    el["segmenti"].append(((mx + 4, yl + 8), (mx + 12, yl - 8)))
            if c["u"] and c["u"].get("anno"):
                el["testi"].append((mx, yl - 5, c["u"]["anno"], 10, MUTED, False))
            mid[k] = (mx, yl)
        else:
            dest.append(((p["x"], p["y"]), (q["x"], q["y"])))
            mid[k] = ((p["x"] + q["x"]) / 2, (p["y"] + q["y"]) / 2)

    figli = {}
    for c in g["persone"]:
        ps = [x for x in (c.get("padre"), c.get("madre")) if x and x in pos and x != c["id"]]
        if ps:
            figli.setdefault(tuple(sorted(ps)), []).append(c)
    for k, cs in figli.items():
        o = mid[k] if len(k) == 2 and k in mid else (pos[k[0]]["x"], pos[k[0]]["y"] + H)
        tops = [(pos[c["id"]]["x"], pos[c["id"]]["y"] - H) for c in cs]
        bar = min(t[1] for t in tops) - 28
        if o[1] < bar:
            l, r = min([o[0]] + [t[0] for t in tops]), max([o[0]] + [t[0] for t in tops])
            el["segmenti"] += [((o[0], o[1]), (o[0], bar)), ((l, bar), (r, bar))]
            el["segmenti"] += [((t[0], bar), (t[0], t[1])) for t in tops]
        else:
            el["segmenti"] += [((o[0], o[1]), t) for t in tops]

    for l in g["legami"]:
        p, q = pos.get(l["a"]), pos.get(l["b"])
        if not p or not q or l["a"] == l["b"]:
            continue
        dx, dy = q["x"] - p["x"], q["y"] - p["y"]
        L = math.hypot(dx, dy) or 1
        a = (p["x"] + dx / L * (H + 6), p["y"] + dy / L * (H + 6))
        b = (q["x"] - dx / L * (H + 6), q["y"] - dy / L * (H + 6))
        el["legami"].append({"a": a, "b": b, "tipo": l["tipo"], "bend": -min(60, L * 0.25)})

    for p in g["persone"]:
        o = pos[p["id"]]
        el["figure"].append({"x": o["x"], "y": o["y"], "sesso": p.get("sesso", "M"),
                             "morto": bool(p.get("morte")), "indice": bool(p.get("indice")),
                             "eta": eta_figura(p)})
        el["testi"].append((o["x"], o["y"] + H + 16, (p.get("nome") or "senza nome")[:18], 12, INK, True))
        el["testi"].append((o["x"], o["y"] + H + 30, anni_label(p), 10.5, MUTED, False))
        if p.get("causa"):
            el["testi"].append((o["x"], o["y"] + H + 43, p["causa"][:22], 10, MUTED, False))

    el["w"] = max(o["x"] for o in pos.values()) + 110
    el["h"] = (max_g + 1) * GEN_H + 70
    return el


def curva_punti(a, b, off, bend, n=24):
    """Punti di una curva quadratica tra a e b, spostata di 'off' lungo la normale."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    L = math.hypot(dx, dy) or 1
    nx, ny = -dy / L, dx / L
    A = (a[0] + nx * off, a[1] + ny * off)
    B = (b[0] + nx * off, b[1] + ny * off)
    C = ((a[0] + b[0]) / 2 + nx * (bend + off), (a[1] + b[1]) / 2 + ny * (bend + off))
    pts = []
    for i in range(n + 1):
        t = i / n
        pts.append(((1 - t) ** 2 * A[0] + 2 * (1 - t) * t * C[0] + t * t * B[0],
                    (1 - t) ** 2 * A[1] + 2 * (1 - t) * t * C[1] + t * t * B[1]))
    return pts, (nx, ny)


def tracciati_legame(lg):
    """Restituisce (polilinee, freccia) per un legame: ogni polilinea è una lista di punti."""
    a, b, bend, tipo = lg["a"], lg["b"], lg["bend"], lg["tipo"]
    if tipo == "fusione":
        return [curva_punti(a, b, o, bend)[0] for o in (-4, 0, 4)], False
    if tipo == "stretto":
        return [curva_punti(a, b, o, bend)[0] for o in (-2.5, 2.5)], False
    if tipo == "conflitto":
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        n = max(8, round(L / 12))
        pts, (nx, ny) = curva_punti(a, b, 0, bend, n)
        zz = []
        for i, (x, y) in enumerate(pts):
            s = 0 if i in (0, n) else (6 if i % 2 else -6)
            zz.append((x + nx * s, y + ny * s))
        return [zz], False
    if tipo == "rottura":
        pts, (nx, ny) = curva_punti(a, b, 0, bend, 40)
        out = [pts]
        for i in (18, 22):
            x, y = pts[i]
            out.append([(x - nx * 8, y - ny * 8), (x + nx * 8, y + ny * 8)])
        return out, False
    return [curva_punti(a, b, 0, bend)[0]], True


# ---------------------------------------------------------------- SVG
def svg_genogramma(g):
    el = geometria(g)
    if not el["pos"]:
        return ""
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {el["w"]:.0f} {el["h"]:.0f}" '
         f'width="{el["w"]:.0f}" height="{el["h"]:.0f}" font-family="Helvetica, Arial, sans-serif">',
         f'<rect width="100%" height="100%" fill="{PAPER}"/>',
         f'<defs><marker id="ag" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
         f'orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{GEN}"/></marker></defs>']
    for (x1, y1), (x2, y2) in el["segmenti"]:
        s.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{INK}" stroke-width="1.6"/>')
    for (x1, y1), (x2, y2) in el["tratteggi"]:
        s.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{INK}" '
                 f'stroke-width="1.6" stroke-dasharray="6 4"/>')
    for lg in el["legami"]:
        linee, freccia = tracciati_legame(lg)
        for i, pts in enumerate(linee):
            d = " ".join(f'{"M" if j == 0 else "L"}{x:.1f},{y:.1f}' for j, (x, y) in enumerate(pts))
            mk = ' marker-end="url(#ag)"' if freccia and i == 0 else ""
            s.append(f'<path d="{d}" fill="none" stroke="{GEN}" stroke-width="1.6"{mk}/>')
    for f in el["figure"]:
        x, y = f["x"], f["y"]
        if f["sesso"] == "F":
            s.append(f'<circle cx="{x}" cy="{y}" r="{H}" fill="{PAPER}" stroke="{INK}" stroke-width="1.8"/>')
            if f["indice"]:
                s.append(f'<circle cx="{x}" cy="{y}" r="{H - 5}" fill="none" stroke="{INK}" stroke-width="1.4"/>')
        elif f["sesso"] == "M":
            s.append(f'<rect x="{x - H}" y="{y - H}" width="{2 * H}" height="{2 * H}" fill="{PAPER}" '
                     f'stroke="{INK}" stroke-width="1.8"/>')
            if f["indice"]:
                s.append(f'<rect x="{x - H + 5}" y="{y - H + 5}" width="{2 * H - 10}" height="{2 * H - 10}" '
                         f'fill="none" stroke="{INK}" stroke-width="1.4"/>')
        else:
            s.append(f'<polygon points="{x},{y - H} {x + H},{y} {x},{y + H} {x - H},{y}" fill="{PAPER}" '
                     f'stroke="{INK}" stroke-width="1.8"/>')
        if f["morto"]:
            s.append(f'<path d="M{x - H + 3},{y - H + 3} L{x + H - 3},{y + H - 3} M{x + H - 3},{y - H + 3} '
                     f'L{x - H + 3},{y + H - 3}" stroke="{INK}" stroke-width="1.6"/>')
        if f["eta"] is not None:
            s.append(f'<text x="{x}" y="{y + 4}" text-anchor="middle" font-size="12" font-weight="bold" '
                     f'fill="{INK}" stroke="{PAPER}" stroke-width="3" paint-order="stroke">{f["eta"]}</text>')
    for x, y, t, size, col, bold in el["testi"]:
        fw = ' font-weight="bold"' if bold else ""
        s.append(f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="middle" font-size="{size}" fill="{col}"{fw} '
                 f'stroke="{PAPER}" stroke-width="3" paint-order="stroke">'
                 f'{escape(str(t))}</text>')
    s.append("</svg>")
    return "\n".join(s)


# ---------------------------------------------------------------- ripetizioni
def ripetizioni(g):
    """Spunti per il colloquio: stessa età del paziente, età alla morte, giorni, nomi."""
    P = g["persone"]
    by = {p["id"]: p for p in P}

    def lbl(p):
        b = parse_data(p.get("nascita"))
        return f'{p.get("nome") or "senza nome"}{f" ({b["y"]})" if b else ""}'

    out = {"indice_nome": None, "indice_eta": None, "indice": [], "eta": [], "date": [], "nomi": []}
    nomi = {}
    for p in P:
        k = (p.get("nome") or "").strip().split(" ")[0].lower()
        if k:
            nomi.setdefault(k, []).append(p)
    for gr in nomi.values():
        if len(gr) > 1:
            out["nomi"].append(f'«{gr[0]["nome"].split(" ")[0]}» ritorna {len(gr)} volte: '
                               + ", ".join(lbl(p) for p in gr))
    ea = {}
    for p in P:
        if p.get("morte"):
            a = eta(parse_data(p.get("nascita")), parse_data(p.get("morte")))
            if a is not None:
                ea.setdefault(a, []).append(p)
    for a in sorted(ea):
        if len(ea[a]) > 1:
            out["eta"].append(f"Morte a {a} anni: " + ", ".join(lbl(p) for p in ea[a]))
    ev = {}
    for p in P:
        for campo, verbo in (("nascita", "nascita"), ("morte", "morte")):
            d = parse_data(p.get(campo))
            if d and d["d"]:
                ev.setdefault((d["d"], d["m"]), []).append(f'{verbo} di {p.get("nome")} ({d["y"]})')
    for u in g["unioni"]:
        d = parse_data(u.get("anno"))
        if d and d["d"] and u["a"] in by and u["b"] in by:
            ev.setdefault((d["d"], d["m"]), []).append(
                f'{u["tipo"]} di {by[u["a"]]["nome"]} e {by[u["b"]]["nome"]} ({d["y"]})')
    for (dd, mm), lista in sorted(ev.items(), key=lambda kv: (kv[0][1], kv[0][0])):
        if len(lista) > 1:
            out["date"].append(f"{dd:02d}/{mm:02d}: " + "; ".join(lista))

    ix = next((p for p in P if p.get("indice")), None)
    if ix and parse_data(ix.get("nascita")):
        A = eta_figura(ix)
        out["indice_nome"], out["indice_eta"] = ix.get("nome"), A
        for p in P:
            pb = parse_data(p.get("nascita"))
            if p["id"] == ix["id"] or not pb:
                continue
            dd = parse_data(p.get("morte"))
            if dd and eta(pb, dd) == A:
                out["indice"].append(f'{lbl(p)} è morto/a a {A} anni' + (f' ({p["causa"]})' if p.get("causa") else ""))
            for u in g["unioni"]:
                if p["id"] not in (u["a"], u["b"]):
                    continue
                ud = parse_data(u.get("anno"))
                if ud and ud["y"] - pb["y"] == A:
                    altro = by.get(u["b"] if u["a"] == p["id"] else u["a"])
                    out["indice"].append(f'{lbl(p)}: {u["tipo"]}' + (f' con {altro["nome"]}' if altro else "")
                                         + f' a {A} anni ({ud["y"]})')
            for c in P:
                if p["id"] in (c.get("padre"), c.get("madre")):
                    cb = parse_data(c.get("nascita"))
                    if cb and cb["y"] - pb["y"] == A:
                        out["indice"].append(f'{lbl(p)}: nascita di {c.get("nome")} a {A} anni ({cb["y"]})')
    return out


def testo_diario(g):
    """Riassunto sintetico per una voce del diario clinico."""
    r = ripetizioni(g)
    n = len(g["persone"])
    gen = (max((v["gen"] for v in impagina(g)[0].values()), default=-1) + 1) if n else 0
    righe = [f"Genosociogramma «{g.get('titolo', '')}»: {n} persone su {gen} generazioni, "
             f"{len(g['unioni'])} unioni, {len(g['legami'])} legami affettivi annotati."]
    if r["indice_eta"] is not None and r["indice"]:
        righe.append(f"Alla stessa età attuale del paziente ({r['indice_eta']} anni): " + "; ".join(r["indice"]) + ".")
    for k, t in (("eta", "Età alla morte ricorrenti"), ("date", "Coincidenze di data"), ("nomi", "Nomi ricorrenti")):
        if r[k]:
            righe.append(f"{t}: " + "; ".join(r[k]) + ".")
    return "\n".join(righe)
