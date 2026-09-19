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
ORG = "project-utm-crs-tests"
QCoreApplication.setOrganizationName(ORG)
QCoreApplication.setApplicationName(ORG)

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
    from project_utm_crs import dialog as dialog_module, msk, utm  # noqa: E402

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


def reverse_answer(iso, state):
    return {"address": {"state": state, "ISO3166-2-lvl4": iso, "country": "Россия",
                        "country_code": "ru"}}


class MskDataTest(unittest.TestCase):
    def test_set(self):
        data = msk.items()
        self.assertEqual(len(data), 253)
        self.assertEqual(len({i["name"] for i in data}), len(data))
        self.assertEqual(len({i["code"] for i in data}), 80)
        known = set(msk.ISO_TO_CODE.values())
        for item in data:
            with self.subTest(item["name"]):
                self.assertIn(item["code"], known)
                self.assertTrue(QgsCoordinateReferenceSystem.fromProj(item["proj"]).isValid())
                self.assertIsNotNone(msk.central_meridian(item))

    def test_region(self):
        self.assertEqual(msk.region_from_reverse(reverse_answer("RU-MOS", "Московская область")),
                         (50, "Московская область"))
        self.assertEqual(msk.region_from_reverse(reverse_answer("RU-MOW", "Москва"))[0], 77)
        self.assertEqual(msk.region_from_reverse(reverse_answer("RU-YAN", "ЯНАО"))[0], 89)
        # без ISO-кода — по названию субъекта
        self.assertEqual(msk.region_from_reverse(reverse_answer("", "Тюменская область"))[0], 72)
        answer = {"address": {"country": "Казахстан", "country_code": "kz", "state": "x"}}
        self.assertEqual(msk.region_from_reverse(answer), (None, "Казахстан"))
        self.assertEqual(msk.region_from_reverse(None)[0], None)

    def test_zone_choice(self):
        self.assertEqual(msk.zones_for(50, 38.3)[0]["name"], "МСК-50 зона 2 Московская область")
        self.assertEqual(msk.zones_for(50, 35.8)[0]["name"], "МСК-50 зона 1 Московская область")
        zones = msk.zones_for(72, 68.0)  # несколько вариантов: основной первым
        self.assertEqual(zones[0]["variant"], "")
        self.assertEqual(len(zones), 14)
        self.assertEqual(msk.zones_for(17, 94.0), [])  # Тывы в наборе нет

    def test_crs_registered_once(self):
        item = [i for i in msk.items() if i["name"].startswith("МСК-50 зона 2")][0]
        registry = QgsApplication.coordinateReferenceSystemRegistry()
        before = len(registry.userCrsList())
        crs = msk.crs_for(item)
        self.assertTrue(crs.authid().startswith("USER:"), crs.authid())
        self.assertEqual(crs.description(), item["name"])
        self.assertEqual(msk.crs_for(item), crs)
        self.assertEqual(len(registry.userCrsList()), before + 1)
        wgs = QgsCoordinateReferenceSystem("EPSG:4326")
        exact = QgsCoordinateReferenceSystem.fromProj(item["proj"])
        a = QgsCoordinateTransform(wgs, crs, CTX).transform(QgsPointXY(38.3, 55.9))
        b = QgsCoordinateTransform(wgs, exact, CTX).transform(QgsPointXY(38.3, 55.9))
        self.assertLess(a.distance(b), 0.001)

    @unittest.skipUnless(os.environ.get("MSK_ONLINE", "1") == "1", "без интернета")
    def test_live_nominatim(self):
        answer, error = msk.reverse_geocode(38.5, 55.9)
        if error:
            self.skipTest(error)
        self.assertEqual(msk.region_from_reverse(answer), (50, "Московская область"))


