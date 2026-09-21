# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════╗
║  RELAZIONE DISCORSIVA — sul modello del report optometrico classico  ║
║                                                                      ║
║  La relazione che il gestionale produceva era un elenco di misure:   ║
║  «PPC accomodativo: 15.0 / 10.0 cm». Corretto, ma illeggibile per    ║
║  una famiglia, per la scuola e per un collega non optometrista.      ║
║                                                                      ║
║  Questa segue l'impianto del report cartaceo: per ogni area          ║
║  funzionale prima si spiega A COSA SERVE quella funzione, poi come   ║
║  è risultata, poi QUALI SINTOMI produce quando è in difficoltà.      ║
║  Alla fine le conclusioni e le indicazioni operative.                ║
║                                                                      ║
║  Nota importante: qui l'AI non serve quasi mai.                      ║
║    · le spiegazioni sono testi fissi, scritti una volta;             ║
║    · i giudizi vengono dal punteggio 1-5 della sezione F, che il     ║
║      clinico ha già assegnato guardando le misure;                   ║
║    · i sintomi sono elenchi legati all'area;                         ║
║    · le indicazioni si accendono in base a cosa è risultato debole.  ║
║  Resta all'AI solo la sintesi che lega le aree fra loro — e anche    ║
║  lì propone, non decide.                                             ║
║                                                                      ║
║  È UN CANOVACCIO. I testi stanno tutti nel dizionario AREE qui       ║
║  sotto, uno accanto all'altro, in italiano: si correggono e si       ║
║  ampliano senza toccare la logica. Vanno riletti e adattati al       ║
║  metodo PNEV prima di consegnarli a un paziente.                     ║
╚══════════════════════════════════════════════════════════════════════╝
"""
from __future__ import annotations

# Soglie sul punteggio 1-5 della sezione F.
SOGLIA_DEFICIT = 2      # <= 2 → area in difficoltà, si stampano i sintomi
SOGLIA_LIMITE = 3       # == 3 → ai limiti


# ══════════════════════════════════════════════════════════════════════
#  I TESTI — è qui che si interviene
#
#  Per ogni area:
#    titolo       come compare nella relazione
#    spiega       a cosa serve quella funzione, in parole piane
#    misure       chiavi da cui pescare i valori misurati (facoltativo)
#    sintomi      cosa si osserva quando l'area è in difficoltà
# ══════════════════════════════════════════════════════════════════════

AREE = {
    "av_l": {
        "titolo": "Acuità visiva da lontano",
        "spiega": (
            "L'acuità visiva misura quanto è nitida l'immagine, ma non dice "
            "quanto sforzo serve per ottenerla: si può vedere dieci decimi e "
            "affaticarsi molto. Da lontano interessa la lavagna, la strada, "
            "lo sport."),
        "sintomi": [
            "difficoltà a copiare dalla lavagna",
            "tendenza a socchiudere gli occhi per mettere a fuoco",
            "avvicinarsi agli oggetti per riconoscerli",
        ],
    },
    "av_v": {
        "titolo": "Acuità visiva da vicino",
        "spiega": (
            "È la nitidezza alla distanza di lettura e scrittura, dove si "
            "svolge gran parte del lavoro scolastico e professionale."),
        "sintomi": [
            "avvicinarsi al foglio quando si legge o si scrive",
            "lettura lenta e faticosa",
            "perdita di comprensione con il passare dei minuti",
        ],
    },
    "conv": {
        "titolo": "Convergenza",
        "spiega": (
            "La convergenza è la capacità di portare e mantenere i due occhi "
            "sullo stesso punto vicino. Serve a tenere una sola immagine "
            "nitida durante la lettura: quando cede, il testo si sdoppia o "
            "sfuoca e si smette di leggere prima per stanchezza che per "
            "difficoltà di comprensione."),
        "sintomi": [
            "mal di testa dopo la lettura o lo studio",
            "visione doppia o sfocata da vicino",
            "bruciore e arrossamento degli occhi",
            "tendenza a evitare i compiti da vicino",
            "chiudere o coprire un occhio per leggere",
        ],
    },
    "vg_bo": {
        "titolo": "Vergenze in base esterna",
        "spiega": (
            "Sono la riserva di convergenza disponibile: quanto margine c'è "
            "oltre lo sforzo già richiesto dalla lettura. Una riserva scarsa "
            "significa lavorare sempre al limite."),
        "sintomi": [
            "affaticamento che compare dopo pochi minuti di lettura",
            "difficoltà a riprendere il segno dopo una pausa",
            "senso di pesantezza agli occhi a fine giornata",
        ],
    },
    "vg_bi": {
        "titolo": "Vergenze in base interna",
        "spiega": (
            "Sono la riserva di divergenza, quella che permette di passare "
            "dal vicino al lontano senza che l'immagine resti appannata."),
        "sintomi": [
            "vista appannata quando si alza lo sguardo dal foglio",
            "difficoltà a passare dal banco alla lavagna",
        ],
    },
    "acc": {
        "titolo": "Accomodazione",
        "spiega": (
            "L'accomodazione è la messa a fuoco da vicino. È un lavoro "
            "muscolare continuo: durante un'ora di studio l'occhio la "
            "sostiene senza interruzioni, e quando la riserva è insufficiente "
            "il testo perde nitidezza a poco a poco."),
        "sintomi": [
            "il fuoco «viene e va» durante la lettura",
            "stanchezza e sonnolenza sui libri",
            "difficoltà a mantenere l'attenzione sul testo",
            "riduzione della comprensione con il passare del tempo",
        ],
    },
    "fac_acc": {
        "titolo": "Flessibilità accomodativa",
        "spiega": (
            "È la rapidità con cui il fuoco si sposta dal vicino al lontano e "
            "viceversa. Conta ogni volta che si alza lo sguardo dal quaderno "
            "alla lavagna, o dal volante al cruscotto."),
        "sintomi": [
            "immagine appannata per qualche secondo nel cambio di distanza",
            "difficoltà a copiare dalla lavagna senza perdere il punto",
            "affaticamento nei compiti che alternano le distanze",
        ],
    },
    "sacc": {
        "titolo": "Movimenti saccadici",
        "spiega": (
            "Le saccadi sono gli spostamenti rapidi dello sguardo da un punto "
            "all'altro: lungo la riga di testo, da una parola alla "
            "successiva, dal banco alla lavagna. Se non sono precise, la "
            "lettura si interrompe di continuo anche quando la capacità di "
            "leggere è intatta."),
        "sintomi": [
            "saltare o rileggere parole e righe",
            "perdere il segno durante la lettura",
            "usare il dito per tenere il rigo",
            "muovere la testa invece degli occhi",
            "lettura lenta con comprensione buona all'ascolto",
        ],
    },
    "purs": {
        "titolo": "Movimenti di inseguimento",
        "spiega": (
            "Sono i movimenti lenti e continui con cui lo sguardo segue un "
            "oggetto che si muove. Servono nello sport, nel traffico, e in "
            "generale ogni volta che l'attenzione deve restare agganciata a "
            "qualcosa che si sposta."),
        "sintomi": [
            "difficoltà a seguire una palla o a prenderla al volo",
            "movimenti a scatti invece che fluidi",
            "compenso con il movimento della testa",
            "scarsa sicurezza nei giochi di squadra",
        ],
    },
    "stereo": {
        "titolo": "Stereopsi",
        "spiega": (
            "La stereopsi è la percezione della profondità, che nasce "
            "dall'uso simultaneo dei due occhi. Senza, il mondo resta "
            "leggibile ma piatto: si valutano peggio le distanze."),
        "sintomi": [
            "difficoltà a valutare le distanze",
            "insicurezza sulle scale o sui dislivelli",
            "difficoltà nei giochi con la palla",
            "urtare gli spigoli o versare accanto al bicchiere",
        ],
    },
    "fiss": {
        "titolo": "Fissazione",
        "spiega": (
            "È la capacità di tenere lo sguardo fermo e centrato su un punto. "
            "È la base di tutto il resto: senza una fissazione stabile né la "
            "lettura né la messa a fuoco possono restare precise."),
        "sintomi": [
            "sguardo che scivola via dal punto osservato",
            "sbattere spesso le palpebre",
            "periodo di attenzione breve sul lavoro da vicino",
        ],
    },
    "perc": {
        "titolo": "Percezione visiva",
        "spiega": (
            "La percezione visiva è ciò che il cervello fa dell'immagine una "
            "volta ricevuta: riconoscere una forma, distinguerla dallo "
            "sfondo, ricordarla, orientarla nello spazio. È qui che la vista "
            "diventa lettura, scrittura e calcolo."),
        "sintomi": [
            "confondere lettere simili (b/d, p/q, m/n)",
            "invertire lettere o numeri nella scrittura",
            "difficoltà a ritrovare la stessa parola in una pagina",
            "confondere destra e sinistra",
            "grafia irregolare, difficoltà a rispettare i margini",
            "ricordare meglio ciò che si ascolta di ciò che si vede",
        ],
    },
}

ORDINE = ["av_l", "av_v", "fiss", "sacc", "purs", "acc", "fac_acc",
          "conv", "vg_bo", "vg_bi", "stereo", "perc"]


# ══════════════════════════════════════════════════════════════════════
#  Indicazioni operative — il «SI CONSIGLIA» del report classico
#
#  Ogni voce si accende se una delle sue aree è risultata debole.
#  "sempre": True → compare comunque.
# ══════════════════════════════════════════════════════════════════════

INDICAZIONI = [
    {
        "quando": ["conv", "vg_bo", "vg_bi", "acc", "fac_acc", "sacc", "purs", "fiss"],
        "testo": (
            "Un programma di training visivo optometrico, per ripristinare una "
            "buona coordinazione fra i due occhi e consolidare le abilità "
            "visive richieste dallo studio e dal lavoro. Il programma è "
            "individuale e si articola in attività monoculari, binoculari, "
            "visuo-spaziali, percettive e visuo-motorie, con integrazione "
            "multisensoriale secondo il metodo PNEV."),
    },
    {
        "quando": ["acc", "fac_acc", "conv", "av_v"],
        "testo": (
            "Una seduta di igiene visiva, per impostare la postura di lettura, "
            "la distanza di lavoro, l'illuminazione e la gestione delle pause. "
            "È il primo intervento e spesso il più efficace in rapporto al "
            "tempo richiesto."),
    },
    {
        "quando": ["perc"],
        "testo": (
            "Un approfondimento neuropsicologico, per distinguere la "
            "componente percettiva da un eventuale disturbo specifico "
            "dell'apprendimento e calibrare di conseguenza l'intervento."),
    },
    {
        "quando": ["av_l", "av_v"],
        "testo": (
            "L'uso della correzione ottica prescritta, con le modalità e per "
            "le distanze indicate nella ricetta allegata."),
    },
    {
        "quando": ["stereo", "purs"],
        "testo": (
            "Attività di integrazione visuo-motoria e, dove opportuno, un "
            "percorso di sports vision, per trasferire le abilità recuperate "
            "nel movimento e nel gesto."),
    },
    {
        "quando": [],
        "sempre": True,
        "testo": (
            "Un controllo di verifica a distanza di due mesi, per misurare "
            "l'evoluzione del quadro e decidere se proseguire, modificare o "
            "concludere il percorso."),
    },
]


# ══════════════════════════════════════════════════════════════════════
#  Giudizi
# ══════════════════════════════════════════════════════════════════════

def _punteggio(sez_f, chiave):
    try:
        v = int(sez_f.get(chiave))
        return v if 1 <= v <= 5 else None
    except Exception:
        return None


def _giudizio(p):
    """Dal punteggio 1-5 alla frase. Sono le stesse categorie del report
    cartaceo, dove però le alternative si stampavano tutte e si cancellava
    a penna quella sbagliata."""
    if p is None:
        return None
    if p <= 1:
        return "risulta nettamente inferiore alle aspettative per l'età"
    if p == 2:
        return "risulta inferiore alle aspettative per l'età"
    if p == 3:
        return "si colloca ai limiti inferiori della norma"
    if p == 4:
        return "risulta nella norma per l'età"
    return "risulta pienamente adeguata, al di sopra della media per l'età"


def _in_difficolta(p):
    return p is not None and p <= SOGLIA_DEFICIT


# ══════════════════════════════════════════════════════════════════════
#  Misure a supporto — i numeri restano, ma dentro la frase
# ══════════════════════════════════════════════════════════════════════

def _vuoto(x):
    if x is None:
        return True
    return str(x).strip().lower() in ("", "nd", "n.d.", "none", "-", "—")


def _zero(x):
    if _vuoto(x):
        return True
    try:
        return float(x) == 0.0
    except Exception:
        return False


def _misure(chiave, a, b, c, dd):
    """Frase con i valori realmente misurati per quell'area, o None.

    I numeri non spariscono: smettono di essere un elenco e diventano la
    prova di quello che la frase precedente ha appena detto."""
    if chiave == "conv":
        rot, rec = b.get("ppc_acc_rot"), b.get("ppc_acc_rec")
        if not (_zero(rot) and _zero(rec)):
            return (f"Il punto prossimo di convergenza è stato rilevato a "
                    f"{rot} cm con recupero a {rec} cm (valori attesi: rottura "
                    f"entro 10 cm, recupero entro 15 cm).")
    if chiave == "acc":
        od, os_ = c.get("pu_od"), c.get("pu_os")
        if not (_zero(od) and _zero(os_)):
            return (f"L'ampiezza accomodativa misurata con metodo push-up è di "
                    f"{od} diottrie in occhio destro e {os_} in occhio sinistro.")
    if chiave == "fac_acc":
        od, os_ = c.get("fl_od"), c.get("fl_os")
        if not (_zero(od) and _zero(os_)):
            return (f"La flessibilità accomodativa è di {od} cicli al minuto in "
                    f"occhio destro e {os_} in occhio sinistro.")
    if chiave == "stereo":
        r = b.get("randot")
        if not _zero(r):
            return f"Al test Randot la stereopsi è risultata di {r} secondi d'arco."
    if chiave == "fiss":
        fod, fos = dd.get("fiss_od"), dd.get("fiss_os")
        if not (_vuoto(fod) and _vuoto(fos)):
            return (f"La fissazione monoculare è risultata «{fod}» in occhio "
                    f"destro e «{fos}» in occhio sinistro.")
    if chiave in ("vg_bo", "vg_bi"):
        aca = b.get("aca")
        if not _zero(aca) and chiave == "vg_bo":
            return (f"Il rapporto AC/A è risultato di {aca}:1 "
                    f"(valore atteso fra 3 e 5).")
    if chiave == "av_l":
        rs_od, rs_os = a.get("rs_od", {}) or {}, a.get("rs_os", {}) or {}
        vd, vs = rs_od.get("acuita"), rs_os.get("acuita")
        if not (_vuoto(vd) and _vuoto(vs)):
            parti = []
            if not _vuoto(vd):
                parti.append(f"{vd} in occhio destro")
            if not _vuoto(vs):
                parti.append(f"{vs} in occhio sinistro")
            return "Con la migliore correzione l'acuità è di " + " e ".join(parti) + "."
    return None


def _refrazione(a):
    """Riga della refrazione soggettiva, saltando l'occhio non compilato."""
    def occhio(sigla, r):
        r = r or {}
        if all(_zero(r.get(k)) for k in ("sf", "cil", "ax")):
            return None
        def f(v):
            try:
                x = float(v or 0)
                return f"+{x:.2f}" if x >= 0 else f"{x:.2f}"
            except Exception:
                return str(v or "")
        return f"{sigla} {f(r.get('sf'))} ({f(r.get('cil'))} × {r.get('ax', 0)}°)"
    parti = [x for x in (occhio("occhio destro", a.get("rs_od")),
                         occhio("occhio sinistro", a.get("rs_os"))) if x]
    if not parti:
        return None
    return "All'esame soggettivo la refrazione è risultata: " + "; ".join(parti) + "."


