from __future__ import annotations

import argparse
import json
from pathlib import Path

from agent import OmniGameDevAgent
from memory import InternetIngestor


def main() -> None:
    parser = argparse.ArgumentParser(description="OmniGameDev AI command-line agent")
    parser.add_argument("request", nargs="*", help="Natural language game request")
    parser.add_argument("--project-name", help="Override generated project folder name")
    parser.add_argument("--no-run", action="store_true", help="Generate files without smoke testing")
    parser.add_argument("--install-deps", action="store_true", help="Install generated project dependencies before smoke tests")
    parser.add_argument("--ingest-url", action="append", default=[], help="Fetch a user-approved URL into persistent memory")
    parser.add_argument("--ingest-only", action="store_true", help="Only ingest URLs, then exit")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    args = parser.parse_args()

    request = " ".join(args.request).strip() or "build a 3D dungeon game with bosses"
    root = Path(__file__).resolve().parent
    agent = OmniGameDevAgent(root)
    if args.ingest_url:
        added = InternetIngestor(agent.memory).ingest_urls(args.ingest_url)
        if args.ingest_only:
            print(json.dumps({"ingested_chunks": added, "urls": args.ingest_url}, indent=2) if args.json else f"Ingested {added} memory chunk(s).")
            return

    result = agent.build(
        request,
        project_name=args.project_name,
        run_after=not args.no_run,
        install_dependencies=args.install_deps,
    )

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
        return

    execution = result.execution
    print(f"OmniGameDev AI generated: {result.generation.project_path}")
    print(f"Engine: {result.plan.engine} | Language: {result.plan.language}")
    print(f"Files: {len(result.generation.files)}")
    if execution:
        print(f"Smoke test: {'passed' if execution.success else 'failed'}")
        if execution.error_summary:
            print(f"Error: {execution.error_summary}")
    if result.fixes:
        print("Self-heal fixes:")
        for fix in result.fixes:
            print(f"- {fix}")


if __name__ == "__main__":
    main()
