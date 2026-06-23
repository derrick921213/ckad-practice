#!/usr/bin/env python3
"""
CKAD Practice System — 主程式入口
使用 Typer 提供 CLI 介面。
"""

from __future__ import annotations
import time
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.prompt import Prompt
from rich import print as rprint

# 確保 src/ 在 import path
sys.path.insert(0, str(Path(__file__).parent))

import loader
import verifier
import environment as env
from scorer import QuestionResult, SessionResult
from schema import Domain, Difficulty
import ui

app = typer.Typer(
    name="ckad",
    help="CKAD Practice System — 本地 K8s 練習評分工具",
    add_completion=False,
)
console = Console()

# ─── 指令 ──────────────────────────────────────────────────────

@app.command("practice")
def practice(
    domain: Optional[str] = typer.Option(None, "--domain", "-d", help="過濾領域 (1-6)"),
    difficulty: Optional[str] = typer.Option(None, "--difficulty", help="easy/medium/hard"),
    question_id: Optional[str] = typer.Option(None, "--id", help="直接練習特定題目 ID"),
    skip_verify: bool = typer.Option(False, "--skip-verify", help="只顯示題目，不驗證"),
    context: str = typer.Option("kind-ckad", "--context", help="kubectl context"),
):
    """互動式練習模式（主要功能）。"""
    ui.show_banner()

    # 檢查 cluster
    cluster_info = env.get_cluster_info()
    ui.show_cluster_status(cluster_info)
    if not cluster_info.get("running") and not skip_verify:
        console.print("\n[yellow]提示: 加上 --skip-verify 可不連接叢集單純瀏覽題目[/yellow]")
        raise typer.Exit(1)

    # 載入題目
    domain_enum = _parse_domain(domain)
    questions = loader.load_all(domain_filter=domain_enum)

    if question_id:
        questions = [q for q in questions if q.id == question_id]
        if not questions:
            console.print(f"[red]找不到題目 ID: {question_id}[/red]")
            raise typer.Exit(1)

    if difficulty:
        questions = [q for q in questions if q.difficulty.value == difficulty]

    if not questions:
        console.print("[yellow]沒有符合條件的題目。[/yellow]")
        raise typer.Exit(0)

    console.print(f"\n[bold]共 {len(questions)} 道題目，開始練習！[/bold]\n")
    session = SessionResult()

    for i, question in enumerate(questions, 1):
        # 執行 setup
        if question.setup and not skip_verify:
            with ui.show_spinner("設定題目環境中...") as progress:
                task = progress.add_task("setup")
                env.apply_setup_commands(question.setup)

        # 顯示題目
        ui.show_question(question, i, len(questions), elapsed=0)

        if skip_verify:
            ui.wait_for_enter()
            continue

        # 等待使用者完成（即時計時器）
        elapsed = ui.wait_with_live_timer()

        # 驗證
        with ui.show_spinner("驗證答案中...") as progress:
            task = progress.add_task("verify")
            check_results = verifier.run_checks(question.verify, context=context)

        result = QuestionResult(
            question=question,
            check_results=check_results,
            elapsed_seconds=elapsed,
        )
        session.add(result)
        ui.show_question_result(result)

        # Cleanup（可選）
        if question.cleanup:
            do_cleanup = typer.confirm("是否清除本題環境？", default=True)
            if do_cleanup:
                with ui.show_spinner("清除中...") as progress:
                    env.apply_cleanup_commands(question.cleanup)

        if i < len(questions):
            ui.wait_for_enter("按 Enter 進入下一題...")

    if not skip_verify:
        session.finish()
        ui.show_session_summary(session)


