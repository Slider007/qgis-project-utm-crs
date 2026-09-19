# Плагин QGIS «UTM СК проекта»

Устройство и возможности — в `README.md`. Общие правила модулей компании — в
`~/Projects/QGIS/CLAUDE.md`.

## Как выпускать версию

1. `tests/run_tests.sh` — все проверки должны пройти.
2. Поднять `version=` и дописать `changelog=` в `project_utm_crs/metadata.txt`.
3. После подтверждения — коммит и пуш, затем релиз с архивом:
   `gh release create vX.Y.Z "$(./build_zip.sh)" --title X.Y.Z --notes "…"`.
4. Дальнейшие шаги — в локальном `CLAUDE.local.md`.

## Устройство

- `utm.py` — выбор зоны и пересчёт центра карты в градусы, без GUI.
- `plugin.py` — кнопка и пункт меню; СК меняется через `QgsProject.setCrs`,
  холст QGIS сам пересчитывает охват и остаётся на том же месте.

## Грабли

- Папка плагина `project_utm_crs` — это id у пользователей, не менять.
- Кнопка — на общей панели «Альтан-Эко», пункт — в подменю «Модули → Альтан-Эко»
  с логотипом: `altan_toolbar.py` и `altan_logo.svg` копируются из
  `~/Projects/QGIS/shared/` без изменений.
- Проверка в настоящем QGIS: `QGIS --profiles-path <tmp> --code check.py`.
  QGIS-LTR на macOS хранит настройки профиля в
  `<tmp>/profiles/default/qgis.org/QGIS3.ini` (не в `QGIS/QGIS3.ini`):
  включать плагин (`[PythonPlugins] project_utm_crs=true`) нужно там.
  В меню QGIS подменю называется «Альтан-Эко» — без `&`.
