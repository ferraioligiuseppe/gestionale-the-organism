from __future__ import annotations


def _src():
    from modules import ui_lenti_contatto as src
    return src


def parse_xyz_file(file_obj):
    return _src()._parse_xyz_file(file_obj)


def parse_csv_topographer(file_obj):
    return _src()._parse_csv_topographer(file_obj)


def parse_zcs_file(file_obj):
    return _src()._parse_zcs_file(file_obj)


def parse_any_topo(file_obj):
    return _src()._parse_any_topo(file_obj)
