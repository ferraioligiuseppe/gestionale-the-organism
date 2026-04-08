# -*- coding: utf-8 -*-
"""
ui_questionari_pnev.py — Moduli questionari PNEV
Implementa:
  - Melillo Adulti (100 domande A/B, dominanza emisferica)
  - Melillo Bambini (checklist Destro/Sinistro per categorie)
  - Fisher Auditivo Bambini
  - Visione Bambini
  - Visione Adulti
  - Disordine Sensomotorio Adulti (checklist)

Pattern identico a inpps_collect_ui() in app_core.py:
  collect_ui(prefix, existing) -> (dict, summary_str)
"""

from __future__ import annotations
from datetime import date
from typing import Any, Optional
import streamlit as st


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS COMUNI
# ─────────────────────────────────────────────────────────────────────────────

def _cb(label: str, val: bool, key: str) -> bool:
    return st.checkbox(label, value=bool(val), key=key)

def _radio_ab(num: int, testo_a: str, testo_b: str, val: str, prefix: str) -> str:
    opts = ["A", "B"]
    idx = 1 if val == "B" else 0
    scelta = st.radio(
        f"**{num}.** A: {testo_a}  \nB: {testo_b}",
        options=opts,
        index=idx,
        key=f"{prefix}_q{num:03d}",
        horizontal=True,
    )
    return scelta


# ─────────────────────────────────────────────────────────────────────────────
# 1. MELILLO ADULTI — 100 domande A/B
# ─────────────────────────────────────────────────────────────────────────────

