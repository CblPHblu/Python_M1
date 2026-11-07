import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys
from .parsing import parse_assignments, decode_json
from .errors import SubmissionError, AnalysisFailure
from .repositories import InMemorySubmissionRepository
from .sources import JSONLSource
from .services import SubmissionService, AnalysisService, import_source
from .analyzers import default_registry, DeclarationAnalyzer
from .models import AnalysisContext

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="school-lab")
    commands = parser.add_subparsers(dest="command", required=True)
    import_cmd = commands.add_parser("import", help="Импорт JSONL")
    import_cmd.add_argument("path", type=Path)
    analyze_cmd = commands.add_parser("analyze", help="Запуск анализатора")
    analyze_cmd.add_argument("path", type=Path)
    analyze_cmd.add_argument("--assignments", type=Path, default=Path("data/assignments.json"))
    analyze_cmd.add_argument("--analyzer", choices=("length", "template", "declaration"), default="length")
    args = parser.parse_args(argv)
    repository = InMemorySubmissionRepository()
    try:
        summary = import_source(JSONLSource(args.path), SubmissionService(repository))
        if args.command == "import":
            print(json.dumps(summary.to_dict(), ensure_ascii=False, indent=2))
            return 1 if summary.errors else 0
        assignments = parse_assignments(decode_json(args.assignments.read_text(encoding="utf-8")))
        registry = default_registry()
        # Демонстрационное расширение: сервис не содержит ветвления по типу анализатора.
        registry.register("declaration", DeclarationAnalyzer)
        service = AnalysisService(repository, registry)
        reports = []
        analysis_errors = list(summary.errors)
        for submission_id in summary.accepted:
            submission = repository.get(submission_id)
            assert submission is not None
            try:
                assignment = assignments[submission.assignment_id]
                report = service.run(submission_id, args.analyzer, AnalysisContext(assignment))
            except (KeyError, AnalysisFailure) as exc:
                analysis_errors.append({"submission_id": submission_id, "code": "analysis_error", "field": "analyzer", "message": str(exc)})
            else:
                reports.append(asdict(report))
        print(json.dumps({"reports": reports, "errors": analysis_errors}, ensure_ascii=False, indent=2))
        return 1 if analysis_errors else 0
    except (OSError, UnicodeError, SubmissionError) as exc:
        print(json.dumps({"code": "source_unavailable", "message": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