@app.command("list")
def list_questions(
    domain: Optional[str] = typer.Option(None, "--domain", "-d"),
    difficulty: Optional[str] = typer.Option(None, "--difficulty"),
):
    """列出所有可用題目。"""
    from rich.table import Table
    from rich import box

    domain_enum = _parse_domain(domain)
    questions = loader.load_all(domain_filter=domain_enum)
    if difficulty:
        questions = [q for q in questions if q.difficulty.value == difficulty]

    table = Table(box=box.ROUNDED, show_header=True)
    table.add_column("ID", style="cyan", width=12)
    table.add_column("Domain", max_width=25)
    table.add_column("標題", max_width=35)
    table.add_column("難度", justify="center", width=8)
    table.add_column("配分", justify="right", width=6)
    table.add_column("Checks", justify="right", width=7)

    for q in questions:
        color = ui.DOMAIN_COLORS.get(q.domain, "white")
        table.add_row(
            q.id,
            f"[{color}]{q.domain.value[:24]}[/{color}]",
            q.title,
            q.difficulty.value,
            str(q.weight),
            str(len(q.verify)),
        )

    console.print(table)
    console.print(f"\n[dim]共 {len(questions)} 道題目[/dim]")


@app.command("fetch")
def fetch_github(
    url: str = typer.Argument(help="GitHub raw Markdown URL"),
    save: bool = typer.Option(False, "--save", help="儲存到 custom/ 資料夾"),
):
    """從 GitHub Markdown URL 匯入題目（預覽或儲存）。"""
    console.print(f"[cyan]正在抓取: {url}[/cyan]")
    questions = loader.load_from_github(url)
    console.print(f"解析到 [bold]{len(questions)}[/bold] 道題目\n")

    for q in questions:
        console.print(f"  [cyan]{q.id}[/cyan]  {q.title}")

    if save and questions:
        from rich.prompt import Confirm
        if Confirm.ask(f"\n儲存 {len(questions)} 道題目到 custom/ 資料夾？"):
            for q in questions:
                path = loader.save_question(q, "custom")
                console.print(f"  ✅ 已儲存: {path.name}")


@app.command("cluster")
def cluster_cmd(
    action: str = typer.Argument(help="status / reset / create / delete"),
):
    """管理 kind cluster 環境。"""
    if action == "status":
        info = env.get_cluster_info()
        ui.show_cluster_status(info)

    elif action == "create":
        console.print("[cyan]建立 kind cluster...[/cyan]")
        env.create_cluster()
        console.print("[green]✅ 完成[/green]")

    elif action == "delete":
        if typer.confirm("確認刪除 kind cluster？"):
            env.delete_cluster()
            console.print("[green]✅ 已刪除[/green]")

    elif action == "reset":
        if typer.confirm("⚠️  確認重製 cluster？（所有資源將被清除）"):
            with ui.show_spinner("重製 cluster 中...") as p:
                p.add_task("reset")
                env.reset_cluster()
            console.print("[green]✅ Cluster 已重製完成[/green]")
    else:
        console.print(f"[red]未知操作: {action}[/red]  可用: status / reset / create / delete")


@app.command("verify")
def verify_cmd(
    question_id: str = typer.Argument(help="題目 ID"),
    context: str = typer.Option("kind-ckad", "--context"),
):
    """直接驗證指定題目（不需要進入 practice 模式）。"""
    q = loader.load_by_id(question_id)
    if not q:
        console.print(f"[red]找不到題目: {question_id}[/red]")
        raise typer.Exit(1)

    console.print(f"\n[bold]驗證題目: {q.title}[/bold]\n")
    with ui.show_spinner("驗證中...") as p:
        p.add_task("v")
        results = verifier.run_checks(q.verify, context=context)

    result = QuestionResult(question=q, check_results=results, elapsed_seconds=0)
    ui.show_question_result(result)


# ─── 輔助函式 ───────────────────────────────────────────────────

_DOMAIN_SHORTCUTS = {
    "1": Domain.DESIGN_BUILD,
    "2": Domain.ENV_CONFIG,
    "3": Domain.DEPLOYMENT,
    "4": Domain.SERVICES,
    "5": Domain.OBSERVABILITY,
    "6": Domain.MISC,
}

def _parse_domain(domain: Optional[str]) -> Optional[Domain]:
    if domain is None:
        return None
    if domain in _DOMAIN_SHORTCUTS:
        return _DOMAIN_SHORTCUTS[domain]
    # 嘗試 enum value 比對
    for d in Domain:
        if domain.lower() in d.value.lower():
            return d
    console.print(f"[yellow]⚠️  無法識別 domain '{domain}'，顯示全部題目[/yellow]")
    return None


if __name__ == "__main__":
    app()