MELILLO_ADULTI_DOMANDE = [
    (1,  "Mi piace fare e imparare le cose un passo alla volta",
         "Mi piace fare e imparare molte cose contemporaneamente"),
    (2,  "Tendo a concentrarmi sui dettagli",
         "Tendo a concentrarmi sul quadro generale"),
    (3,  "Non sempre capisco la battuta o la trovo divertente come gli altri",
         "Capisco sempre la battuta, anche prima degli altri"),
    (4,  "Non mi piace il cambiamento",
         "Ho bisogno di cambiare le cose spesso"),
    (5,  "Mi piacciono le routine",
         "Raramente faccio le cose nello stesso modo"),
    (6,  "Ho una calligrafia molto buona",
         "Ho una calligrafia scarsa"),
    (7,  "Mi piace quando le cose sono chiaramente definite e precise",
         "Mi piace pensare in termini generali"),
    (8,  "Tendo a prendere le cose alla lettera",
         "Sono bravo a leggere tra le righe"),
    (9,  "Leggo un contratto o le istruzioni più volte per non perdere nulla",
         "Non mi piace leggere contratti o istruzioni"),
    (10, "Credo o mi è stato detto di avere un QI alto",
         "Credo o mi è stato detto di avere un QI nella media"),
    (11, "Ho ottenuto risultati migliori nella parte matematica del SAT",
         "Ho ottenuto risultati migliori nella parte verbale del SAT"),
    (12, "Mi piaceva la scuola e sono bravo/a in ambito accademico",
         "Non mi piaceva la scuola e ha influenzato i miei voti"),
    (13, "Sono bravo/a nell'apprendimento tramite memorizzazione e ripetizione",
         "Imparo meglio facendo le cose"),
    (14, "Preferirei lavorare con i computer",
         "Preferirei lavorare con le persone"),
    (15, "Non sono bravo/a con le nuove idee",
         "Sono molto bravo/a nel trovare nuove idee"),
    (16, "Non sono bravo/a nella risoluzione creativa dei problemi",
         "Sono molto bravo/a nella risoluzione dei problemi, specialmente quando richiede una soluzione creativa"),
    (17, "Ero più bravo/a in algebra che in geometria",
         "Ero più bravo/a in geometria che in algebra"),
    (18, "È facile per me visualizzare le cose",
         "È difficile per me visualizzare le cose"),
    (19, "Non riesco a ruotare facilmente gli oggetti nella mia mente",
         "Riesco a ruotare facilmente gli oggetti nella mia mente"),
    (20, "Ho difficoltà a fare amicizia",
         "Faccio amicizia facilmente"),
    (21, "Non vado molto d'accordo con il sesso opposto",
         "Vado molto d'accordo con il sesso opposto"),
    (22, "Non sono una persona emotiva e non mostro mai emozioni",
         "Sono una persona emotiva e mostro le emozioni facilmente"),
    (23, "Preferisco gli sport individuali",
         "Preferisco gli sport di squadra"),
    (24, "Non riesco mai a capire cosa sta pensando qualcuno",
         "Penso sempre di sapere cosa sta pensando qualcuno"),
    (25, "Mi piace leggere",
         "Non leggo molto"),
    (26, "Sono molto bravo/a nell'ortografia e nella grammatica",
         "Non sono granché nell'ortografia e nella grammatica"),
    (27, "Mi piace leggere libri tecnici e non fiction",
         "Mi piace leggere romanzi e storie"),
    (28, "Se non capisco una parola mi fermo a cercarla il più delle volte",
         "Se non capisco una parola generalmente vado avanti e la capisco dopo"),
    (29, "Ho sempre potuto fare calcoli facilmente in testa",
         "Non faccio bene i calcoli in testa; ho bisogno di scriverli"),
    (30, "Mi piacciono i numeri; sono bravo/a coi numeri",
         "Non mi piacciono i numeri"),
    (31, "Sono più bravo/a nei libri che per strada",
         "Sono più bravo/a per strada che sui libri"),
    (32, "Mi piace pianificare in anticipo",
         "Odio pianificare; voglio solo capire man mano che vado"),
    (33, "Non sono bravo/a con le metafore; mi piacciono i fatti",
         "Mi piacciono le metafore o gli esempi ipotetici"),
    (34, "Leggerò attentamente le istruzioni prima di provare qualcosa",
         "Non leggo mai le istruzioni; preferisco buttarmi"),
    (35, "A volte fatico a capire l'idea principale di una storia",
         "Capisco sempre l'idea principale di una storia"),
    (36, "Sono più bravo/a a capire che a fare",
         "Sono più bravo/a a fare che a capire"),
    (37, "Sono logico/a; tendo a riflettere attentamente prima di agire",
         "Sono intuitivo/a; mi piace agire d'istinto"),
    (38, "Ho un'ottima memoria per fatti e dettagli",
         "Non ho un'ottima memoria per fatti e dettagli"),
    (39, "Ricordo i nomi non i volti",
         "Sono molto bravo/a coi volti ma dimentico i nomi"),
    (40, "Ho un pessimo senso dell'orientamento",
         "Ho un ottimo senso dell'orientamento"),
    (41, "Ho uno scatto d'ira esplosivo se vengo provocato/a",
         "Ci vuole molto per farmi arrabbiare; le cose non mi turbano molto"),
    (42, "Preferisco lavorare da solo/a",
         "Preferisco lavorare in squadra"),
    (43, "Quando qualcuno dice che ha buone e cattive notizie, voglio sentire prima le cattive",
         "Quando qualcuno dice che ha buone e cattive notizie, voglio sentire prima le buone"),
    (44, "Sono bravo/a a risparmiare denaro",
         "Non sono bravo/a a risparmiare denaro"),
    (45, "Mi piace tenere le cose; ci vuole molto prima che butti qualcosa",
         "Mi piace sbarazzarmi delle cose vecchie e sostituirle con cose nuove"),
    (46, "Mi piace l'arte realistica",
         "Mi piace l'arte astratta"),
    (47, "Non mi concentro molto su come appaio",
         "Sono molto consapevole del mio aspetto"),
    (48, "Non noto cosa pensano gli altri di me",
         "Noto e mi importa molto di quello che pensano gli altri di me"),
    (49, "Non conosco né seguo le tendenze della moda",
         "Adoro indossare gli ultimi stili"),
    (50, "Preferisco indossare abiti classici che porto da anni e che sono comodi",
         "Preferisco indossare stili più nuovi anche se sono scomodi"),
    (51, "Alcune persone mi considererebbero un nerd",
         "Nessuno mi considererebbe mai un nerd"),
    (52, "In generale rispetto le leggi e le regole",
         "In generale non seguo le regole; la maggior parte non ha senso"),
    (53, "Lavoro meglio con il rinforzo positivo; lavoro per raggiungere un obiettivo",
         "Lavoro meglio con il rinforzo negativo; mi concentro sull'evitare il fallimento"),
    (54, "Sono molto ordinato/a e organizzato/a",
         "Sarei considerato/a disordinato/a e disorganizzato/a"),
    (55, "Mi piace stare da solo/a",
         "Mi piace stare con gli altri"),
    (56, "Non ricordo mai le parole di una canzone; mi piace di più la musica",
         "Mi piacciono le parole di una canzone e le ricordo quasi istantaneamente"),
    (57, "Preferisco il giallo o l'arancione (colori caldi)",
         "Preferisco il viola, il blu o il verde (colori freddi)"),
    (58, "Mi piacciono le cose artificiali e meccaniche",
         "Mi piacciono le cose naturali"),
    (59, "Sono un/a perfezionista",
         "Non mi importa se le cose non sono perfette"),
    (60, "Non mostrerei mai a qualcuno qualcosa che ho scritto senza prima controllare errori grammaticali o di ortografia",
         "Sono più interessato/a al contenuto generale di quello che scrivo che ai dettagli come ortografia o grammatica"),
    (61, "Non sono bravo/a nella scrittura creativa",
         "Mi piace scrivere le mie storie"),
    (62, "Mi piace ascoltare la musica classica",
         "Mi piace la musica popolare (rock o country)"),
    (63, "Sono molto bravo/a nell'apprendimento delle lingue",
         "Sono pessimo/a nelle lingue"),
    (64, "Sono più bravo/a a leggere i libri che le persone",
         "Sono più bravo/a a leggere le persone che i libri"),
    (65, "Capisco mentalmente la sofferenza, ma non la sento davvero",
         "Mi sento molto male o triste per gli altri che soffrono"),
    (66, "Raramente mi deprimo",
         "Mi deprimo facilmente"),
    (67, "In generale non mi piace essere toccato/a, specialmente da qualcuno che non conosco",
         "Ho bisogno del contatto umano e mi piace essere toccato/a e toccare gli altri"),
    (68, "Sono un po' scoordinato/a, non molto atletico/a",
         "In generale sono molto coordinato/a e atletico/a"),
    (69, "Preferirei stare in casa",
         "Preferirei stare fuori"),
    (70, "Mi piace andare in vacanza sempre negli stessi posti",
         "Mi piace andare in vacanza in posti nuovi"),
    (71, "Non mi piacciono le feste e i raduni sociali in generale",
         "Adoro le feste e i raduni sociali"),
    (72, "Sono un realista",
         "Sono un sognatore"),
    (73, "La funzione è molto più importante dello stile e del design",
         "Il design è almeno importante quanto la funzione"),
    (74, "Preferisco la matematica, la ricerca o la scienza",
         "Preferisco la filosofia e la mitologia"),
    (75, "Preferirei comunicare tramite testo o email",
         "Preferirei comunicare al telefono o di persona"),
    (76, "Non sono una persona socievole",
         "Sono decisamente una persona socievole"),
    (77, "Preferisco essere organizzato/a e pianificare le cose",
         "Preferisco essere spontaneo/a e non preoccuparmi dei dettagli"),
    (78, "Penso che sia importante migliorare le cose esistenti",
         "Penso che sia importante sviluppare cose e idee nuove"),
    (79, "Penso che la ragione sia più importante dei sentimenti",
         "Penso che i sentimenti siano più importanti della ragione"),
    (80, "Quando imparo un nuovo capitolo di un libro di testo, penso che sia meglio fare uno schema del capitolo",
         "Quando imparo un nuovo capitolo di un libro di testo, penso che sia meglio riassumere il capitolo"),
    (81, "Sono più bravo/a nei cruciverba",
         "Sono più bravo/a nei puzzle"),
    (82, "In una produzione teatrale, preferirei essere il regista",
         "In una produzione teatrale, preferirei essere il protagonista"),
    (83, "Se sto imparando a usare un nuovo apparecchio: leggo attentamente il manuale prima di iniziare",
         "Se sto imparando a usare un nuovo apparecchio: mi butto e vado (uso il manuale come ultima risorsa)"),
    (84, "Quello che viene detto (le parole) è più importante di come viene detto (tono, ritmo, volume, emozione)",
         "Come viene detto qualcosa (tono, ritmo, volume, emozione) è più importante di quello che viene detto"),
    (85, "Non uso gesti con le mani quando parlo",
         "Uso molti gesti e movimenti delle mani quando parlo"),
    (86, "Se appendessi un quadro a una parete, misurerei attentamente per essere sicuro/a che sia centrato e dritto",
         "Se appendessi un quadro a una parete, lo metterei dove sembra giusto e lo sposterei se necessario"),
    (87, "Al lavoro: mi concentro su un compito alla volta fino al completamento",
         "Al lavoro: di solito gestisco più cose contemporaneamente"),
    (88, "Mi piace pianificare i miei passi futuri",
         "Mi piace sognare il mio futuro"),
    (89, "Mi piace scomporre le idee e guardarle separatamente",
         "Mi piace mettere insieme le idee"),
    (90, "Mi piace imparare le cose di cui siamo certi",
         "Mi piace imparare le possibilità nascoste"),
    (91, "Penso che sia più emozionante migliorare qualcosa",
         "Penso che sia più emozionante inventare qualcosa"),
    (92, "Sono forte nel ricordare materiale verbale (nomi, date)",
         "Sono forte nel ricordare materiale spaziale (direzioni e luoghi)"),
    (93, "Preferisco il silenzio totale quando leggo o studio",
         "Preferisco avere musica mentre leggo o studio"),
    (94, "Penso in parole",
         "Penso in immagini"),
    (95, "Da bambino/a, la cosa peggiore sarebbe stata: bocciare un test",
         "Da bambino/a, la cosa peggiore sarebbe stata: essere imbarazzato/a in classe"),
    (96, "Imparo meglio da insegnanti che spiegano con le parole",
         "Imparo meglio da insegnanti che spiegano con immagini, movimento e azioni"),
    (97, "Mi piace esprimere sentimenti e idee in linguaggio semplice",
         "Mi piace esprimere sentimenti e idee in poesia, canzone, danza e arte"),
    (98, "Preferirei non fare supposizioni o seguire intuizioni",
         "Mi piace seguire intuizioni e fare supposizioni"),
    (99, "Sono molto diretto/a e schietto/a con le persone",
         "Cerco di non ferire i sentimenti di qualcuno, quindi non sono così diretto/a"),
    (100,"Penso che la qualità migliore sia essere riservato/a e modesto/a",
         "Penso che la qualità migliore sia essere estroverso/a e interessante"),
]


