import json
import sys
from pathlib import Path

import requests

sys.stdout.reconfigure(encoding="utf-8")
root = Path(__file__).resolve().parent / "source_checks"
response = requests.get(
    "https://kokkai.ndl.go.jp/api/speech",
    params={"issueID": "122115262X00120260324", "speaker": "会田卓司", "recordPacking": "json", "maximumRecords": 30},
    timeout=30,
)
response.raise_for_status()
data = response.json()
(root / "diet_20260324_aida.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
print("records", data.get("numberOfRecords"))
for row in data.get("speechRecord", []):
    speech = row.get("speech", "")
    print(row.get("speechOrder"), row.get("speechURL"), speech[:150])
