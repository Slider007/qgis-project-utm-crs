"""Выбор зоны UTM (WGS 84) по точке. Без GUI, чтобы проверять headless."""

import math

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsCsException,
    QgsPointXY,
)

WGS84 = "EPSG:4326"
# Сетка UTM определена от 80° ю. ш. до 84° с. ш., ближе к полюсам — UPS
MIN_LAT = -80.0
MAX_LAT = 84.0


def zone_for(lon, lat):
    """Номер зоны UTM (1–60) с исключениями для Норвегии и Шпицбергена."""
    lon = (lon + 180.0) % 360.0 - 180.0  # долгота в [-180, 180)
    zone = int(math.floor((lon + 180.0) / 6.0)) + 1
    if 56.0 <= lat < 64.0 and 3.0 <= lon < 12.0:
        zone = 32  # юго-запад Норвегии
    elif 72.0 <= lat < 84.0 and 0.0 <= lon < 42.0:
        # Шпицберген: вместо зон 32, 34, 36 — расширенные 31, 33, 35, 37
        if lon < 9.0:
            zone = 31
        elif lon < 21.0:
            zone = 33
        elif lon < 33.0:
            zone = 35
        else:
            zone = 37
    return zone


def epsg_for(lon, lat):
    """Код EPSG «WGS 84 / UTM zone NN{N|S}»: 326NN на севере, 327NN на юге."""
    return (32600 if lat >= 0 else 32700) + zone_for(lon, lat)


def lonlat(point, crs, transform_context):
    """Точка из crs в градусы WGS 84; None, если пересчитать нельзя."""
    if not crs.isValid():
        return None
    wgs = QgsCoordinateReferenceSystem(WGS84)
    try:
        p = QgsCoordinateTransform(crs, wgs, transform_context).transform(QgsPointXY(point))
    except QgsCsException:
        return None
    if not (math.isfinite(p.x()) and math.isfinite(p.y())):
        return None
    return p.x(), p.y()


def crs_for_point(point, crs, transform_context):
    """СК UTM для точки в системе crs.

    Возвращает (СК, None) или (None, текст ошибки для пользователя)."""
    ll = lonlat(point, crs, transform_context)
    if ll is None:
        return None, "Не удалось пересчитать центр карты в градусы."
    lon, lat = ll
    if not MIN_LAT <= lat <= MAX_LAT:
        return None, (
            "Центр карты на широте {:.1f}°: зоны UTM есть только от 80° ю. ш. "
            "до 84° с. ш.".format(lat))
    utm = QgsCoordinateReferenceSystem("EPSG:%d" % epsg_for(lon, lat))
    if not utm.isValid():
        return None, "В QGIS нет системы координат EPSG:%d." % epsg_for(lon, lat)
    return utm, None
