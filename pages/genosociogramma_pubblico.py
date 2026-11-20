"""Vecchio link alla pagina «genosociogramma_pubblico»: porta alla stessa pagina sul nuovo indirizzo."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _vai import vai

vai("genosociogramma_pubblico")
