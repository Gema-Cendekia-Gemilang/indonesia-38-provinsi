import csv
import json
import pathlib
from collections import defaultdict
import shutil

ROOT = pathlib.Path(__file__).parent.parent
SRC = ROOT / "data" / "raw"
OUT = ROOT / "data" / "json"
OUT.mkdir(parents=True, exist_ok=True)


def load_csv(path: pathlib.Path):
    """Read CSV with headers intact and keep codes as strings."""
    rows = []
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        # normalise headers
        fieldnames = [h.strip().lower() for h in reader.fieldnames or []]
        id_key = "id" if "id" in fieldnames else fieldnames[0]
        name_key = "name" if "name" in fieldnames else fieldnames[1]
        for row in reader:
            code = (row.get(id_key) or "").strip()
            name = (row.get(name_key) or "").strip()
            if not code:
                continue
            rows.append({"id": code, "name": name})
    return rows


def dump(rows, path: pathlib.Path):
    path.write_bytes(json.dumps(rows, ensure_ascii=False).encode("utf-8"))


prov = load_csv(SRC / "provinsi.csv")
reg = load_csv(SRC / "kabupaten_kota.csv")
kec = load_csv(SRC / "kecamatan.csv")
des = load_csv(SRC / "kelurahan.csv")

# clean old outputs to avoid stale files
for sub in ("regencies", "districts", "villages"):
    target = OUT / sub
    if target.exists():
        shutil.rmtree(target)

# index data for faster grouping
reg_by_prov = defaultdict(list)
for r in reg:
    prov_code = r["id"].split(".")[0]
    reg_by_prov[prov_code].append(r)

kec_by_kab = defaultdict(list)
for r in kec:
    kab_code = ".".join(r["id"].split(".")[:2])
    kec_by_kab[kab_code].append(r)

des_by_kec = defaultdict(list)
for r in des:
    kec_code = ".".join(r["id"].split(".")[:3])
    des_by_kec[kec_code].append(r)

dump(prov, OUT / "provinsi.json")

for pid in (row["id"] for row in prov):
    parent = OUT / "regencies"
    parent.mkdir(exist_ok=True)
    dump(reg_by_prov.get(pid, []), parent / f"{pid}.json")

for rid in (row["id"] for row in reg):
    parent = OUT / "districts"
    parent.mkdir(exist_ok=True)
    dump(kec_by_kab.get(rid, []), parent / f"{rid}.json")

for kid in (row["id"] for row in kec):
    parent = OUT / "villages"
    parent.mkdir(exist_ok=True)
    dump(des_by_kec.get(kid, []), parent / f"{kid}.json")
