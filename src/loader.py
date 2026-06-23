"""
Question loader: 從本地 YAML 或 GitHub URL 載入題目。
"""

from __future__ import annotations
import os
import re
import urllib.request
from pathlib import Path
from typing import Optional

import yaml

from schema import Question, Domain, Difficulty, VerifyCheck, CheckType, QuestionSource


QUESTIONS_DIR = Path(__file__).parent.parent / "questions"

# domain 資料夾名對應
DOMAIN_MAP = {
    "01-design-build": Domain.DESIGN_BUILD,
    "02-env-config": Domain.ENV_CONFIG,
    "03-deployment": Domain.DEPLOYMENT,
    "04-services": Domain.SERVICES,
    "05-observability": Domain.OBSERVABILITY,
    "06-misc": Domain.MISC,
    "custom": Domain.MISC,
}


def load_all(domain_filter: Optional[Domain] = None) -> list[Question]:
    """載入所有本地題目，可依 domain 過濾。"""
    questions: list[Question] = []
    for folder, domain in DOMAIN_MAP.items():
        dir_path = QUESTIONS_DIR / folder
        if not dir_path.exists():
            continue
        for yaml_file in sorted(dir_path.glob("*.yaml")):
            try:
                q = _load_yaml(yaml_file, domain)
                if domain_filter is None or q.domain == domain_filter:
                    questions.append(q)
            except Exception as e:
                print(f"[loader] ⚠️  跳過 {yaml_file.name}: {e}")
    return questions


def load_by_id(question_id: str) -> Optional[Question]:
    """依 ID 載入單道題目。"""
    for q in load_all():
        if q.id == question_id:
            return q
    return None


def load_from_github(url: str) -> list[Question]:
    """
    從 GitHub raw Markdown URL 解析題目（jamesbuckett 格式）。
    這是輕量解析器，抓取後轉成 Question 物件。
    """
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            content = resp.read().decode("utf-8")
    except Exception as e:
        print(f"[loader] ❌ 無法取得 {url}: {e}")
        return []

    return _parse_markdown_questions(content, url)


def _load_yaml(path: Path, fallback_domain: Domain) -> Question:
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    # 把 verify list 轉成 VerifyCheck
    raw_checks = data.pop("verify", [])
    checks = [VerifyCheck(**c) for c in raw_checks]

    raw_sources = data.pop("sources", [])
    sources = [QuestionSource(**s) for s in raw_sources]

    if "domain" not in data:
        data["domain"] = fallback_domain

    return Question(**data, verify=checks, sources=sources)


def _parse_markdown_questions(content: str, source_url: str) -> list[Question]:
    """
    簡易解析 jamesbuckett 格式的 Markdown：
    - ### XX-YY. Title 為題目開頭
    - * bullet 為 prompt 內容
    - <details>...<summary>Solution</summary> 為解答（略過）
    """
    questions: list[Question] = []
    # 找每個 ### 區塊
    sections = re.split(r"(?=^### )", content, flags=re.MULTILINE)

    counter = 1
    for section in sections:
        m = re.match(r"^### ([\d\w-]+)\.\s+(.+)", section)
        if not m:
            continue

        raw_id = m.group(1).lower()
        title = m.group(2).strip()

        # 抓 bullet point 作為 prompt（去掉 <details> 以後的部分）
        body = re.split(r"<details", section, maxsplit=1)[0]
        lines = body.strip().split("\n")[1:]  # 去掉標題行
        prompt_lines = [
            l.lstrip("* ").strip()
            for l in lines
            if l.strip().startswith("*") and l.strip()
        ]
        prompt = "\n".join(prompt_lines) if prompt_lines else title

        q = Question(
            id=f"gh-{raw_id}",
            domain=Domain.MISC,
            difficulty=Difficulty.MEDIUM,
            title=title,
            prompt=prompt,
            verify=[],
            sources=[QuestionSource(url=source_url)],
            tags=["github", "auto-imported"],
        )
        questions.append(q)
        counter += 1

    return questions


def save_question(q: Question, folder: str = "custom") -> Path:
    """把 Question 物件存為 YAML 到 custom 資料夾。"""
    target_dir = QUESTIONS_DIR / folder
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / f"{q.id}.yaml"

    data = q.model_dump(exclude_none=True)
    # 把 enum 轉 str
    data["domain"] = q.domain.value
    data["difficulty"] = q.difficulty.value
    data["verify"] = [
        {k: (v.value if hasattr(v, "value") else v) for k, v in c.items() if v is not None}
        for c in data.get("verify", [])
    ]

    with open(target_path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, sort_keys=False)

    return target_path
