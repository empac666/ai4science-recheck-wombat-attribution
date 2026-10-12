"""Download fixed inputs and audit bytes/Parquet metadata only; no model calls."""
import hashlib
import json
import time
import urllib.request
from pathlib import Path

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
REV = "e86ec35687b0c0ebd1ecc151610a08224d8cf851"
SIZES = {4: 158085845, 5: 142772488, 12: 203909943}


def main():
    dest = ROOT / "data"
    dest.mkdir(exist_ok=True)
    records = []
    for pattern, expected in SIZES.items():
        url = (f"{dataset_base_url}/resolve/"
               f"{REV}/validation_datasets/Pattern%20{pattern}/"
               "validation_molecules.parquet?download=true")
        path = dest / f"pattern_{pattern}.parquet"
        partial = path.with_suffix(".partial")
        started = time.monotonic()
        if not path.exists():
            request = urllib.request.Request(url, headers={"Cache-Control": "no-cache"})
            with urllib.request.urlopen(request, timeout=120) as response:
                if response.status != 200:
                    raise RuntimeError(f"Expected full HTTP 200, got {response.status}")
                with partial.open("wb") as out:
                    while chunk := response.read(1024 * 1024):
                        out.write(chunk)
            if partial.stat().st_size != expected:
                raise RuntimeError(f"Pattern {pattern}: incomplete byte count")
            partial.rename(path)
        assert path.stat().st_size == expected
        digest = hashlib.sha256()
        with path.open("rb") as source:
            while chunk := source.read(1024 * 1024):
                digest.update(chunk)
        parquet = pq.ParquetFile(path)
        record = dict(pattern=pattern, revision=REV, url=url,
                      file=str(path.relative_to(ROOT)), bytes=path.stat().st_size,
                      sha256=digest.hexdigest(), rows=parquet.metadata.num_rows,
                      row_groups=parquet.metadata.num_row_groups,
                      schema=str(parquet.schema_arrow), seconds=time.monotonic()-started)
        records.append(record)
        (ROOT / "evidence/parquet_full_manifest.json").write_text(
            json.dumps(records, indent=2) + "\n")
        print(json.dumps(record), flush=True)


if __name__ == "__main__":
    main()
