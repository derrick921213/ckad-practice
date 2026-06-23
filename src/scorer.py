"""
Scoring logic: 根據 verify 結果計算分數。
"""

from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import Optional

from schema import Question


@dataclass
class QuestionResult:
    question: Question
    check_results: list[dict]           # from verifier.run_checks()
    elapsed_seconds: float
    attempted: bool = True

    @property
    def total_checks(self) -> int:
        return len(self.check_results)

    @property
    def passed_checks(self) -> int:
        return sum(1 for r in self.check_results if r["passed"])

    @property
    def score(self) -> float:
        """依通過的 check 比例給分，滿分為題目的 weight。"""
        if self.total_checks == 0:
            return 0.0
        ratio = self.passed_checks / self.total_checks
        return round(self.question.weight * ratio, 1)

    @property
    def max_score(self) -> float:
        return float(self.question.weight)

    @property
    def passed(self) -> bool:
        return self.passed_checks == self.total_checks and self.total_checks > 0


@dataclass
class SessionResult:
    results: list[QuestionResult] = field(default_factory=list)
    started_at: float = field(default_factory=time.time)
    finished_at: Optional[float] = None

    def add(self, result: QuestionResult) -> None:
        self.results.append(result)

    def finish(self) -> None:
        self.finished_at = time.time()

    @property
    def total_score(self) -> float:
        return round(sum(r.score for r in self.results), 1)

    @property
    def max_possible(self) -> float:
        return round(sum(r.max_score for r in self.results), 1)

    @property
    def percentage(self) -> float:
        if self.max_possible == 0:
            return 0.0
        return round(self.total_score / self.max_possible * 100, 1)

    @property
    def elapsed_minutes(self) -> float:
        end = self.finished_at or time.time()
        return round((end - self.started_at) / 60, 1)

    @property
    def passed_questions(self) -> int:
        return sum(1 for r in self.results if r.passed)

    def summary(self) -> dict:
        return {
            "total_questions": len(self.results),
            "passed_questions": self.passed_questions,
            "total_score": self.total_score,
            "max_possible": self.max_possible,
            "percentage": self.percentage,
            "elapsed_minutes": self.elapsed_minutes,
            "pass_threshold": 66.0,
            "exam_pass": self.percentage >= 66.0,
        }
