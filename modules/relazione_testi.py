# -*- coding: utf-8 -*-
"""Testi standard per le relazioni: intro PNEV (in testa) + bibliografia (in coda)."""
import textwrap

_INTRO = [
    "Lo Studio The Organism adotta un modello di lavoro multidisciplinare e integrato (PNEV), "
    "avvalendosi della collaborazione di professionisti appartenenti a diverse aree specialistiche, "
    "tra cui neuropsicologia, logopedia, terapia miofunzionale, psicomotricità, osteopatia, "
    "dietistica, oftalmologia, optometria, posturologia, fisioterapia e odontoiatria.",
    "Tale approccio consente una lettura complessa e unitaria del funzionamento sensorimotorio, "
    "neuropsicomotorio e neuroevolutivo della persona, bambino o adulto, al fine di individuare "
    "eventuali fragilità, disarmonie o rallentamenti nei processi di sviluppo e di integrazione "
    "funzionale. In base agli esiti della valutazione viene quindi formulato un intervento "
    "terapeutico multidisciplinare e multisensoriale, personalizzato sui bisogni del singolo, "
    "articolato in setting individuali e/o di gruppo, volto a sostenere i processi di "
    "organizzazione, regolazione e integrazione delle funzioni neurosensoriali, motorie e relazionali.",
    "PNEV by The Organism è un Metodo Psico-Neuro-Evolutivo Integrato, multidisciplinare e "
    "multisensoriale, finalizzato alla valutazione e al trattamento delle fragilità del "
    "funzionamento neuroevolutivo, sensorimotorio e neuropsicomotorio nel bambino e nell'adulto ©.",
]

_BIBLIO = [
    "Castagnini M. I disturbi dello sviluppo neuro e psicomotorio del bambino: diagnosi e terapia. Con particolare riferimento alle paralisi cerebrali infantili. Verona: Tipolitografia Don Calabria; 2002.",
    "Fiorentino MR. Reflex Testing Methods for Evaluating C.N.S. Development. Springfield (IL): Thomas; 1963.",
    "Fiorentino MR. Reflex Testing Methods for Evaluating C.N.S. Development. 2nd ed. Springfield (IL): Thomas; 1973.",
    "Ayres AJ, Robbins J. Sensory Integration and the Child: Understanding Hidden Sensory Challenges. Rev ed. Los Angeles: Western Psychological Services; 2005.",
    "Schaaf RC, Miller LJ. Occupational therapy using a sensory integrative approach for children with developmental disabilities. Ment Retard Dev Disabil Res Rev. 2005;11(2):143-148.",
    "Parham LD, Smith Roley S, May-Benson TA, Koomar J, Brett-Green B, Burke JP, et al. Development of a fidelity measure for research on the effectiveness of the Ayres Sensory Integration intervention. Am J Occup Ther. 2011;65(2):133-142. doi:10.5014/ajot.2011.000745.",
    "Schaaf RC, Dumont RL, Arbesman M, May-Benson TA. Efficacy of occupational therapy using Ayres Sensory Integration®: A systematic review. Am J Occup Ther. 2018;72(1):7201190010p1-7201190010p10.",
    "Schoen SA, Lane SJ, Mailloux Z, May-Benson T, Parham LD, Smith Roley S, Schaaf RC. A systematic review of Ayres Sensory Integration intervention for children with autism. Autism Res. 2019;12(1):6-19. doi:10.1002/aur.2046.",
    "Scheiman M, Wick B. Clinical Management of Binocular Vision: Heterophoric, Accommodative, and Eye Movement Disorders. 4th ed. Philadelphia: Lippincott Williams & Wilkins; 2014.",
    "Scheiman M, Mitchell GL, Cotter S, Cooper J, Kulp M, Rouse M, et al. A randomized clinical trial of treatments for convergence insufficiency in children. Arch Ophthalmol. 2005;123(1):14-24.",
    "Convergence Insufficiency Treatment Trial Study Group. Randomized clinical trial of treatments for symptomatic convergence insufficiency in children. Arch Ophthalmol. 2008;126(10):1336-1349.",
    "Näätänen R. Attention and Brain Function. Hillsdale (NJ): Lawrence Erlbaum Associates; 1992.",
    "Cheour M, Leppänen PH, Kraus N. Mismatch negativity (MMN) as a tool for investigating auditory discrimination and sensory memory in infants and children. Clin Neurophysiol. 2000;111(1):4-16. doi:10.1016/S1388-2457(99)00191-1.",
    "Garrido MI, Kilner JM, Stephan KE, Friston KJ. The mismatch negativity: a review of underlying mechanisms. Clin Neurophysiol. 2009;120(3):453-463. doi:10.1016/j.clinph.2008.11.029.",
    "Hirose Y, Kakigi R, Hoshiyama M, Kuroda Y. Changes in the duration and frequency of deviant stimuli engender different mismatch negativity patterns in temporal lobe epilepsy. Epilepsy Behav. 2014;31:136-142. doi:10.1016/j.yebeh.2013.11.026.",
    "Coppola G, Toro A, Operto FF, Ferraioli G, Pisano S, Viggiano A, Verrotti A. Mozart's music in children with drug-refractory epileptic encephalopathies. Epilepsy Behav. 2015;50:18-22. doi:10.1016/j.yebeh.2015.05.038.",
    "Coppola G, Operto FF, Caprio F, Ferraioli G, Pisano S, Viggiano A, Verrotti A. Mozart's music in children with drug-refractory epileptic encephalopathies: Comparison of two protocols. Epilepsy Behav. 2018;78:100-103. doi:10.1016/j.yebeh.2017.09.028.",
]


def intro_pnev() -> str:
    out = "### Relazione clinica completa\n"
    for p in _INTRO:
        out += "\n".join(textwrap.wrap(p, 100)) + "\n\n"
    return out


def bibliografia() -> str:
    out = "### Bibliografia\n"
    for i, r in enumerate(_BIBLIO, 1):
        out += "\n".join(textwrap.wrap(f"{i}. {r}", 100)) + "\n"
    return out
