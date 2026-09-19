"""Собирает project_utm_crs/msk.json из пользовательских СК профиля QGIS.

Запуск: python3 tools/build_msk_json.py <путь к qgis.db профиля>
Берутся только записи, у которых по названию понятны субъект и зона.
"""
import json
import os
import re
import sqlite3
import sys

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "project_utm_crs", "msk.json")

PATTERN = re.compile(
    r"^МСК-(?P<code>\d+)(?:\.\d+)?"
    r"(?: от (?P<base>СК-\d+))?"
    r"(?: зона (?P<zone>\d+))?"
    r"(?: \((?P<deg>[\d.]+) градусная\)|, (?P<deg2>[\d.]+) градусная)?"
    r"(?: (?P<subject>.+))?$")
SPECIAL = {
    "Московская СК (МГГТ)": (77, "Москва", None, ""),
    "МСК-1964 Санкт-Петербург": (78, "Санкт-Петербург", None, ""),
}
SUBJECT_FOR_CODE = {89: "Ямало-Ненецкий автономный округ"}


def parse(description):
    if description in SPECIAL:
        return SPECIAL[description]
    m = PATTERN.match(description)
    if not m:
        return None
    code = int(m.group("code"))
    if code > 99:
        return None
    variant = []
    if m.group("base"):
        variant.append("от " + m.group("base"))
    deg = m.group("deg") or m.group("deg2")
    if deg:
        variant.append(deg + "-градусная")
    subject = m.group("subject") or SUBJECT_FOR_CODE.get(code)
    if not subject:
        return None
    zone = int(m.group("zone")) if m.group("zone") else None
    return code, subject, zone, ", ".join(variant)


def main(db):
    rows = sqlite3.connect(db).execute(
        "select description, parameters from tbl_srs order by description").fetchall()
    items, skipped, seen = [], [], set()
    for description, proj in rows:
        parsed = parse(description)
        if parsed is None or not proj:
            skipped.append(description)
            continue
        if description in seen:
            skipped.append(description + " (повтор)")
            continue
        seen.add(description)
        code, subject, zone, variant = parsed
        proj = proj.replace(" +type=crs", "").strip()
        items.append({"name": description, "code": code, "subject": subject,
                      "zone": zone, "variant": variant, "proj": proj})
    items.sort(key=lambda i: (i["code"], i["variant"], i["zone"] or 0))
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print("записано", len(items), "->", OUT)
    print("пропущено:", skipped)


if __name__ == "__main__":
    main(sys.argv[1])
