class SubmissionError(Exception):
    """Ошибка, понятная CLI и другим адаптерам."""

    def __init__(self, code: str, field: str, message: str) -> None:
        super().__init__(message)
        self.code, self.field, self.message = code, field, message

    def to_dict(self) -> dict[str, str]:
        return {"code": self.code, "field": self.field, "message": self.message}

class AnalysisFailure(Exception):
    """Нарушение контракта анализатора или условий анализа."""
