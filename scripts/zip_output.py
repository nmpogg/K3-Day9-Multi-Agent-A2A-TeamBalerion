"""
scripts/zip_output.py
Creates output.zip containing exactly the 50 EC_*.json files from output/
as required for submission.

Usage: python scripts/zip_output.py
"""
import sys
import zipfile
from pathlib import Path

OUTPUT_DIR = Path("output")
ZIP_PATH = Path("output.zip")


def main():
    files = sorted(OUTPUT_DIR.glob("EC_*.json"))
    if len(files) == 0:
        print("ERROR: No output files found in output/")
        sys.exit(1)
    if len(files) != 50:
        print(f"WARNING: Expected 50 files, found {len(files)}")

    with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in files:
            zf.write(f, f"output/{f.name}")  # Store inside output/ directory
            print(f"  Added: output/{f.name}")

    print(f"\nCreated {ZIP_PATH} with {len(files)} files.")

    # Verify zip
    with zipfile.ZipFile(ZIP_PATH, "r") as zf:
        names = zf.namelist()
        print(f"Verified: {len(names)} files in zip.")
        unexpected = [n for n in names if not n.startswith("output/EC_") or not n.endswith(".json")]
        if unexpected:
            print(f"WARNING: Unexpected files in zip: {unexpected}")


if __name__ == "__main__":
    main()
