import json
from datetime import datetime
from collections.abc import Mapping
from .errors import SubmissionError
from .models import AIDeclaration, Submission, Assignment

SUBMISSION_FIELDS = frozenset({"schema_version", "submission_id", "student_id", "assignment_id", "submitted_at", "text", "code", "template_id", "ai_declaration"})
DECLARATION_FIELDS = frozenset({"used", "tool", "purpose", "verified_by_student"})

def require_object(raw: object, name: str) -> dict[str, object]:
    if not isinstance(raw, dict) or any(not isinstance(k, str) for k in raw):
        raise SubmissionError("schema_error", name, "Ожидается JSON-объект")
    return raw

def require_fields(raw: Mapping[str, object], expected: frozenset[str], prefix: str = "") -> None:
    missing = expected - raw.keys()
    extra = raw.keys() - expected
    if missing:
        raise SubmissionError("schema_error", prefix + sorted(missing)[0], "Отсутствует обязательное поле")
    if extra:
        raise SubmissionError("schema_error", prefix + sorted(extra)[0], "Неизвестное поле")

def require_string(value: object, name: str, *, nonempty: bool = True) -> str:
    if not isinstance(value, str) or (nonempty and not value.strip()):
        raise SubmissionError("schema_error", name, "Ожидается непустая строка" if nonempty else "Ожидается строка")
    return value

def optional_string(value: object, name: str) -> str | None:
    return None if value is None else require_string(value, name)

def require_bool(value: object, name: str) -> bool:
    if type(value) is not bool:
        raise SubmissionError("schema_error", name, "Ожидается bool")
    return value

def decode_json(line: str) -> object:
    def unique_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, val in pairs:
            if key in result:
                raise SubmissionError("invalid_json", key, "Повторяющийся JSON-ключ")
            result[key] = val
        return result
    try:
        return json.loads(line, object_pairs_hook=unique_keys, parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))
    except (json.JSONDecodeError, ValueError) as exc:
        raise SubmissionError("invalid_json", "json", "Повреждённый JSON") from exc

def parse_submission(raw: object) -> Submission:
    data = require_object(raw, "submission")
    require_fields(data, SUBMISSION_FIELDS)
    version = data["schema_version"]
    if type(version) is not int:
        raise SubmissionError("schema_error", "schema_version", "Ожидается целое число, не bool")
    if version != 1:
        raise SubmissionError("unsupported_version", "schema_version", "Поддерживается только версия 1")
    declaration_raw = require_object(data["ai_declaration"], "ai_declaration")
    require_fields(declaration_raw, DECLARATION_FIELDS, "ai_declaration.")
    declaration = AIDeclaration(
        used=require_bool(declaration_raw["used"], "ai_declaration.used"),
        tool=optional_string(declaration_raw["tool"], "ai_declaration.tool"),
        purpose=optional_string(declaration_raw["purpose"], "ai_declaration.purpose"),
        verified_by_student=require_bool(declaration_raw["verified_by_student"], "ai_declaration.verified_by_student"),
    )
    if declaration.used and (declaration.tool is None or declaration.purpose is None):
        raise SubmissionError("schema_error", "ai_declaration", "При used=true необходимы tool и purpose")
    stamp = require_string(data["submitted_at"], "submitted_at")
    try:
        moment = datetime.fromisoformat(stamp)
    except ValueError as exc:
        raise SubmissionError("schema_error", "submitted_at", "Неверный формат даты ISO 8601") from exc
    if moment.tzinfo is None or moment.utcoffset() is None:
        raise SubmissionError("schema_error", "submitted_at", "Необходим часовой пояс")
    content_text = require_string(data["text"], "text", nonempty=False)
    content_code = require_string(data["code"], "code", nonempty=False)
    if not content_text.strip() and not content_code.strip():
        raise SubmissionError("schema_error", "text/code", "Текст или код должны быть непустыми")
    return Submission(version, require_string(data["submission_id"], "submission_id"), require_string(data["student_id"], "student_id"), require_string(data["assignment_id"], "assignment_id"), stamp, content_text, content_code, optional_string(data["template_id"], "template_id"), declaration)

def parse_assignments(raw: object) -> dict[str, Assignment]:
    if not isinstance(raw, list):
        raise SubmissionError("schema_error", "assignments", "Ожидается список заданий")
    result: dict[str, Assignment] = {}
    for item in raw:
        obj = require_object(item, "assignment")
        require_fields(obj, frozenset({"assignment_id", "allowed_template", "requirements"}))
        aid = require_string(obj["assignment_id"], "assignment_id")
        template = require_string(obj["allowed_template"], "allowed_template", nonempty=False)
        requirements = obj["requirements"]
        if not isinstance(requirements, list) or any(not isinstance(r, str) for r in requirements):
            raise SubmissionError("schema_error", "requirements", "Ожидается список строк")
        if aid in result:
            raise SubmissionError("conflict", "assignment_id", "Повтор идентификатора задания")
        result[aid] = Assignment(aid, template, tuple(requirements))
    return result
