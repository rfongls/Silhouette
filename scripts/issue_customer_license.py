#!/usr/bin/env python3
"""
Render a customer license from CUSTOMER_LICENSE_TEMPLATE.md,
embed identifiers, and update WATERMARK.json.
"""
import argparse, pathlib, datetime, json


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--customer-id", required=True, help="Unique customer ID or contract identifier"
    )
    ap.add_argument(
        "--out", default="artifacts/licenses", help="Output directory for rendered license"
    )
    args = ap.parse_args()

    template = pathlib.Path("CUSTOMER_LICENSE_TEMPLATE.md").read_text()
    now = datetime.datetime.utcnow().strftime("%Y-%m-%d")

    rendered = (
        template.replace("{{CUSTOMER_ID}}", args.customer_id).replace("{{DATE}}", now)
    )

    out_dir = pathlib.Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"license_{args.customer_id}_{now}.md"
    out_file.write_text(rendered, encoding="utf-8")
    print(f"Wrote license: {out_file}")

    # Embed into watermark
    wm_path = pathlib.Path("WATERMARK.json")
    if wm_path.exists():
        wm = json.loads(wm_path.read_text())
    else:
        wm = {}
    wm["customer_id"] = args.customer_id
    wm["license_date"] = now
    wm_path.write_text(json.dumps(wm, indent=2))
    print(f"Updated watermark with customer_id={args.customer_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
