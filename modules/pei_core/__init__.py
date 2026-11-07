"""pei_core — PEI, Profilo Dinamico Funzionale, DF, PF e allegati PDF.
Nucleo comune a gestionale The Organism e TFA Manager."""
from .schema import SCHEMA_VERSION, TIPI_DOCUMENTO
from .model import Documento, precompila_sezione2, controlla_anonimato
from .icf import riporta_nel_pei, controlla_icf
from .pdf_io import genera_pdf, leggi_allegato, unisci_pdf

__all__ = ["SCHEMA_VERSION", "TIPI_DOCUMENTO", "Documento", "precompila_sezione2",
           "controlla_anonimato", "riporta_nel_pei", "controlla_icf", "genera_pdf", "leggi_allegato", "unisci_pdf"]
