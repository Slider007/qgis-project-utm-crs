"""Проверки модуля без интерфейса QGIS. Запуск: tests/run_tests.sh

Настройки QGIS уводятся во временный профиль tests/_profile.
"""

import os
import shutil
import sys
import unittest
import warnings

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from qgis.PyQt.QtCore import QCoreApplication, QSettings  # noqa: E402

PROFILE = os.path.join(HERE, "_profile")
shutil.rmtree(PROFILE, ignore_errors=True)
QSettings.setDefaultFormat(QSettings.Format.IniFormat)
QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, PROFILE)
QCoreApplication.setOrganizationName("project-utm-crs-tests")
QCoreApplication.setApplicationName("project-utm-crs-tests")

from qgis.core import (  # noqa: E402
    Qgis,
    QgsApplication,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsCoordinateTransformContext,
    QgsPointXY,
    QgsProject,
    QgsRectangle,
)
from qgis.gui import QgsMapCanvas  # noqa: E402
from qgis.PyQt import sip  # noqa: E402
from qgis.PyQt.QtCore import QEvent  # noqa: E402
from qgis.PyQt.QtWidgets import QMainWindow, QMenu, QToolBar  # noqa: E402

app = QgsApplication([], True, PROFILE)
if os.environ.get("QGIS_PREFIX_PATH"):
    app.setPrefixPath(os.environ["QGIS_PREFIX_PATH"], True)
app.initQgis()
# initQgis() переносит настройки в профиль default организации: возвращаем во временный
QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, PROFILE)
assert QSettings().fileName().startswith(PROFILE), QSettings().fileName()

with warnings.catch_warnings():
    warnings.simplefilter("error", DeprecationWarning)
    import project_utm_crs  # noqa: E402
    from project_utm_crs import utm  # noqa: E402

CTX = QgsCoordinateTransformContext()


class ZoneTest(unittest.TestCase):
    def test_known_points(self):
        cases = [
            ((37.62, 55.75), 32637, "Москва"),
            ((82.92, 55.03), 32644, "Новосибирск"),
            ((30.32, 59.94), 32636, "Санкт-Петербург"),
            ((135.07, 48.48), 32653, "Хабаровск"),
            ((-58.38, -34.60), 32721, "Буэнос-Айрес"),
            ((151.21, -33.87), 32756, "Сидней"),
            ((-0.13, 51.51), 32630, "Лондон"),
            ((0.0, 0.0), 32631, "0°, 0°"),
            ((36.0, 50.0), 32637, "граница зон 36/37"),
            ((-180.0, 10.0), 32601, "180° з. д."),
            ((180.0, 10.0), 32601, "180° в. д. = 180° з. д."),
            ((179.99, 10.0), 32660, "зона 60"),
            ((5.32, 60.39), 32632, "Берген: исключение, зона 32"),
            ((2.0, 60.0), 32631, "Шетланды: без исключения"),
            ((15.63, 78.22), 32633, "Шпицберген, Лонгйир: 33"),
            ((25.0, 78.0), 32635, "Шпицберген: 35"),
            ((40.0, 80.0), 32637, "Земля Франца-Иосифа: 37"),
            ((50.0, 80.0), 32639, "восточнее 42°: обычная зона"),
        ]
        for (lon, lat), epsg, name in cases:
            with self.subTest(name):
                self.assertEqual(utm.epsg_for(lon, lat), epsg)

    def test_point_in_other_crs(self):
        # Москва в Web Mercator
        merc = QgsCoordinateReferenceSystem("EPSG:3857")
        p = QgsCoordinateTransform(QgsCoordinateReferenceSystem("EPSG:4326"), merc, CTX) \
            .transform(QgsPointXY(37.62, 55.75))
        crs, err = utm.crs_for_point(p, merc, CTX)
        self.assertIsNone(err)
        self.assertEqual(crs.authid(), "EPSG:32637")
        # Та же точка в UTM 36N остаётся зоной 37
        u36 = QgsCoordinateReferenceSystem("EPSG:32636")
        p = QgsCoordinateTransform(QgsCoordinateReferenceSystem("EPSG:4326"), u36, CTX) \
            .transform(QgsPointXY(37.62, 55.75))
        self.assertEqual(utm.crs_for_point(p, u36, CTX)[0].authid(), "EPSG:32637")

    def test_polar_and_invalid(self):
        wgs = QgsCoordinateReferenceSystem("EPSG:4326")
        crs, err = utm.crs_for_point(QgsPointXY(30, 85), wgs, CTX)
        self.assertIsNone(crs)
        self.assertIn("84", err)
        crs, err = utm.crs_for_point(QgsPointXY(30, -81), wgs, CTX)
        self.assertIsNone(crs)
        crs, err = utm.crs_for_point(QgsPointXY(0, 0), QgsCoordinateReferenceSystem(), CTX)
        self.assertIsNone(crs)
        self.assertTrue(err)


