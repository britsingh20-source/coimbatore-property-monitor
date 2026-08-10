import argparse
import json
from pathlib import Path


MISSING = {"", "NOT SPECIFIED", "UNKNOWN", "N/A", "NONE"}


def present(value) -> bool:
    return str(value or "").strip().upper() not in MISSING


def build_caption(job: dict) -> str:
    prop = job.get("property") or {}
    location = str(job.get("property_location") or "Coimbatore").strip()
    property_type = str(prop.get("property_type") or "Property").strip()

    facts = []
    for label, key in (
        ("BHK", "bhk"),
        ("Land", "land_area"),
        ("Built-up", "built_up_area"),
        ("Price", "price"),
        ("Facing", "facing"),
        ("Road", "road_width"),
        ("Approval", "approval"),
    ):
        value = prop.get(key)
        if present(value):
            facts.append(f"{label}: {value}")

    lines = [
        f"🏡 {property_type} in {location}",
        "",
    ]
    lines.extend(facts[:6])
    lines += [
        "",
        "Property details are based on the source listing. Verify documents, dimensions, location and availability before purchase.",
        "",
        "DM for details / site visit.",
        "",
        "#CoimbatoreRealEstate #CoimbatoreProperty #TamilNaduRealEstate",
    ]
    return "\n".join(lines).strip()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("job")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    job = json.loads(Path(args.job).read_text(encoding="utf-8"))
    caption = build_caption(job)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(caption + "\n", encoding="utf-8")
    print(caption)


if __name__ == "__main__":
    main()
