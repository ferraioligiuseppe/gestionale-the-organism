"""
Modulo Genetica PNEV · checklist del volto (morfologia facciale).

I segni si valutano a vista, sulla persona o sulle foto standardizzate (frontale e profilo).
Ogni voce è un termine HPO verificato sui dati del modulo (release 2026-09-01).
Le etichette sono in italiano clinico; tra parentesi il termine inglese HPO per chi scrive al genetista.
I segni già presenti nella tabella ponte (area «Volto e corpo»: asimmetria facciale, palato alto,
retrognazia, micro/macrocefalia, ipertelorismo…) non sono ripetuti qui.

Nessuna analisi automatica della foto: la valutazione è sempre del clinico.
"""

# (gruppo, codice HPO, etichetta italiana, termine inglese HPO)
VOLTO = [
    # Cranio e forma del viso
    ("Cranio e forma del viso", "HP:0000248", "Brachicefalia (testa corta e larga)", "Brachycephaly"),
    ("Cranio e forma del viso", "HP:0000268", "Dolicocefalia (testa lunga e stretta)", "Dolichocephaly"),
    ("Cranio e forma del viso", "HP:0001357", "Plagiocefalia", "Plagiocephaly"),
    ("Cranio e forma del viso", "HP:0002007", "Bozze frontali prominenti", "Frontal bossing"),
    ("Cranio e forma del viso", "HP:0000348", "Fronte alta", "High forehead"),
    ("Cranio e forma del viso", "HP:0000341", "Fronte stretta", "Narrow forehead"),
    ("Cranio e forma del viso", "HP:0000294", "Attaccatura anteriore dei capelli bassa", "Low anterior hairline"),
    ("Cranio e forma del viso", "HP:0000311", "Viso rotondo", "Round face"),
    ("Cranio e forma del viso", "HP:0000276", "Viso lungo", "Long face"),
    ("Cranio e forma del viso", "HP:0000325", "Viso triangolare", "Triangular face"),
    ("Cranio e forma del viso", "HP:0012368", "Viso piatto", "Flat face"),
    ("Cranio e forma del viso", "HP:0011800", "Ipoplasia/retrusione del terzo medio", "Midface retrusion"),
    ("Cranio e forma del viso", "HP:0000293", "Guance piene", "Full cheeks"),
    ("Cranio e forma del viso", "HP:0000280", "Tratti del viso grossolani", "Coarse facial features"),

    # Occhi e sopracciglia
    ("Occhi e sopracciglia", "HP:0000601", "Ipotelorismo (occhi ravvicinati)", "Hypotelorism"),
    ("Occhi e sopracciglia", "HP:0000582", "Rime palpebrali rivolte verso l'alto", "Upslanted palpebral fissure"),
    ("Occhi e sopracciglia", "HP:0000494", "Rime palpebrali rivolte verso il basso", "Downslanted palpebral fissures"),
    ("Occhi e sopracciglia", "HP:0012745", "Rime palpebrali corte", "Short palpebral fissure"),
    ("Occhi e sopracciglia", "HP:0000286", "Epicanto", "Epicanthus"),
    ("Occhi e sopracciglia", "HP:0000508", "Ptosi palpebrale", "Ptosis"),
    ("Occhi e sopracciglia", "HP:0000629", "Pienezza periorbitale", "Periorbital fullness"),
    ("Occhi e sopracciglia", "HP:0000527", "Ciglia lunghe", "Long eyelashes"),
    ("Occhi e sopracciglia", "HP:0000574", "Sopracciglia folte", "Thick eyebrow"),
    ("Occhi e sopracciglia", "HP:0002553", "Sopracciglia molto arcuate", "Highly arched eyebrow"),
    ("Occhi e sopracciglia", "HP:0000664", "Sinofria (sopracciglia unite)", "Synophrys"),

    # Naso e filtro
    ("Naso e filtro", "HP:0005280", "Radice del naso depressa (piatta)", "Depressed nasal bridge"),
    ("Naso e filtro", "HP:0000431", "Radice del naso larga", "Wide nasal bridge"),
    ("Naso e filtro", "HP:0003196", "Naso corto", "Short nose"),
    ("Naso e filtro", "HP:0000445", "Naso largo", "Wide nose"),
    ("Naso e filtro", "HP:0000414", "Naso bulboso", "Bulbous nose"),
    ("Naso e filtro", "HP:0000463", "Narici antiverse (rivolte in avanti)", "Anteverted nares"),
    ("Naso e filtro", "HP:0000343", "Filtro lungo", "Long philtrum"),
    ("Naso e filtro", "HP:0000322", "Filtro corto", "Short philtrum"),
    ("Naso e filtro", "HP:0000319", "Filtro liscio (appiattito)", "Smooth philtrum"),

    # Bocca, labbra e denti
    ("Bocca, labbra e denti", "HP:0000154", "Bocca larga", "Wide mouth"),
    ("Bocca, labbra e denti", "HP:0000160", "Bocca piccola/stretta", "Narrow mouth"),
    ("Bocca, labbra e denti", "HP:0002714", "Angoli della bocca rivolti in basso", "Downturned corners of mouth"),
    ("Bocca, labbra e denti", "HP:0000194", "Bocca abitualmente aperta", "Open mouth"),
    ("Bocca, labbra e denti", "HP:0012471", "Labbra spesse (vermiglio spesso)", "Thick vermilion border"),
    ("Bocca, labbra e denti", "HP:0000219", "Labbro superiore sottile", "Thin upper lip vermilion"),
    ("Bocca, labbra e denti", "HP:0000179", "Labbro inferiore spesso", "Thick lower lip vermilion"),
    ("Bocca, labbra e denti", "HP:0000158", "Macroglossia (lingua grande)", "Macroglossia"),
    ("Bocca, labbra e denti", "HP:0000687", "Denti distanziati (diastemi)", "Widely spaced teeth"),
    ("Bocca, labbra e denti", "HP:0000212", "Ipertrofia gengivale", "Gingival overgrowth"),

    # Mento e mandibola
    ("Mento e mandibola", "HP:0000347", "Micrognazia (mandibola piccola)", "Micrognathia"),
    ("Mento e mandibola", "HP:0000331", "Mento corto", "Short chin"),
    ("Mento e mandibola", "HP:0000303", "Prognatismo mandibolare", "Mandibular prognathia"),

    # Orecchie
    ("Orecchie", "HP:0000369", "Orecchie a basso impianto", "Low-set ears"),
    ("Orecchie", "HP:0000358", "Orecchie ruotate posteriormente", "Posteriorly rotated ears"),
    ("Orecchie", "HP:0000411", "Orecchie sporgenti (a ventola)", "Protruding ear"),
    ("Orecchie", "HP:0000400", "Orecchie grandi (macrotia)", "Macrotia"),
    ("Orecchie", "HP:0008551", "Orecchie piccole (microtia)", "Microtia"),
    ("Orecchie", "HP:0000377", "Padiglione auricolare di forma anomala", "Abnormal pinna morphology"),
    ("Orecchie", "HP:0000384", "Appendice cutanea preauricolare", "Preauricular skin tag"),
]

GRUPPI = list(dict.fromkeys(g for g, *_ in VOLTO))

# Viste fotografiche standard (come in dismorfologia clinica)
VISTE = ["Frontale", "Profilo destro", "Profilo sinistro", "Tre quarti", "Orecchio", "Altro"]
