#!/usr/bin/env python3
import os
import sys
from pathlib import Path

# Ensure src is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

MANIFEST_PATH = "artifacts/research/cp_source_feasibility_2026_07/cp_root_population_manifest_v2.jsonl.zst"
META_PATH = "artifacts/research/cp_source_feasibility_2026_07/cp_root_population_manifest_v2.meta.json"
STOCKFISH_PATH = "/opt/homebrew/bin/stockfish"
OUTPUT_PATH = "artifacts/research/cp_target_reconstruction_2026_09/attempt_2/cp_target_root_results_v2.jsonl"


def main():
    out_file = Path(OUTPUT_PATH)
    if out_file.exists():
        raise FileExistsError(
            f"Attempt 2 output file already exists at {out_file}. "
            "Resuming or unlinking an existing attempt is strictly forbidden."
        )

    from chessheat.cp_target_acquisition import TargetAcquisitionRunnerV2

    runner = TargetAcquisitionRunnerV2(
        manifest_path=MANIFEST_PATH,
        output_path=OUTPUT_PATH,
        stockfish_path=STOCKFISH_PATH,
        meta_path=META_PATH,
    )

    print("Starting exact TARGET reconstruction attempt 2...")
    runner.run()
    print("Completed exact TARGET reconstruction attempt 2.")


if __name__ == "__main__":
    main()
