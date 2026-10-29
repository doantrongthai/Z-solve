import argparse
import logging
import sys
import time
from collections import Counter
from pathlib import Path

root_directory = Path(__file__).resolve().parent.parent
src_directory = root_directory / "src"
if str(root_directory) not in sys.path:
    sys.path.insert(0, str(root_directory))
if str(src_directory) not in sys.path:
    sys.path.insert(0, str(src_directory))

from datamate.config import PipelineConfig
from datamate.pipeline import DataMatePipeline


def setup_logger() -> logging.Logger:
    logger = logging.getLogger("DataMateRunner")
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter("[%(asctime)s] %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


def main() -> None:
    parser = argparse.ArgumentParser(description="DataMate Runner")
    parser.add_argument("--split", type=str, default="public_test", choices=["train", "public_test"])
    parser.add_argument("--output", type=Path, default=Path("results/submission.jsonl"))
    parser.add_argument("--max-samples", type=int, default=None)
    parser.add_argument("--data-dir", type=Path, default=Path("datamate"))
    parser.add_argument("--enable-llm", action="store_true")
    parser.add_argument("--model", type=str, default="Qwen/Qwen2.5-Coder-7B-Instruct")
    parser.add_argument("--load-in-4bit", action="store_true")
    parser.add_argument("--load-in-8bit", action="store_true")
    args = parser.parse_args()

    logger = setup_logger()
    logger.info("Initializing DataMate pipeline for split: %s", args.split)
    if args.enable_llm:
        logger.info("LLM enabled: %s (4-bit: %s, 8-bit: %s)", args.model, args.load_in_4bit, args.load_in_8bit)

    start_time = time.time()
    config = PipelineConfig(
        base_data_directory=args.data_dir,
        results_directory=args.output.parent,
        submission_filename=args.output.name,
        enable_llm=args.enable_llm,
        model_name=args.model,
        load_in_4bit=args.load_in_4bit,
        load_in_8bit=args.load_in_8bit,
    )
    pipeline = DataMatePipeline(config=config)

    submissions, metrics = pipeline.run_split(
        split=args.split,
        output_file_path=args.output,
        max_samples=args.max_samples,
    )
    elapsed_time = time.time() - start_time

    type_counts = Counter(sub.type for sub in submissions)
    abstain_count = type_counts.get("abstain", 0)

    print("\n" + "=" * 60)
    print("DATAMATE RUN EXECUTION REPORT")
    print("=" * 60)
    print(f"Split: {args.split}")
    print(f"Total processed questions: {len(submissions)}")
    print(f"Output file: {metrics['destination_path']}")
    print(f"Execution runtime: {elapsed_time:.2f} seconds")
    print(f"Total abstain count: {abstain_count} ({abstain_count / max(1, len(submissions)) * 100:.1f}%)")
    print("\nAnswer Type Distribution:")
    for ans_type, count in sorted(type_counts.items(), key=lambda x: -x[1]):
        print(f"  - {ans_type:15}: {count:5} ({count / len(submissions) * 100:.1f}%)")

    if "penalized_accuracy" in metrics:
        breakdown = metrics["evaluation_breakdown"]
        print(f"\nPenalized Accuracy (PA): {metrics['penalized_accuracy']:.4f}")
        print(f"  - Correct (+1): {breakdown['correct']}")
        print(f"  - Abstain  ( 0): {breakdown['abstain']}")
        print(f"  - Wrong   (-1): {breakdown['wrong']}")
        print(f"  - Total       : {breakdown['total']}")

    print("\nFirst 10 records of submission:")
    with open(metrics["destination_path"], "r", encoding="utf-8") as file_handle:
        for idx, line in enumerate(file_handle):
            if idx >= 10:
                break
            print(f"  [{idx + 1:02d}] {line.strip()}")
    print("=" * 60)


if __name__ == "__main__":
    main()