def melillo_adulti_ui(prefix: str, existing: dict | None = None) -> tuple[dict, str]:
    """Melillo Cognitive Style Assessment adulti — 100 domande A/B."""
    existing = existing or {}
    risposte = existing.get("risposte", {})

    st.markdown("### 🧠 Melillo Cognitive Style Assessment – Adulti")
    st.caption(
        "Scegli la risposta che descrive meglio la tua tendenza naturale, non il comportamento appreso. "
        "Pensa a te stesso/a da bambino/a, adolescente o giovane adulto/a. "
        "**Scegli sempre una risposta per ogni domanda.**"
    )

    nuove_risposte = {}
    for num, testo_a, testo_b in MELILLO_ADULTI_DOMANDE:
        val_prec = risposte.get(f"Q{num:03d}", "A")
        with st.container():
            scelta = _radio_ab(num, testo_a, testo_b, val_prec, prefix)
            nuove_risposte[f"Q{num:03d}"] = scelta

    # Scoring
    tot_a = sum(1 for v in nuove_risposte.values() if v == "A")
    tot_b = sum(1 for v in nuove_risposte.values() if v == "B")
    diff = abs(tot_a - tot_b)
    dominanza = "Sinistra (A)" if tot_a >= tot_b else "Destra (B)"

    # Visualizzazione risultato
    st.markdown("---")
    st.markdown("#### 📊 Risultato scoring")
    col1, col2, col3 = st.columns(3)
    col1.metric("Totale A (Sinistra)", tot_a)
    col2.metric("Totale B (Destra)", tot_b)
    col3.metric("Differenza", diff)

    if tot_a > tot_b:
        intensita = "forte" if diff >= 40 else "moderata" if diff >= 20 else "lieve"
        st.success(f"🧠 Dominanza **emisferica sinistra** ({intensita}) — {tot_a}A – {tot_b}B = {diff}A")
    elif tot_b > tot_a:
        intensita = "forte" if diff >= 40 else "moderata" if diff >= 20 else "lieve"
        st.info(f"🧠 Dominanza **emisferica destra** ({intensita}) — {tot_b}B – {tot_a}A = {diff}B")
    else:
        st.warning("🧠 **Profilo bilanciato** — nessuna dominanza emisferica prevalente")

    result = {
        "version": "melillo_adulti_v1",
        "date": date.today().isoformat(),
        "risposte": nuove_risposte,
        "scoring": {
            "tot_a": tot_a,
            "tot_b": tot_b,
            "differenza": diff,
            "dominanza": dominanza,
        },
    }

    summary = (
        f"Melillo Adulti: A={tot_a} B={tot_b} → Dominanza {dominanza} (diff={diff})"
    )
    return result, summary


# ─────────────────────────────────────────────────────────────────────────────
# 2. MELILLO BAMBINI — checklist Destro / Sinistro per categorie
# ─────────────────────────────────────────────────────────────────────────────

