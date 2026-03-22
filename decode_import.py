import base64
import gzip
import json
import sys

from pathlib import Path
with open(Path(__file__).parent / "BetterTTS_Streamerbot_Import.txt", "r") as f:
    encoded = f.read().strip()

raw = base64.b64decode(encoded)

# Skip 4-byte "SBAE" header
header = raw[:4]
print(f"Header: {header}")
assert header == b"SBAE", f"Unexpected header: {header}"

compressed = raw[4:]
decompressed = gzip.decompress(compressed)
data = json.loads(decompressed)
print(json.dumps(data, indent=2))
