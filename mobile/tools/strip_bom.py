from pathlib import Path

root = Path(__file__).resolve().parents[1] / "app" / "src" / "main"
fixed = 0
for path in root.rglob("*"):
    if not path.is_file():
        continue
    data = path.read_bytes()
    if data.startswith(b"\xef\xbb\xbf"):
        path.write_bytes(data[3:])
        fixed += 1
        print("stripped BOM:", path.relative_to(root))
print("done", fixed)