MELILLO_BAMBINI_DESTRO = {
    "Motorie": [
        "Goffaggine e postura strana",
        "Scarso coordinamento",
        "Non è atleticamente incline e non ha interesse negli sport",
        "Basso tono muscolare (muscoli sembrano deboli)",
        "Scarse capacità motorie grossolane (bicicletta, correre, cammina stranamente)",
        "Manierismi motori ripetitivi/stereotipati (gira in tondo, agita le braccia)",
        "Si agita eccessivamente",
        "Scarso contatto visivo",
        "Cammina sulle punte dei piedi da piccolo",
    ],
    "Sensoriali": [
        "Scarso orientamento spaziale: si imbatte spesso nelle cose",
        "Sensibilità al suono",
        "Confusione quando gli si chiede di indicare parti del corpo",
        "Scarso senso dell'equilibrio",
        "Alta soglia per il dolore (non piange quando si taglia)",
        "Ama girare, giostre, altalene — qualsiasi cosa con movimento",
        "Tocca le cose compulsivamente",
        "Non ama la sensazione dei vestiti su braccia o gambe",
        "Non ama essere toccato e non gli piace toccare le cose",
        "Annusa incessantemente tutto",
        "Preferisce cibi insipidi",
        "Evita il cibo per il suo aspetto",
        "Odia dover mangiare e non è interessato nemmeno ai dolci",
        "Mangiatore estremamente esigente",
    ],
    "Emotive": [
        "Piange e/o ride spontaneamente, improvvise esplosioni di rabbia o paura",
        "Si preoccupa molto e ha diverse fobie",
        "Si aggrappa alle ferite passate",
        "Improvvise esplosioni emotive iperreattive e inappropriate",
        "Attacchi di panico e/o ansia",
        "A volte mostra pensieri oscuri o violenti",
        "Il viso manca di espressione (poco linguaggio del corpo)",
        "Troppo teso, non riesce a rilassarsi",
        "Manca di empatia e sentimenti per gli altri",
        "Manca di reciprocità emotiva",
        "Spesso sembra senza paura ed è amante del rischio",
    ],
    "Comportamentali": [
        "Pensa logicamente ma spesso manca l'essenza di una storia",
        "Di solito l'ultimo a capire una battuta",
        "Rimane bloccato nel comportamento; non riesce a lasciarlo andare",
        "Manca di tatto sociale / antisociale / socialmente isolato",
        "Scarsa gestione del tempo, sempre in ritardo",
        "Disorganizzato",
        "Problema nell'attenzione",
        "È iperattivo e/o impulsivo",
        "Ha pensieri o comportamenti ossessivi",
        "Discute sempre ed è generalmente poco collaborativo",
        "Imita suoni o parole ripetutamente senza capire il significato",
        "Appare annoiato, distaccato e brusco",
        "Considerato strano dagli altri bambini",
        "Incapacità di formare amicizie",
        "Difficoltà a condividere divertimento, interessi o risultati",
        "Comportamento inappropriato o sciocco in situazioni sociali",
        "Parla incessantemente e fa le stesse domande",
    ],
    "Accademiche": [
        "Scarso ragionamento matematico (problemi con le parole, geometria, algebra)",
        "Scarsa comprensione della lettura e capacità pragmatiche",
        "Manca il quadro generale: vede solo le parti",
        "Molto analitico",
        "Prende tutto alla lettera",
        "È molto bravo a trovare errori (ortografia)",
        "Ha iniziato a parlare molto presto",
        "È stato uno dei primi lettori di parole",
        "Impara a memoria (memorizzando)",
        "Parla in modo monotono, poca inflessione",
        "È un cattivo comunicatore non verbale",
        "Non ama i rumori forti (fuochi d'artificio)",
        "Matematica fu la prima materia diventata un problema",
    ],
    "Immunitarie": [
        "Ha molte allergie",
        "Raramente si ammala di raffreddori e infezioni",
        "Ha avuto o ha eczema o asma",
        "Pelle con piccole protuberanze bianche (specialmente dorso delle braccia)",
        "Comportamento irregolare: un giorno buono, il successivo cattivo",
        "Brama certi alimenti, in particolare latticini e prodotti a base di grano",
    ],
    "Autonome": [
        "Problemi intestinali (costipazione e diarrea)",
        "Frequenza cardiaca rapida e/o pressione alta per l'età",
        "Appare gonfio dopo i pasti, lamenta dolori di stomaco",
        "Ha odore corporeo",
        "Suda molto",
        "Le mani sono sempre umide e bagnate",
    ],
}

MELILLO_BAMBINI_SINISTRO = {
    "Motorie": [
        "Problemi motori fini (scrittura a mano scarsa o lenta)",
        "Difficoltà con capacità motorie (abbottonare una camicia)",
        "Presa della mano scarsa o immatura durante la scrittura",
        "Tende a scrivere molto grande per età o grado",
        "Inciampa sulle parole quando è affaticato",
        "Ritardo nel gattonare, stare in piedi e/o camminare",
        "Ama lo sport ed è bravo",
        "Buon tono muscolare",
        "Scarse capacità di disegno",
        "Difficoltà ad imparare a suonare la musica",
        "Difficoltà di pianificazione e coordinamento dei movimenti del corpo",
    ],
    "Sensoriali": [
        "Non sembra avere molti problemi sensoriali",
        "Ha una buona consapevolezza spaziale",
        "Ha un buon senso dell'equilibrio",
        "Mangia praticamente qualsiasi cosa",
        "Ha un senso del gusto e dell'olfatto nella norma o superiore",
        "Ama essere abbracciato e tenuto in braccio",
        "Non ha stranezze riguardo all'abbigliamento",
        "Ha problemi di elaborazione uditiva",
        "Sembra non sentire bene, anche se i test uditivi sono normali",
        "Il ritardo nel parlare è stato attribuito a infezioni dell'orecchio",
    ],
    "Emotive": [
        "Eccessivamente felice e affettuoso; ama abbracciare e baciare",
        "Spesso lunatico e irritabile",
        "Ama fare cose nuove o diverse, ma si annoia facilmente",
        "Manca di motivazione",
        "Ritirato e timido",
        "Eccessivamente cauto, pessimista o negativo",
        "Non sembra trarre piacere dalla vita",
        "Socialmente ritirato",
        "Piange facilmente; i sentimenti vengono feriti facilmente",
        "Empatico verso i sentimenti degli altri",
        "Si imbarazza facilmente",
        "Molto sensibile a cosa pensano gli altri",
    ],
    "Comportamentali": [
        "Procrastina",
        "È estremamente timido, specialmente con gli estranei",
        "Non ha problemi comportamentali a scuola",
        "Comprende le regole sociali",
        "Ha scarsa autostima",
        "Odia fare i compiti",
        "È molto bravo nell'interazione sociale",
        "Stabilisce un buon contatto visivo",
        "Ama stare in mezzo alla gente e gode delle attività sociali",
        "Non gli piace andare ai pigiama party",
        "Non è bravo a seguire le routine",
        "Impossibile seguire indicazioni in più passaggi",
        "Salta alle conclusioni",
    ],
    "Accademiche": [
        "Molto bravo nelle capacità di visione d'insieme",
        "È un pensatore intuitivo guidato dai sentimenti",
        "Bravo nell'associazione astratta libera",
        "Scarse capacità analitiche",
        "Molto visivo; ama le immagini e i modelli",
        "Scarso senso del tempo",
        "Ha problemi a stabilire le priorità",
        "È improbabile che legga le istruzioni prima di provare qualcosa",
        "Lettura errata o omissione di parolette comuni",
        "Ha difficoltà a dire parole lunghe",
        "Si legge molto lentamente e faticosamente",
        "Ha bisogno di ascoltare o vedere concetti molte volte per impararli",
        "Ha mostrato una tendenza al ribasso nei punteggi dei test",
        "Il lavoro scolastico è incoerente",
        "Era un oratore tardivo",
        "Ha difficoltà a pronunciare le parole (scarso con la fonetica)",
        "Aveva difficoltà a imparare l'alfabeto, filastrocche o canzoni",
        "Agisce prima di pensare e commette errori incuranti",
        "Sogna ad occhi aperti molto",
        "Ha difficoltà a sequenziare gli eventi nell'ordine corretto",
        "Spesso scrive lettere al contrario",
        "È scarso nelle operazioni matematiche di base",
        "Ha scarse capacità di memorizzazione",
    ],
    "Immunitarie": [
        "Ottiene infezioni croniche dell'orecchio",
        "Ha assunto antibiotici più di 10-15 volte prima dei 10 anni",
        "Ha avuto tubi messi nelle orecchie",
        "Prende raffreddori frequentemente",
        "Nessuna allergia",
    ],
    "Autonome": [
        "Ha un problema di enuresi notturna",
        "Ha o ha avuto un battito cardiaco irregolare (aritmia o soffio)",
    ],
}


