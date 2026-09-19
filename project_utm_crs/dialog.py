from qgis.core import Qgis, QgsProject
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QFont
from qgis.PyQt.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
)

from . import msk, utm

TITLE = "СК проекта"
ROLE = Qt.ItemDataRole.UserRole


class CrsDialog(QDialog):
    """СК по центру карты: зона UTM и МСК субъекта РФ."""

    def __init__(self, iface, parent=None):
        super().__init__(parent)
        self.iface = iface
        self.setWindowTitle("СК проекта по центру карты")
        self.resize(520, 360)

        self.info = QLabel()
        self.info.setWordWrap(True)
        self.list = QListWidget()
        self.refresh_btn = QPushButton("Определить заново")
        self.apply_btn = QPushButton("Назначить проекту")
        self.apply_btn.setDefault(True)
        buttons = QHBoxLayout()
        buttons.addWidget(self.refresh_btn)
        buttons.addStretch()
        buttons.addWidget(self.apply_btn)
        close = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close.rejected.connect(self.close)

        layout = QVBoxLayout(self)
        layout.addWidget(self.info)
        layout.addWidget(self.list, 1)
        layout.addLayout(buttons)
        layout.addWidget(close)

        self.refresh_btn.clicked.connect(self.refresh)
        self.apply_btn.clicked.connect(self.apply)
        self.list.itemDoubleClicked.connect(self.apply)
        self.list.currentItemChanged.connect(self._update_buttons)
        self._update_buttons()

    def _update_buttons(self, *args):
        self.apply_btn.setEnabled(self.list.currentItem() is not None)

    def _add(self, text, data, bold=False):
        entry = QListWidgetItem(text)
        entry.setData(ROLE, data)
        if bold:
            font = QFont(entry.font())
            font.setBold(True)
            entry.setFont(font)
        self.list.addItem(entry)

    def refresh(self):
        self.list.clear()
        canvas = self.iface.mapCanvas()
        center = canvas.extent().center()
        crs = canvas.mapSettings().destinationCrs()
        context = QgsProject.instance().transformContext()
        lines = []
        ll = utm.lonlat(center, crs, context)
        if ll is None:
            self.info.setText("Не удалось пересчитать центр карты в градусы.")
            self._update_buttons()
            return
        lon, lat = ll
        lines.append("Центр карты: {:.4f}° {}, {:.4f}° {}".format(
            abs(lon), "в. д." if lon >= 0 else "з. д.", abs(lat), "с. ш." if lat >= 0 else "ю. ш."))

        utm_crs, error = utm.crs_for_point(center, crs, context)
        if utm_crs is not None:
            self._add("{} ({})".format(utm_crs.description(), utm_crs.authid()), ("utm", utm_crs))
        else:
            lines.append(error)

        self.info.setText("\n".join(lines + ["Запрос субъекта РФ к OpenStreetMap…"]))
        self.info.repaint()
        lines.append(self._add_msk(lon, lat))
        lines.append("Сейчас у проекта: " + (QgsProject.instance().crs().description() or "СК не задана"))
        self.info.setText("\n".join(line for line in lines if line))
        if self.list.count():
            self.list.setCurrentRow(0)
        self._update_buttons()

    def _add_msk(self, lon, lat):
        """Добавляет МСК субъекта; возвращает строку для пояснения."""
        answer, error = msk.reverse_geocode(lon, lat)
        if error:
            return error + " МСК не показаны."
        code, name = msk.region_from_reverse(answer)
        if code is None:
            return "Не территория России ({}): МСК нет.".format(name or "место не определено")
        zones = msk.zones_for(code, lon)
        if not zones:
            return "Субъект: {} ({:02d}). В модуле для него нет МСК.".format(name, code)
        for i, item in enumerate(zones):
            text = item["name"]
            cm = msk.central_meridian(item)
            if cm is not None:
                text += "  (осевой меридиан {:.2f}°)".format(cm)
            self._add(text, ("msk", item), bold=i == 0)
        return "Субъект: {} ({:02d}). Подходящая МСК выделена жирным.".format(name, code)

    def apply(self, *args):
        current = self.list.currentItem()
        if current is None:
            return
        kind, value = current.data(ROLE)
        crs = msk.crs_for(value) if kind == "msk" else value
        name = value["name"] if kind == "msk" else current.text()
        project = QgsProject.instance()
        if project.crs() == crs:
            self.iface.messageBar().pushMessage(TITLE, "Уже установлена: " + name,
                                                Qgis.MessageLevel.Info, 4)
            return
        project.setCrs(crs)
        self.iface.messageBar().pushMessage(TITLE, "СК проекта: " + name,
                                            Qgis.MessageLevel.Success, 4)
        self.info.setText(self.info.text().rsplit("\n", 1)[0] + "\nСейчас у проекта: " + name)
