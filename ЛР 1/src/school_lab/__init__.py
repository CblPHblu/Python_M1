"""Учебный пакет приёма лабораторных работ."""
from .models import Submission, AIDeclaration, Assignment, AnalysisReport
from .parsing import parse_submission
from .services import SubmissionService, AnalysisService

__all__ = ["Submission", "AIDeclaration", "Assignment", "AnalysisReport", "parse_submission", "SubmissionService", "AnalysisService"]
