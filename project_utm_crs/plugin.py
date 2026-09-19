import os

from qgis.core import Qgis, QgsProject
from qgis.PyQt.QtGui import QIcon

from . import altan_toolbar, utm

try:  # Qt6 / QGIS 4: QAction живёт в QtGui
    from qgis.PyQt.QtGui import QAction
except ImportError:  # Qt5 / QGIS 3
    from qgis.PyQt.QtWidgets import QAction

PLUGIN_DIR = os.path.dirname(__file__)
TITLE = "UTM"


class ProjectUtmCrsPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.action = None

    def initGui(self):
        self.action = QAction(
            QIcon(os.path.join(PLUGIN_DIR, "icon.svg")),
            "СК проекта — UTM по центру карты",
            self.iface.mainWindow(),
        )
        self.action.setToolTip(
            "Установить системе координат проекта зону UTM (WGS 84), "
            "в которую попадает центр карты")
        self.action.triggered.connect(self.run)
        altan_toolbar.add_action(self.iface, self.action)
        altan_toolbar.add_to_menu(self.iface, self.action)

    def unload(self):
        if self.action:
            altan_toolbar.remove_from_menu(self.iface, self.action)
            altan_toolbar.remove_action(self.iface, self.action)
            self.action.deleteLater()
            self.action = None

    def run(self):
        canvas = self.iface.mapCanvas()
        settings = canvas.mapSettings()
        project = QgsProject.instance()
        crs, error = utm.crs_for_point(
            canvas.extent().center(), settings.destinationCrs(), project.transformContext())
        bar = self.iface.messageBar()
        if crs is None:
            bar.pushMessage(TITLE, error, Qgis.MessageLevel.Warning, 6)
            return
        name = "{} ({})".format(crs.description(), crs.authid())
        if project.crs() == crs:
            bar.pushMessage(TITLE, "СК проекта уже " + name, Qgis.MessageLevel.Info, 4)
            return
        project.setCrs(crs)
        bar.pushMessage(TITLE, "СК проекта: " + name, Qgis.MessageLevel.Success, 4)
