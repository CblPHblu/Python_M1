# Лабораторная работа №1 — Приём работ и расширяемые анализаторы

**Филатов Алексей Кириллович, М8О-104СВ-26**  
**Траектория:** Python Core · **уровень:** основной + одно углубление (типизированный декоратор)

Программа принимает JSONL-файл со сдачами студентов, проверяет данные и запускает простые заменяемые анализаторы. Сдаваемый код **не выполняется**. Схема Submission и AnalysisReport повторяет контракт из ноутбука «Лекция».

## Запуск

Нужен Python **3.10+**. Из папки проекта:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[test]"
python -m pytest -q
school-lab import data/submissions.jsonl
school-lab import data/invalid_submissions.jsonl
school-lab analyze data/submissions.jsonl --assignments data/assignments.json --analyzer length
school-lab analyze data/submissions.jsonl --assignments data/assignments.json --analyzer template
school-lab analyze data/submissions.jsonl --assignments data/assignments.json --analyzer declaration
```

Если PowerShell не даёт активировать окружение, запускайте `.venv\Scripts\python.exe -m pip install -e ".[test]"` и `.venv\Scripts\python.exe -m school_lab.cli import data/submissions.jsonl`.

CLI `import` выдаёт JSON с ключами `accepted`, `duplicate`, `errors`. При ошибке отдельной строки указывается `line_no`, импорт продолжается. Код завершения 1 означает ошибки среди строк; это предусмотрено, а не падение.

## Структура

- `models.py` — замороженные dataclass: Submission, Assignment, AnalysisReport и связанные модели.
- `parsing.py` — валидация JSON, схемы версии 1, ISO 8601 с зоной и AI-декларации.
- `hashing.py` — SHA-256 по каноническому JSON.
- `repositories.py` — in-memory хранение, запрет перезаписи.
- `sources.py` — два источника, контекстный менеджер для закрытия файла.
- `services.py` — приём, импорт, запуск анализа.
- `analyzers.py` — LengthAnalyzer, TemplateAnalyzer, Protocol и явный реестр.
- `cli.py` — терминальный адаптер.
- `tests/` — автоматические проверки.

## Правила приёма

Обязательные поля: `schema_version`, `submission_id`, `student_id`, `assignment_id`, `submitted_at`, `text`, `code`, `template_id`, `ai_declaration`. Версия схемы — 1; неизвестные поля запрещены. В декларации обязательны `used`, `tool`, `purpose`, `verified_by_student`; если `used=true`, `tool` и `purpose` должны быть непустыми. Строки `text`/`code` сохраняются как есть.

Повтор одинаковой сдачи возвращает `duplicate`, другой текст под прежним `submission_id` — ошибку `conflict`. Репозиторий живёт в пределах одного запуска CLI. Для демонстрации конфликтов есть `invalid_submissions.jsonl`.

## Анализаторы

`LengthAnalyzer`: количество непустых строк в `text` и `code`, с исходными номерами строк в evidence; оценка score=None.

`TemplateAnalyzer`: точные совпадения блока разрешённого шаблона в исходном коде, без обвинений в плагиате; score=None.

`DeclarationAnalyzer`: третий пример для защиты. Проверяет декларацию ИИ; новый класс добавлен через `registry.register()` без изменения `AnalysisService`.

Контракты отделяют объект от способа хранения. `Protocol` разрешает подставить любой класс с подходящими методами; в отличие от наследования от базового класса, явное объявление родителя не требуется.

## Дополнительное углубление

В `timing.py` есть декоратор `timed` с `ParamSpec`, `TypeVar` и `functools.wraps`. Он сохраняет сигнатуру, возвращаемое значение и метаданные функции, записывает длительность вызова даже при исключении. Для него есть отдельные тесты.

## Известные ограничения

Нет базы данных, сетевых запросов, запуска чужого кода и ML/LLM. Сравнение шаблона точное, без семантического поиска. После выхода CLI хранилище очищается. Это соответствует основному уровню ЛР №1.

## Git

Для сдачи требуются исходники, тесты, README, AI_USAGE.md, REPORT.md и тег `lab-1`. Если выполняете этапы раздельно, сделайте коммит `stage-a` после этапа А, затем `lab-1` после этапа Б. Не создавайте фиктивную историю задним числом.
