"""Состояния окна «СК проекта» для scripts/ui_snap.py навыка qgis-ui-review.

Запуск: ~/.claude/skills/qgis-plugin/scripts/qgis_env.sh -- \
            python ~/.claude/skills/qgis-ui-review/scripts/ui_snap.py tests/ui_shots.py

Ответ Nominatim подменяется: снимки должны получаться одинаковыми и без сети.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN_ROOT = os.path.dirname(HERE)
sys.path.insert(0, PLUGIN_ROOT)

from qgis.core import QgsCoordinateReferenceSystem, QgsRectangle       # noqa: E402
from qgis.gui import QgsMapCanvas                                      # noqa: E402
from qgis.PyQt.QtWidgets import QMainWindow                            # noqa: E402


class Iface:
    """Минимальный iface: окну нужны только главное окно и холст."""

    def __init__(self, rect):
        self.window = QMainWindow()
        self.canvas = QgsMapCanvas(self.window)
        self.canvas.setDestinationCrs(QgsCoordinateReferenceSystem("EPSG:4326"))
        self.canvas.setExtent(rect)

    def mainWindow(self):
        return self.window

    def mapCanvas(self):
        return self.canvas

    def messageBar(self):
        return None


def answer(iso, state, country="Россия", code="ru"):
    return {"address": {"ISO3166-2-lvl4": iso, "state": state,
                        "country": country, "country_code": code}}


def windows():
    from project_utm_crs import msk
    from project_utm_crs.dialog import CrsDialog

    ROSTOV = QgsRectangle(39.6, 47.1, 39.8, 47.3)      # МСК субъекта есть
    KHERSON = QgsRectangle(32.5, 46.5, 32.7, 46.7)     # МСК нет — зоны СК-63

    def filled(rect, reverse):
        def make():
            msk.reverse_geocode = reverse
            return CrsDialog(Iface(rect))
        return make

    def shown(rect, reverse):
        def make():
            dlg = filled(rect, reverse)()
            dlg.refresh()
            return dlg
        return make

    msk_ok = lambda lon, lat: (answer("RU-ROS", "Ростовская область"), None)          # noqa: E731
    abroad = lambda lon, lat: (answer("UA-65", "Херсонська область", "Украина", "ua"), None)  # noqa: E731
    offline = lambda lon, lat: (None, "Нет связи с OpenStreetMap.")                   # noqa: E731

    return [
        ("окно_до_определения", filled(ROSTOV, msk_ok)),
        ("окно_с_мск", shown(ROSTOV, msk_ok)),
        ("окно_с_ск63", shown(KHERSON, abroad)),
        ("окно_без_сети", shown(ROSTOV, offline)),
    ]
