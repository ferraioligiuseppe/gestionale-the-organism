"""Vecchio link alla pagina «iscrizione_evento»: porta alla stessa pagina sul nuovo indirizzo."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _vai import vai

vai("iscrizione_evento")
