#!/usr/bin/env python3
"""
Generate golden JSON reference files from CardDemo ASCII data files.

Usage:
    python test-harness/generate_golden_files.py [--data-dir DIR] [--output-dir DIR]

Parses each ASCII data file in app/data/ASCII/ using the corresponding
copybook layout and writes structured JSON to golden-files/.
"""

import argparse
import json
import os
import sys

from copybook_parser import LAYOUT_REGISTRY, generate_golden_file


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate golden JSON files from CardDemo ASCII data"
    )
    parser.add_argument(
        "--data-dir",
        default=os.path.join(
            os.path.dirname(__file__), "..", "app", "data", "ASCII"
        ),
        help="Path to ASCII data directory",
    )
    parser.add_argument(
        "--output-dir",
        default=os.path.join(os.path.dirname(__file__), "..", "golden-files"),
        help="Path to golden files output directory",
    )
    args = parser.parse_args()

    data_dir = os.path.abspath(args.data_dir)
    output_dir = os.path.abspath(args.output_dir)

    print(f"Data directory:   {data_dir}")
    print(f"Output directory: {output_dir}")
    print()

    results = []
    for file_key in sorted(LAYOUT_REGISTRY.keys()):
        result = generate_golden_file(data_dir, output_dir, file_key)
        results.append(result)
        status = result["status"]
        if status == "generated":
            print(f"  {file_key:12s}  {result['records']:>4d} records  -> {result['output']}")
        else:
            print(f"  {file_key:12s}  SKIPPED ({result.get('reason', 'unknown')})")

    # Write summary
    summary_path = os.path.join(output_dir, "_generation_summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "data_dir": data_dir,
                "output_dir": output_dir,
                "results": results,
            },
            f,
            indent=2,
        )

    total = sum(1 for r in results if r["status"] == "generated")
    total_records = sum(r.get("records", 0) for r in results if r["status"] == "generated")
    print(f"\nGenerated {total} golden files with {total_records} total records.")
    print(f"Summary: {summary_path}")


if __name__ == "__main__":
    main()