def melillo_bambini_ui(prefix: str, existing: dict | None = None) -> tuple[dict, str]:
    """Melillo Bambini — checklist squilibrio emisferico destro e sinistro."""
    existing = existing or {}
    items_d = existing.get("items_destro", {})
    items_s = existing.get("items_sinistro", {})

    st.markdown("### 🧒 Melillo – Checklist Squilibrio Cerebrale Bambini")
    st.caption(
        "Seleziona le caratteristiche che descrivono il bambino. "
        "Non è necessario che ricadano tutte da un solo lato: "
        "lo squilibrio si rivela quando i risultati si inclinano verso destra o sinistra."
    )

    nuovi_d: dict[str, bool] = {}
    nuovi_s: dict[str, bool] = {}

    tab_d, tab_s = st.tabs(["🔴 Ritardo Cerebrale Destro", "🔵 Ritardo Cerebrale Sinistro"])

    with tab_d:
        tot_d = 0
        for categoria, voci in MELILLO_BAMBINI_DESTRO.items():
            with st.expander(f"**{categoria}**", expanded=False):
                for voce in voci:
                    key = f"{prefix}_D_{categoria[:3]}_{voce[:20]}"
                    val = bool(items_d.get(voce, False))
                    checked = _cb(voce, val, key)
                    nuovi_d[voce] = checked
                    if checked:
                        tot_d += 1
        st.metric("✅ Totale selezionati (Destro)", tot_d)

    with tab_s:
        tot_s = 0
        for categoria, voci in MELILLO_BAMBINI_SINISTRO.items():
            with st.expander(f"**{categoria}**", expanded=False):
                for voce in voci:
                    key = f"{prefix}_S_{categoria[:3]}_{voce[:20]}"
                    val = bool(items_s.get(voce, False))
                    checked = _cb(voce, val, key)
                    nuovi_s[voce] = checked
                    if checked:
                        tot_s += 1
        st.metric("✅ Totale selezionati (Sinistro)", tot_s)

    # Interpretazione
    st.markdown("---")
    if tot_d > tot_s and tot_d > 3:
        st.warning(f"⚠️ Prevalenza caratteristiche **Ritardo Destro** ({tot_d}D vs {tot_s}S)")
    elif tot_s > tot_d and tot_s > 3:
        st.info(f"ℹ️ Prevalenza caratteristiche **Ritardo Sinistro** ({tot_s}S vs {tot_d}D)")
    elif tot_d > 0 or tot_s > 0:
        st.success(f"✅ Profilo misto (Destro: {tot_d} — Sinistro: {tot_s})")

    result = {
        "version": "melillo_bambini_v1",
        "date": date.today().isoformat(),
        "items_destro": nuovi_d,
        "items_sinistro": nuovi_s,
        "scoring": {"tot_destro": tot_d, "tot_sinistro": tot_s},
    }
    summary = f"Melillo Bambini: Destro={tot_d} Sinistro={tot_s}"
    if tot_d > tot_s and tot_d > 3:
        summary += " → prevalenza Destra"
    elif tot_s > tot_d and tot_s > 3:
        summary += " → prevalenza Sinistra"
    return result, summary


# ─────────────────────────────────────────────────────────────────────────────
# 3. FISHER AUDITIVO BAMBINI — 25 item, scoring 4% per item non selezionato
# ─────────────────────────────────────────────────────────────────────────────

FISHER_ITEMS = [
    (1,  "Ha una storia di perdita dell'udito"),
    (2,  "Ha una storia di infezioni dell'orecchio"),
    (3,  "Non presta attenzione alle istruzioni il 50% o più delle volte"),
    (4,  "Non ascolta attentamente le indicazioni, spesso necessario ripetere"),
    (5,  "Dice 'huh' e 'cosa' almeno 5 o più volte al giorno"),
    (6,  "Non riesce ad assistere agli stimoli uditivi per più di pochi secondi"),
    (7,  "Ha un breve intervallo di attenzione"),
    (8,  "Sogna ad occhi aperti, l'attenzione si sposta"),
    (9,  "È facilmente distratto dai suoni di sottofondo"),
    (10, "Ha difficoltà con la fonetica"),
    (11, "Riscontra problemi di discriminazione acustica"),
    (12, "Dimentica ciò che viene detto in pochi minuti"),
    (13, "Non ricorda semplici cose di routine di giorno in giorno"),
    (14, "Ha problemi nel ricordare ciò che ha ascoltato settimane/mesi fa"),
    (15, "Ha difficoltà a ricordare una sequenza ascoltata"),
    (16, "Sperimenta difficoltà a seguire indicazioni uditive"),
    (17, "Spesso fraintende ciò che viene detto"),
    (18, "Non comprende molte parole/concetti verbali per età/grado"),
    (19, "Impara male attraverso il canale uditivo"),
    (20, "Ha un problema linguistico (morfologia, sintassi, vocabolario, fonologia)"),
    (21, "Ha un problema di articolazione (discorso)"),
    (22, "Non riesce sempre a mettere in relazione ciò che sente con ciò che vede"),
    (23, "Manca la motivazione per imparare"),
    (24, "Mostra una risposta lenta o ritardata agli stimoli verbali"),
    (25, "Dimostra prestazioni inferiori alla media in una o più aree accademiche"),
]

FISHER_NORMATIVI = [
    ("Scuola materna", "5.0-5.11", 92.0),
    ("Primo", "6.0-6.11", 89.9),
    ("Secondo", "7.0-7.11", 87.0),
    ("Terzo", "8.0-8.11", 85.6),
    ("Quarto", "9.0-9.11", 85.9),
    ("Quinto", "10.0-10.11", 87.4),
    ("Sesto", "11.0-11.11", 80.0),
]


