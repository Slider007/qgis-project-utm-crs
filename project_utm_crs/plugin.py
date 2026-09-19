import os

from qgis.PyQt.QtGui import QIcon

from . import altan_toolbar

try:  # Qt6 / QGIS 4: QAction живёт в QtGui
    from qgis.PyQt.QtGui import QAction
except ImportError:  # Qt5 / QGIS 3
    from qgis.PyQt.QtWidgets import QAction

PLUGIN_DIR = os.path.dirname(__file__)


class ProjectUtmCrsPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.action = None
        self.dialog = None

    def initGui(self):
        self.action = QAction(
            QIcon(os.path.join(PLUGIN_DIR, "icon.svg")),
            "СК проекта по центру карты (UTM, МСК)…",
            self.iface.mainWindow(),
        )
        self.action.setToolTip(
            "Зона UTM и местные системы координат (МСК) для центра карты; "
            "выбранную можно назначить проекту")
        self.action.triggered.connect(self.run)
        altan_toolbar.add_action(self.iface, self.action)
        altan_toolbar.add_to_menu(self.iface, self.action)

    def unload(self):
        if self.action:
            altan_toolbar.remove_from_menu(self.iface, self.action)
            altan_toolbar.remove_action(self.iface, self.action)
            self.action.deleteLater()
            self.action = None
        if self.dialog:
            self.dialog.close()
            self.dialog.deleteLater()
            self.dialog = None

    def run(self):
        # Импорт внутри метода: окно не нужно в headless-режиме
        from .dialog import CrsDialog

        if self.dialog is None:
            self.dialog = CrsDialog(self.iface, self.iface.mainWindow())
        # немодальное окно: повторный вызов поднимает то же окно
        self.dialog.show()
        self.dialog.raise_()
        self.dialog.activateWindow()
        self.dialog.refresh()