# ══════════════════════════════════════════════════════════════════════
#  Composizione
# ══════════════════════════════════════════════════════════════════════

def componi_relazione(d: dict, nome_paziente: str = "", eta=None,
                      diagnosi: str = "", piano: str = "",
                      motivo: str = "") -> str:
    """Relazione discorsiva. Ritorna testo con i titoli marcati «###»,
    nel formato che genera_carta_intestata e il Word già sanno impaginare."""
    a = d.get("sez_a", {}) or {}
    b = d.get("sez_b", {}) or {}
    c = d.get("sez_c", {}) or {}
    dd = d.get("sez_d", {}) or {}
    f = d.get("sez_f", {}) or {}

    chi = nome_paziente.strip() or "Il paziente"
    righe = []

    if motivo.strip():
        righe += ["### Motivo della valutazione", motivo.strip(), ""]

    righe += [
        "### Come si legge questa relazione",
        "Per ogni area funzionale sono indicati a cosa serve quella funzione, "
        "come è risultata all'esame e, quando è emersa una difficoltà, quali "
        "manifestazioni quotidiane le si associano. I valori misurati sono "
        "riportati accanto al giudizio.",
        "",
    ]

    refr = _refrazione(a)
    if refr:
        righe += ["### Stato refrattivo", refr, ""]

    deboli = []
    for chiave in ORDINE:
        area = AREE.get(chiave)
        if not area:
            continue
        p = _punteggio(f, chiave)
        giud = _giudizio(p)
        if giud is None:
            continue          # area non valutata: non se ne parla

        righe.append("### " + area["titolo"])
        righe.append(area["spiega"])
        righe.append(f"All'esame, in {chi} questa funzione {giud}.")

        m = _misure(chiave, a, b, c, dd)
        if m:
            righe.append(m)

        if _in_difficolta(p):
            deboli.append(chiave)
            righe.append("Una difficoltà in quest'area si manifesta abitualmente con:")
            for s in area["sintomi"]:
                righe.append(f"• {s}")
        righe.append("")

    # ── Conclusioni ───────────────────────────────────────────────────
    righe.append("### Conclusioni")
    if deboli:
        elenco = [AREE[k]["titolo"].lower() for k in deboli]
        if len(elenco) == 1:
            testo = elenco[0]
        else:
            testo = ", ".join(elenco[:-1]) + " e " + elenco[-1]
        righe.append(
            f"La valutazione ha evidenziato in {chi} una difficoltà nelle "
            f"seguenti aree: {testo}. Le altre funzioni esaminate si collocano "
            f"entro i valori attesi per l'età.")
        righe.append(
            "Le aree risultate deboli non vanno lette separatamente: nel "
            "modello PNEV concorrono allo stesso quadro funzionale, e "
            "l'intervento agisce sulla loro integrazione più che sul singolo "
            "parametro.")
    else:
        righe.append(
            f"Tutte le funzioni esaminate si collocano entro i valori attesi "
            f"per l'età. Non emergono elementi che richiedano un intervento "
            f"riabilitativo sul versante visuo-percettivo.")
    if diagnosi.strip():
        righe += ["", diagnosi.strip()]
    righe.append("")

    # ── Si consiglia ──────────────────────────────────────────────────
    voci = []
    for ind in INDICAZIONI:
        if ind.get("sempre") or any(k in deboli for k in ind["quando"]):
            voci.append(ind["testo"])
    if voci:
        righe.append("### Si consiglia")
        for n, t in enumerate(voci, start=1):
            righe.append(f"{n}. {t}")
        righe.append("")

    if piano.strip():
        righe += ["### Piano terapeutico", piano.strip(), ""]

    while righe and not righe[-1]:
        righe.pop()
    return "\n".join(righe)