def fisher_auditivo_bambini_ui(prefix: str, existing: dict | None = None) -> tuple[dict, str]:
    """Fisher Auditory Problems Checklist — Bambini (25 item)."""
    existing = existing or {}
    items_prec = existing.get("items", {})

    st.markdown("### 👂 Elenco di Controllo dei Problemi Uditivi di Fisher – Bambini")
    st.caption(
        "Metti un segno di spunta prima di ogni elemento considerato un problema dall'osservatore. "
        "**Scoring:** 4% per ogni item NON selezionato (max 100%)."
    )

    # Fascia età per confronto normativo
    grado_opts = ["Non specificato"] + [f"{g} ({fa})" for g, fa, _ in FISHER_NORMATIVI]
    grado_sel = st.selectbox("Grado scolastico del bambino", grado_opts,
                              index=grado_opts.index(existing.get("grado", "Non specificato"))
                              if existing.get("grado") in grado_opts else 0,
                              key=f"{prefix}_grado")

    nuovi_items: dict[str, bool] = {}
    selezionati = 0

    with st.expander("📋 25 Item — Problemi Uditivi", expanded=True):
        for num, label in FISHER_ITEMS:
            val = bool(items_prec.get(f"F{num:02d}", False))
            checked = _cb(f"{num}. {label}", val, f"{prefix}_F{num:02d}")
            nuovi_items[f"F{num:02d}"] = checked
            if checked:
                selezionati += 1

    # Scoring Fisher
    non_sel = 25 - selezionati
    punteggio = non_sel * 4  # 4% per item non selezionato
    cutoff = 72.0

    st.markdown("---")
    st.markdown("#### 📊 Risultato Fisher")
    col1, col2 = st.columns(2)
    col1.metric("Item selezionati (problemi)", selezionati)
    col2.metric("Punteggio Fisher", f"{punteggio}%")

    # Confronto normativo
    norm_media = None
    if grado_sel != "Non specificato":
        for g, fa, media in FISHER_NORMATIVI:
            if grado_sel.startswith(g):
                norm_media = media
                break

    if punteggio < cutoff:
        st.error(f"⚠️ Punteggio {punteggio}% < cut-off {cutoff}% → Necessità di ulteriore valutazione")
    elif norm_media and punteggio < norm_media - 18.2:
        st.warning(f"⚠️ Punteggio {punteggio}% — 1 SD sotto la media del gruppo ({norm_media:.1f}%)")
    else:
        st.success(f"✅ Punteggio {punteggio}% — Nella norma")

    # APD classification (Jack Katz)
    apd_dic = [f"F{n:02d}" for n in [5, 10, 11, 17, 18, 21, 24]]
    apd_tfm = [f"F{n:02d}" for n in [6, 7, 9, 12]]
    apd_org = ["F15"]
    apd_int = ["F22"]

    def _apd_count(keys):
        return sum(1 for k in keys if nuovi_items.get(k, False))

    with st.expander("🔍 Classificazione APD (Jack Katz)", expanded=False):
        st.write(f"DIC (discriminazione): {_apd_count(apd_dic)}/7 positivi")
        st.write(f"TFM (figura-terra): {_apd_count(apd_tfm)}/4 positivi")
        st.write(f"ORGANIZZAZIONE: {_apd_count(apd_org)}/1 positivi")
        st.write(f"INT (integrazione): {_apd_count(apd_int)}/1 positivi")

    result = {
        "version": "fisher_bambini_v1",
        "date": date.today().isoformat(),
        "grado": grado_sel,
        "items": nuovi_items,
        "scoring": {
            "selezionati": selezionati,
            "non_selezionati": non_sel,
            "punteggio_pct": punteggio,
            "cutoff": cutoff,
            "flag_valutazione": punteggio < cutoff,
        },
        "apd": {
            "DIC": _apd_count(apd_dic),
            "TFM": _apd_count(apd_tfm),
            "ORGANIZZAZIONE": _apd_count(apd_org),
            "INT": _apd_count(apd_int),
        },
    }
    flag = punteggio < cutoff
    summary = (
        f"Fisher Auditivo Bambini: {selezionati}/25 problemi, punteggio {punteggio}%"
        + (" → SOTTO CUTOFF (valutazione necessaria)" if flag else " → nella norma")
    )
    return result, summary


# ─────────────────────────────────────────────────────────────────────────────
# 4. VISIONE BAMBINI
# ─────────────────────────────────────────────────────────────────────────────

VISIONE_BAMBINI_SINTOMI = [
    ("VB01", "Mal di testa"),
    ("VB02", "Visione sfuocata / il fuoco viene e va"),
    ("VB03", "Visione doppia"),
    ("VB04", "Gli occhi fanno male"),
    ("VB05", "Gli occhi si stancano"),
    ("VB06", "Le parole si muovono nella pagina"),
    ("VB07", "Mal di movimento / mal d'auto"),
    ("VB08", "Capogiro / nausea"),
]

VISIONE_BAMBINI_OSSERVATI = [
    ("VB09", "Gli occhi si arrossano spesso"),
    ("VB10", "Si stropiccia spesso gli occhi"),
    ("VB11", "Orzaioli frequenti"),
    ("VB12", "Infastidito dalla luce"),
    ("VB13", "Sbatte spesso gli occhi"),
    ("VB14", "Chiude o copre un occhio"),
    ("VB15", "Difficoltà a vedere oggetti lontani"),
    ("VB16", "Si avvicina al foglio quando legge o scrive"),
    ("VB17", "Evita la lettura"),
    ("VB18", "Inclina la testa quando legge"),
    ("VB19", "Inclina la testa quando scrive"),
    ("VB20", "Muove la testa quando legge"),
    ("VB21", "Salta le righe oppure le rilegge"),
    ("VB22", "Confonde lettere o parole"),
    ("VB23", "Scrive lettere o parole rovesciate"),
    ("VB24", "Confonde destra e sinistra"),
    ("VB25", "Salta, rilegge, omette parole"),
    ("VB26", "Perde il segno quando legge"),
    ("VB27", "Mormora se deve leggere a mente"),
    ("VB28", "Legge lentamente"),
    ("VB29", "Usa un dito per tenere il segno"),
    ("VB30", "Scarsa comprensione del testo letto"),
    ("VB31", "La comprensione si riduce nel tempo"),
    ("VB32", "Scrive o disegna male"),
    ("VB33", "La grafia è buona ma è lento"),
    ("VB34", "Non tiene il foglio quando scrive"),
    ("VB35", "Impugna male la penna"),
    ("VB36", "Deve cancellare spesso"),
    ("VB37", "Si stanca facilmente"),
    ("VB38", "Lo svolgimento dei compiti richiede più tempo del necessario"),
    ("VB39", "Difficoltà a copiare dalla lavagna"),
    ("VB40", "Difficoltà nel riconoscere la stessa parola in una pagina successiva"),
    ("VB41", "Difficoltà a memorizzare quello che vede"),
    ("VB42", "Ricorda meglio quello che ascolta"),
    ("VB43", "Va meglio nell'orale che nello scritto"),
    ("VB44", "Sembra sapere la lezione, ma va male nelle verifiche"),
    ("VB45", "Evita o non ama i compiti svolti da vicino"),
    ("VB46", "Periodo d'attenzione breve / perde interesse"),
    ("VB47", "Scarsa coordinazione motoria generale"),
    ("VB48", "Scarsa coordinazione motoria fine"),
    ("VB49", "Difficoltà con forbici o altri piccoli utensili"),
    ("VB50", "Evita o non ama gli sport"),
    ("VB51", "Ha difficoltà nel prendere o colpire una palla"),
]

