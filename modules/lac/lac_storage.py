from __future__ import annotations
from typing import Any


def _src():
    from modules import ui_lenti_contatto as src
    return src


def get_conn():
    return _src()._get_conn()


def init_db(conn) -> None:
    return _src().init_lenti_contatto_db(conn)


def build_payload(paziente_id, data_scheda, occhio, operatore, eye_input, proposta) -> dict:
    return dict(_src()._build_payload(paziente_id, data_scheda, occhio, operatore, eye_input, proposta))


def load_storico_paziente(conn, paziente_id: int):
    return _src().load_storico_paziente(conn, paziente_id)
