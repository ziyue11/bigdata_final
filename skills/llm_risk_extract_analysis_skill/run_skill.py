import argparse
import os


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--industry", default="finance", help="finance or medical")
    parser.add_argument("--fallback", default="auto", choices=["auto", "rule", "llm"])
    args = parser.parse_args()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(script_dir))
    os.chdir(project_root)

    commands = [
        f"python src/llm_extract/extract_risk_fields.py --industry {args.industry} --fallback {args.fallback}",
        f"python src/llm_extract/build_risk_event_table.py --industry {args.industry}",
        f"python src/analysis/run_analysis.py --industry {args.industry}",
    ]
    for index, command in enumerate(commands, start=1):
        print(f"[Step {index}/3] {command}")
        exit_code = os.system(command)
        if exit_code != 0:
            raise SystemExit(exit_code)
    print(f"Skill complete for industry={args.industry}")


if __name__ == "__main__":
    main()
