"""
main.py — Entry point for the Multi-Agent E-commerce Dispute Resolution pipeline.

Usage:
    python main.py

Reads:  input/EC_001.json ... input/EC_050.json
Writes: output/EC_001.json ... output/EC_050.json
        logging/trace.jsonl  (overwritten each run — only latest run)
"""
import json
import sys
from pathlib import Path
from datetime import datetime, timezone

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from utils.data_loader import load_all_data
from agents.coordinator import process_case
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Requirement #4: Declare model name clearly in source code
MODEL_NAME = "gpt-4o-mini"

INPUT_DIR = Path("input")
OUTPUT_DIR = Path("output")
TRACE_FILE = Path("logging/trace.jsonl")


def main():
    start_time = datetime.now(timezone.utc)
    print(f"[Main] Pipeline started at {start_time.isoformat()}")

    # --- Load all data once ---
    store = load_all_data("data")

    # --- Prepare output directory ---
    OUTPUT_DIR.mkdir(exist_ok=True)

    # --- Collect input cases ---
    case_files = sorted(INPUT_DIR.glob("EC_*.json"))
    if not case_files:
        print("[Main] ERROR: No input files found in input/ directory!")
        print("[Main] Waiting for Checkpoint 1 input files...")
        sys.exit(1)

    print(f"[Main] Found {len(case_files)} input cases.")

    # --- Process each case ---
    trace_records = []
    success_count = 0
    error_count = 0

    for i, case_file in enumerate(case_files, 1):
        case_id = case_file.stem
        print(f"[Main] ({i:02d}/{len(case_files)}) Processing {case_id}...", end=" ")

        try:
            final_output, trace = process_case(case_file, store)

            # Write output
            out_path = OUTPUT_DIR / case_file.name
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(final_output, f, ensure_ascii=False, indent=2)

            trace_records.append(trace)
            success_count += 1
            print(f"OK  [{final_output['assessment']['primary_issue']}]")

        except Exception as e:
            error_count += 1
            print(f"ERROR: {e}")
            import traceback
            traceback.print_exc()

    # --- Write trace (overwrite, only latest run) ---
    TRACE_FILE.parent.mkdir(exist_ok=True)
    with open(TRACE_FILE, "w", encoding="utf-8") as f:
        for record in trace_records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    end_time = datetime.now(timezone.utc)
    elapsed = (end_time - start_time).total_seconds()
    print(f"\n[Main] Done in {elapsed:.1f}s. Success: {success_count}, Errors: {error_count}")
    print(f"[Main] Output: {OUTPUT_DIR}/  |  Trace: {TRACE_FILE}")


if __name__ == "__main__":
    main()