class PluginTest(unittest.TestCase):
    def setUp(self):
        QgsProject.instance().clear()
        self.iface = Iface()
        self.plugin = project_utm_crs.classFactory(self.iface)
        self.plugin.initGui()
        self._reverse = msk.reverse_geocode
        self.set_region("RU-MOS", "Московская область")

    def tearDown(self):
        msk.reverse_geocode = self._reverse
        self.plugin.unload()
        QgsProject.instance().clear()

    def set_region(self, iso, state):
        msk.reverse_geocode = lambda lon, lat: (reverse_answer(iso, state), None)

    def show(self, crs_id, rect):
        crs = QgsCoordinateReferenceSystem(crs_id)
        QgsProject.instance().setCrs(crs)
        self.iface.canvas.setDestinationCrs(crs)
        self.iface.canvas.setExtent(rect)

    def open(self):
        self.plugin.action.trigger()
        return self.plugin.dialog

    def rows(self, dlg):
        return [dlg.list.item(i).text() for i in range(dlg.list.count())]

    def test_button_and_menu(self):
        bars = toolbars(self.iface)
        self.assertEqual(len(bars), 1)
        self.assertIn(self.plugin.action, bars[0].actions())
        self.assertEqual(self.iface.menu, [("&Альтан-Эко", self.plugin.action.text())])
        self.assertFalse(self.plugin.action.icon().isNull())

    def test_utm_and_msk_rows(self):
        self.show("EPSG:4326", QgsRectangle(38.2, 55.85, 38.5, 55.95))
        dlg = self.open()
        self.assertIsInstance(dlg, dialog_module.CrsDialog)
        rows = self.rows(dlg)
        self.assertEqual(rows[0], "WGS 84 / UTM zone 37N (EPSG:32637)")
        self.assertTrue(rows[1].startswith("МСК-50 зона 2 Московская область"))
        self.assertTrue(rows[2].startswith("МСК-50 зона 1 Московская область"))
        self.assertTrue(dlg.list.item(1).font().bold())
        self.assertIn("Московская область (50)", dlg.info.text())
        self.assertEqual(dlg.list.currentRow(), 0)
        # повторное нажатие поднимает то же окно
        self.assertIs(self.open(), dlg)

    def test_apply_utm(self):
        self.show("EPSG:4326", QgsRectangle(37.0, 55.5, 38.2, 56.0))
        dlg = self.open()
        dlg.apply_btn.click()
        self.assertEqual(QgsProject.instance().crs().authid(), "EPSG:32637")
        text, level = self.iface.bar.messages[-1]
        self.assertEqual(level, Qgis.MessageLevel.Success)
        self.assertIn("EPSG:32637", text)
        self.assertIn("Сейчас у проекта: WGS 84 / UTM zone 37N", dlg.info.text())
        dlg.apply_btn.click()
        self.assertEqual(self.iface.bar.messages[-1][1], Qgis.MessageLevel.Info)

    def test_apply_msk(self):
        self.show("EPSG:4326", QgsRectangle(38.2, 55.85, 38.5, 55.95))
        dlg = self.open()
        dlg.list.setCurrentRow(1)
        dlg.apply_btn.click()
        self.assertEqual(QgsProject.instance().crs().description(), "МСК-50 зона 2 Московская область")

    def test_south_from_mercator(self):
        msk.reverse_geocode = lambda lon, lat: (
            {"address": {"country": "Австралия", "country_code": "au"}}, None)
        merc = QgsCoordinateReferenceSystem("EPSG:3857")
        c = QgsCoordinateTransform(QgsCoordinateReferenceSystem("EPSG:4326"), merc, CTX) \
            .transform(QgsPointXY(151.21, -33.87))
        self.show("EPSG:3857", QgsRectangle(c.x() - 5000, c.y() - 5000, c.x() + 5000, c.y() + 5000))
        dlg = self.open()
        self.assertEqual(self.rows(dlg), ["WGS 84 / UTM zone 56S (EPSG:32756)"])
        self.assertIn("Не территория России (Австралия)", dlg.info.text())
        dlg.apply_btn.click()
        self.assertEqual(QgsProject.instance().crs().authid(), "EPSG:32756")

    def test_polar_no_utm(self):
        self.show("EPSG:4326", QgsRectangle(10, 85, 20, 88))
        msk.reverse_geocode = lambda lon, lat: ({}, None)
        dlg = self.open()
        self.assertEqual(dlg.list.count(), 0)
        self.assertFalse(dlg.apply_btn.isEnabled())
        self.assertIn("84", dlg.info.text())
        self.assertEqual(QgsProject.instance().crs().authid(), "EPSG:4326")

    def test_offline_keeps_utm(self):
        msk.reverse_geocode = lambda lon, lat: (None, "Нет ответа от сервиса адресов OpenStreetMap.")
        self.show("EPSG:4326", QgsRectangle(38.2, 55.85, 38.5, 55.95))
        dlg = self.open()
        self.assertEqual(self.rows(dlg), ["WGS 84 / UTM zone 37N (EPSG:32637)"])
        self.assertIn("МСК не показаны", dlg.info.text())

    def test_region_without_msk(self):
        self.set_region("RU-TY", "Республика Тыва")
        self.show("EPSG:4326", QgsRectangle(93.9, 51.6, 94.1, 51.8))
        dlg = self.open()
        self.assertEqual(dlg.list.count(), 1)  # только UTM
        self.assertIn("нет МСК", dlg.info.text())

    def test_unload_leaves_nothing(self):
        self.open()
        self.plugin.unload()
        self.assertEqual(toolbars(self.iface), [])
        self.assertEqual(self.iface.menu, [])
        self.assertIsNone(self.plugin.dialog)
        self.plugin.initGui()  # для tearDown


def _leftover_dirs():
    """Папки тестовой организации вне tests/_profile: их создают Qt и initQgis()."""
    from qgis.PyQt.QtCore import QStandardPaths
    base = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.GenericDataLocation)
    found = [os.path.join(base, ORG)]
    path = QgsApplication.qgisSettingsDirPath().rstrip("/")
    while path and os.path.dirname(path) != path:
        if os.path.basename(path) == ORG:
            found.append(path)
        path = os.path.dirname(path)
    return [p for p in found if os.path.basename(p) == ORG and not p.startswith(PROFILE)]


if __name__ == "__main__":
    result = unittest.main(exit=False, verbosity=2).result
    leftovers = _leftover_dirs()
    QgsProject.instance().clear()
    app.exitQgis()
    shutil.rmtree(PROFILE, ignore_errors=True)
    for path in leftovers:
        shutil.rmtree(path, ignore_errors=True)
    sys.exit(0 if result.wasSuccessful() else 1)