VISIONE_BAMBINI_SVILUPPO = [
    ("VS01", "Ha saltato i periodi di carpone e striscio"),
    ("VS02", "Ritardo nell'imparare a camminare (16 mesi o più tardi)"),
    ("VS03", "Ritardo nell'imparare a parlare (frasi di due parole a 18 mesi o più)"),
    ("VS04", "Difficoltà nell'imparare ad allacciarsi le scarpe o a vestirsi"),
    ("VS05", "Difficoltà per imparare a leggere"),
    ("VS06", "Difficoltà per imparare a scrivere / transizione al corsivo"),
    ("VS07", "Difficoltà per imparare ad andare in bicicletta"),
    ("VS08", "Difficoltà nel prendere una palla al volo"),
    ("VS09", "Soffre di mal d'auto"),
    ("VS10", "Povera orientazione spaziale / destra e sinistra"),
    ("VS11", "Difficoltà ad identificare l'ora da orologio analogico"),
    ("VS12", "Frequenti problemi d'udito, naso e gola"),
    ("VS13", "Soffre di allergie (asma, eczema, febbre da fieno, orticaria)"),
    ("VS14", "Difficoltà a rimanere seduto e mantenere l'attenzione"),
    ("VS15", "Intorno ai 7/8 o 12/13 anni: frequenti o forti mal di testa"),
    ("VS16", "Problemi di linguaggio che si manifestano di più quando stanco o stressato"),
]


def visione_bambini_ui(prefix: str, existing: dict | None = None) -> tuple[dict, str]:
    """Questionario per la Visione del Bambino (fino a 11-12 anni)."""
    existing = existing or {}
    items = existing.get("items", {})

    st.markdown("### 👁️ Questionario per la Visione del/la Bambino/a")
    st.caption("Compilate il questionario. Selezionate tutti i sintomi o problemi presenti.")

    nuovi: dict[str, bool] = {}

    with st.expander("🔴 Sintomi lamentati dal bambino", expanded=True):
        for code, label in VISIONE_BAMBINI_SINTOMI:
            nuovi[code] = _cb(label, bool(items.get(code, False)), f"{prefix}_{code}")

    with st.expander("👀 Problemi osservati dai genitori", expanded=False):
        for code, label in VISIONE_BAMBINI_OSSERVATI:
            nuovi[code] = _cb(label, bool(items.get(code, False)), f"{prefix}_{code}")

    with st.expander("📋 Questionario breve ritardi sviluppo", expanded=False):
        for code, label in VISIONE_BAMBINI_SVILUPPO:
            nuovi[code] = _cb(label, bool(items.get(code, False)), f"{prefix}_{code}")

    tot = sum(1 for v in nuovi.values() if v)
    st.markdown("---")
    st.metric("Totale elementi selezionati", tot)

    if tot >= 15:
        st.warning(f"⚠️ {tot} elementi selezionati — si consiglia valutazione optometrica comportamentale completa")
    elif tot >= 7:
        st.info(f"ℹ️ {tot} elementi selezionati — possibili difficoltà visuo-motorie da approfondire")
    elif tot > 0:
        st.success(f"✅ {tot} elementi selezionati — pochi elementi, monitorare")

    result = {
        "version": "visione_bambini_v1",
        "date": date.today().isoformat(),
        "items": nuovi,
        "scoring": {"totale": tot},
    }
    summary = f"Visione Bambini: {tot} elementi selezionati"
    if tot >= 15:
        summary += " → valutazione optometrica consigliata"
    elif tot >= 7:
        summary += " → difficoltà visuo-motorie da approfondire"
    return result, summary


# ─────────────────────────────────────────────────────────────────────────────
# 5. VISIONE ADULTI
# ─────────────────────────────────────────────────────────────────────────────

VISIONE_ADULTI_SINTOMI = [
    ("VA01", "Visione sfuocata da lontano"),
    ("VA02", "Visione sfuocata da vicino"),
    ("VA03", "Orzaioli ricorrenti"),
    ("VA04", "Gli occhi prudono e sono rossi"),
    ("VA05", "Gli occhi bruciano"),
    ("VA06", "Gli occhi fanno male"),
    ("VA07", "Gli occhi si stancano"),
    ("VA08", "Le parole si muovono nella pagina"),
    ("VA09", "Capogiro / nausea con i lavori da vicino"),
    ("VA10", "Aloni intorno alle luci"),
    ("VA11", "Visione doppia da lontano"),
    ("VA12", "Visione doppia da vicino"),
    ("VA13", "Inclina la testa quando legge o scrive"),
    ("VA14", "Chiude o copre un occhio"),
    ("VA15", "Postura alterata quando legge/scrive"),
    ("VA16", "Bisogno di molta luce per leggere"),
    ("VA17", "Preferisce poca luce per leggere"),
    ("VA18", "Perde interesse / poca concentrazione"),
    ("VA19", "Difficoltà a sostenere lettura / scrittura"),
    ("VA20", "Fatica visiva / generale a fine giornata"),
    ("VA21", "Perde il segno quando legge"),
    ("VA22", "Salta le righe quando legge"),
    ("VA23", "Rilegge lettere o parole"),
    ("VA24", "Omette parole quando legge/copia"),
    ("VA25", "Usa un dito per tenere il segno"),
    ("VA26", "Muove la testa quando legge"),
    ("VA27", "Confonde quello che ha visto / letto"),
    ("VA28", "Sonnolenza quando legge"),
    ("VA29", "Mormora/muove le labbra se legge a mente"),
    ("VA30", "Mal d'auto / cinetosi"),
    ("VA31", "Ridotta comprensione del testo letto"),
    ("VA32", "La comprensione si riduce nel tempo"),
    ("VA33", "Le parole fluttuano nella pagina"),
    ("VA34", "Difficoltà ad incolonnare i numeri"),
    ("VA35", "Va meglio nell'orale che nello scritto"),
    ("VA36", "Scrive o disegna male"),
    ("VA37", "Cattiva gestione del tempo"),
    ("VA38", "Rendimento altalenante (lavoro / sport)"),
    ("VA39", "Scarsa coordinazione generale – goffo"),
    ("VA40", "Scarsa coordinazione motoria fine"),
    ("VA41", "Problemi di memoria a breve termine"),
    ("VA42", "Problemi di memoria a lungo termine"),
]

