"""
Convert KODE-WILAYAH-KEPMENDAGRI-2025.xlsx into raw CSVs (prov/kab/kec/kel).

The XLSX is expected at project root under KODE-WILAYAH-KEPMENDAGRI-2025/KODE-WILAYAH-KEPMENDAGRI-2025.xlsx.
No external dependencies (uses stdlib zip + xml.etree).
"""

from __future__ import annotations

import csv
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Iterable, Tuple
from zipfile import ZipFile

ROOT = Path(__file__).parent.parent
SRC_XLSX = ROOT / "KODE-WILAYAH-KEPMENDAGRI-2025" / "KODE-WILAYAH-KEPMENDAGRI-2025.xlsx"
RAW_DIR = ROOT / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)


NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


def load_shared_strings(zf: ZipFile) -> list[str]:
    tree = ET.fromstring(zf.read("xl/sharedStrings.xml"))
    out = []
    for si in tree.findall(f"{NS}si"):
        t = si.find(f".//{NS}t")
        out.append(t.text if t is not None else "")
    return out


def iter_rows(zf: ZipFile, shared: list[str]) -> Iterable[Dict[str, str]]:
    """Yield rows as dict keyed by column letters."""
    for event, elem in ET.iterparse(zf.open("xl/worksheets/sheet1.xml"), events=("end",)):
        if elem.tag != f"{NS}row":
            continue
        # skip header
        if elem.attrib.get("r") == "1":
            elem.clear()
            continue

        row: Dict[str, str] = {}
        for c in elem.findall(f"{NS}c"):
            ref = c.attrib.get("r", "")
            col = "".join(ch for ch in ref if ch.isalpha())
            v = c.find(f"{NS}v")
            if v is None:
                continue
            val = v.text
            if c.attrib.get("t") == "s":
                val = shared[int(val)]
            row[col] = val
        if row:
            yield row
        elem.clear()


def collect() -> Tuple[Dict[str, str], Dict[str, str], Dict[str, str], Dict[str, str]]:
    prov: Dict[str, str] = {}
    kab: Dict[str, str] = {}
    kec: Dict[str, str] = {}
    kel: Dict[str, str] = {}

    with ZipFile(SRC_XLSX) as zf:
        shared = load_shared_strings(zf)
        for row in iter_rows(zf, shared):
            prov_code, prov_name = row.get("G", ""), row.get("H", "")
            kab_code, kab_name = row.get("E", ""), row.get("F", "")
            kec_code, kec_name = row.get("C", ""), row.get("D", "")
            kel_code, kel_name = row.get("A", ""), row.get("B", "")

            if prov_code:
                prov.setdefault(prov_code, prov_name)
            if kab_code:
                kab.setdefault(kab_code, kab_name)
            if kec_code:
                kec.setdefault(kec_code, kec_name)
            if kel_code:
                kel.setdefault(kel_code, kel_name)

    return prov, kab, kec, kel


def write_csv(path: Path, rows: Dict[str, str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "name"])
        for k in sorted(rows.keys()):
            writer.writerow([k, rows[k]])


def main():
    if not SRC_XLSX.exists():
        raise SystemExit(f"Source XLSX not found: {SRC_XLSX}")

    prov, kab, kec, kel = collect()

    write_csv(RAW_DIR / "provinsi.csv", prov)
    write_csv(RAW_DIR / "kabupaten_kota.csv", kab)
    write_csv(RAW_DIR / "kecamatan.csv", kec)
    write_csv(RAW_DIR / "kelurahan.csv", kel)

    print("Written:")
    print("  provinsi :", len(prov))
    print("  kab/kota :", len(kab))
    print("  kecamatan:", len(kec))
    print("  kel/desa :", len(kel))


if __name__ == "__main__":
    main()