class MessageBar:
    def __init__(self):
        self.messages = []

    def pushMessage(self, title, text, level, duration):
        self.messages.append((text, level))


class Iface:
    def __init__(self):
        self.window = QMainWindow()
        self.canvas = QgsMapCanvas(self.window)
        self.bar = MessageBar()
        self.menu = []
        self.plugin_menu = QMenu("Модули")

    def mainWindow(self): return self.window
    def mapCanvas(self): return self.canvas
    def messageBar(self): return self.bar
    def addToolBar(self, name):
        # как в настоящем QGIS: панель в окне, но владеет ею Python
        bar = QToolBar(name)
        self.window.addToolBar(bar)
        sip.transferback(bar)
        return bar
    def pluginMenu(self): return self.plugin_menu
    def addPluginToMenu(self, m, a): self.menu.append((m, a.text()))
    def removePluginMenu(self, m, a): self.menu.remove((m, a.text()))


def toolbars(iface):
    app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    return [b for b in iface.window.findChildren(QToolBar) if b.objectName() == "AltanEcoToolbar"]


class PluginTest(unittest.TestCase):
    def setUp(self):
        QgsProject.instance().clear()
        self.iface = Iface()
        self.plugin = project_utm_crs.classFactory(self.iface)
        self.plugin.initGui()

    def tearDown(self):
        self.plugin.unload()

    def show(self, crs_id, rect):
        crs = QgsCoordinateReferenceSystem(crs_id)
        QgsProject.instance().setCrs(crs)
        self.iface.canvas.setDestinationCrs(crs)
        self.iface.canvas.setExtent(rect)

    def test_button_and_menu(self):
        bars = toolbars(self.iface)
        self.assertEqual(len(bars), 1)
        self.assertIn(self.plugin.action, bars[0].actions())
        self.assertEqual(self.iface.menu, [("&Альтан-Эко", self.plugin.action.text())])
        self.assertFalse(self.plugin.action.icon().isNull())

    def test_sets_project_crs(self):
        # Москва в градусах
        self.show("EPSG:4326", QgsRectangle(37.0, 55.5, 38.2, 56.0))
        self.plugin.action.trigger()
        self.assertEqual(QgsProject.instance().crs().authid(), "EPSG:32637")
        text, level = self.iface.bar.messages[-1]
        self.assertEqual(level, Qgis.MessageLevel.Success)
        self.assertIn("EPSG:32637", text)
        # повторное нажатие ничего не меняет
        self.plugin.action.trigger()
        text, level = self.iface.bar.messages[-1]
        self.assertEqual(level, Qgis.MessageLevel.Info)
        self.assertIn("уже", text)

    def test_south_from_mercator(self):
        # Сидней, карта в Web Mercator
        merc = QgsCoordinateReferenceSystem("EPSG:3857")
        c = QgsCoordinateTransform(QgsCoordinateReferenceSystem("EPSG:4326"), merc, CTX) \
            .transform(QgsPointXY(151.21, -33.87))
        self.show("EPSG:3857", QgsRectangle(c.x() - 5000, c.y() - 5000, c.x() + 5000, c.y() + 5000))
        self.plugin.action.trigger()
        self.assertEqual(QgsProject.instance().crs().authid(), "EPSG:32756")

    def test_polar_keeps_crs(self):
        self.show("EPSG:4326", QgsRectangle(10, 85, 20, 88))
        self.plugin.action.trigger()
        self.assertEqual(QgsProject.instance().crs().authid(), "EPSG:4326")
        self.assertEqual(self.iface.bar.messages[-1][1], Qgis.MessageLevel.Warning)

    def test_unload_leaves_nothing(self):
        self.plugin.unload()
        self.assertEqual(toolbars(self.iface), [])
        self.assertEqual(self.iface.menu, [])
        self.plugin.initGui()  # для tearDown


if __name__ == "__main__":
    result = unittest.main(exit=False, verbosity=2).result
    QgsProject.instance().clear()
    app.exitQgis()
    shutil.rmtree(PROFILE, ignore_errors=True)
    sys.exit(0 if result.wasSuccessful() else 1)