VISIONE_ADULTI_ANAMNESI = [
    ("AM01", "Diabete (familiare o personale)"),
    ("AM02", "Glaucoma (familiare o personale)"),
    ("AM03", "Strabismo (familiare o personale)"),
    ("AM04", "Occhio pigro (familiare o personale)"),
    ("AM05", "Pressione sangue alta (familiare o personale)"),
    ("AM06", "Ipo/Iper-tiroidismo (familiare o personale)"),
    ("AM07", "Cataratta (familiare o personale)"),
    ("AM08", "Sclerosi Multipla (familiare o personale)"),
]


def visione_adulti_ui(prefix: str, existing: dict | None = None) -> tuple[dict, str]:
    """Questionario per la Visione dell'Adulto."""
    existing = existing or {}
    items = existing.get("items", {})

    st.markdown("### 👁️ Questionario per la Visione dell'Adulto")
    st.caption("Selezionate i sintomi presenti. I dati vengono salvati nel profilo PNEV del paziente.")

    nuovi: dict[str, bool] = {}

    with st.expander("🔴 Sintomi visivi presenti", expanded=True):
        for code, label in VISIONE_ADULTI_SINTOMI:
            nuovi[code] = _cb(label, bool(items.get(code, False)), f"{prefix}_{code}")

    with st.expander("🏥 Anamnesi patologie (paziente/familiari)", expanded=False):
        for code, label in VISIONE_ADULTI_ANAMNESI:
            nuovi[code] = _cb(label, bool(items.get(code, False)), f"{prefix}_{code}")

    # Campi testo libero
    st.markdown("---")
    occupazione = st.text_input(
        "Occupazione / lavoro prevalente",
        value=existing.get("occupazione", ""),
        key=f"{prefix}_occupazione",
    )
    ore_pc = st.number_input(
        "Ore/giorno al videoterminale",
        min_value=0, max_value=24, step=1,
        value=int(existing.get("ore_pc", 0)),
        key=f"{prefix}_ore_pc",
    )
    note = st.text_area(
        "Note aggiuntive / altri disturbi",
        value=existing.get("note", ""),
        height=70,
        key=f"{prefix}_note",
    )

    tot_sintomi = sum(1 for k, v in nuovi.items() if k.startswith("VA") and v)
    tot_anamn = sum(1 for k, v in nuovi.items() if k.startswith("AM") and v)
    tot = tot_sintomi + tot_anamn

    st.metric("Sintomi visivi selezionati", tot_sintomi)

    if tot_sintomi >= 12:
        st.warning(f"⚠️ {tot_sintomi} sintomi visivi — valutazione optometrica comportamentale raccomandata")
    elif tot_sintomi >= 6:
        st.info(f"ℹ️ {tot_sintomi} sintomi visivi — possibili disfunzioni visuo-motorie")
    elif tot_sintomi > 0:
        st.success(f"✅ {tot_sintomi} sintomi — monitorare")

    result = {
        "version": "visione_adulti_v1",
        "date": date.today().isoformat(),
        "items": nuovi,
        "occupazione": occupazione,
        "ore_pc": ore_pc,
        "note": note,
        "scoring": {"tot_sintomi": tot_sintomi, "tot_anamnesi": tot_anamn},
    }
    summary = f"Visione Adulti: {tot_sintomi} sintomi visivi"
    if tot_sintomi >= 12:
        summary += " → valutazione optometrica raccomandata"
    elif tot_sintomi >= 6:
        summary += " → disfunzioni visuo-motorie possibili"
    return result, summary


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT — render_questionari_pnev()
# Può essere chiamato da app_core.py con un tab per ogni questionario
# ─────────────────────────────────────────────────────────────────────────────

def render_questionari_pnev(
    pnev_json: dict,
    prefix: str,
    fascia_eta: str = "bambino",   # "bambino" | "adulto"
    readonly: bool = False,
) -> tuple[dict, str]:
    """
    Entry point principale.
    Mostra tutti i questionari disponibili in tabs.
    fascia_eta: 'bambino' o 'adulto'
    Ritorna (pnev_json aggiornato, summary_globale).
    """
    if pnev_json is None:
        pnev_json = {}
    q = pnev_json.setdefault("questionari", {})

    summaries = []

    if fascia_eta == "adulto":
        tab_mel_a, tab_vis_a = st.tabs([
            "🧠 Melillo Adulti",
            "👁️ Visione Adulti",
        ])
        with tab_mel_a:
            data, s = melillo_adulti_ui(f"{prefix}_mela", q.get("melillo_adulti"))
            q["melillo_adulti"] = data; summaries.append(s)
        with tab_vis_a:
            data, s = visione_adulti_ui(f"{prefix}_visa", q.get("visione_adulti"))
            q["visione_adulti"] = data; summaries.append(s)

    else:  # bambino
        tab_mel_b, tab_fish, tab_vis_b = st.tabs([
            "🧒 Melillo Bambini",
            "👂 Fisher Auditivo",
            "👁️ Visione Bambini",
        ])
        with tab_mel_b:
            data, s = melillo_bambini_ui(f"{prefix}_melb", q.get("melillo_bambini"))
            q["melillo_bambini"] = data; summaries.append(s)
        with tab_fish:
            data, s = fisher_auditivo_bambini_ui(f"{prefix}_fish", q.get("fisher_auditivo_bambini"))
            q["fisher_auditivo_bambini"] = data; summaries.append(s)
        with tab_vis_b:
            data, s = visione_bambini_ui(f"{prefix}_visb", q.get("visione_bambini"))
            q["visione_bambini"] = data; summaries.append(s)

    pnev_json["questionari"] = q
    summary_globale = " | ".join(summaries)
    return pnev_json, summary_globale
