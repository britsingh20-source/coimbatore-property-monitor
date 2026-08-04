import base64
from pathlib import Path


def main() -> None:
    source = Path("assets/sample_b64")
    if not source.exists():
        return
    destination = Path("assets/properties/pattanam-sample")
    destination.mkdir(parents=True, exist_ok=True)
    for encoded in sorted(source.glob("*.jpg.b64")):
        output = destination / encoded.name.removesuffix(".b64")
        output.write_bytes(base64.b64decode(encoded.read_text(encoding="ascii")))
        print(f"Decoded sample asset: {output}")


if __name__ == "__main__":
    main()
