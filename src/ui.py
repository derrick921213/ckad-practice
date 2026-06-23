"""
Rich TUI 介面：顯示題目、計時、結果。
"""

from __future__ import annotations
import sys
import time
import threading
from typing import Optional

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.rule import Rule
from rich.prompt import Prompt, Confirm
from rich import box

from schema import Question, Domain
from scorer import QuestionResult, SessionResult

console = Console()

DOMAIN_COLORS = {
    Domain.DESIGN_BUILD: "cyan",
    Domain.ENV_CONFIG: "yellow",
    Domain.DEPLOYMENT: "green",
    Domain.SERVICES: "blue",
    Domain.OBSERVABILITY: "magenta",
    Domain.MISC: "white",
}

CKAD_BANNER = """
 ██████╗██╗  ██╗ █████╗ ██████╗
██╔════╝██║ ██╔╝██╔══██╗██╔══██╗
██║     █████╔╝ ███████║██║  ██║
██║     ██╔═██╗ ██╔══██║██║  ██║
╚██████╗██║  ██╗██║  ██║██████╔╝
 ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝
     Practice System v1.0
"""


def show_banner() -> None:
    console.print(Text(CKAD_BANNER, style="bold cyan"), justify="center")
    console.print()


def show_question(q: Question, index: int, total: int, elapsed: float = 0) -> None:
    """顯示題目內容。"""
    color = DOMAIN_COLORS.get(q.domain, "white")
    mins = int(elapsed // 60)
    secs = int(elapsed % 60)

    header = (
        f"[bold]題目 {index}/{total}[/bold]  "
        f"[{color}]● {q.domain.value}[/{color}]  "
        f"[dim]難度: {q.difficulty.value}  "
        f"配分: {q.weight}pts  "
        f"已用時: {mins:02d}:{secs:02d}[/dim]"
    )

    content = f"\n[bold yellow]{q.title}[/bold yellow]\n\n{q.prompt}"
    if q.tips:
        content += f"\n\n[dim italic]💡 提示: {q.tips}[/dim italic]"

    console.print()
    console.print(Rule(header))
    console.print(Panel(content, border_style=color, padding=(1, 2)))
    console.print()


def show_check_results(results: list[dict]) -> None:
    """顯示驗證結果表格。"""
    table = Table(box=box.ROUNDED, show_header=True, header_style="bold")
    table.add_column("檢查項目", style="dim", max_width=30)
    table.add_column("結果", justify="center", width=6)
    table.add_column("訊息")

    for r in results:
        check_type = r["check"].type.value
        if r["passed"]:
            icon = "[bold green]✅[/bold green]"
        else:
            icon = "[bold red]❌[/bold red]"
        table.add_row(check_type, icon, r["message"])

    console.print(table)


def show_question_result(result: QuestionResult) -> None:
    """顯示單題結果。"""
    console.print()
    if result.passed:
        console.print(Panel(
            f"[bold green]✅ 通過！得 {result.score}/{result.max_score} 分[/bold green]",
            border_style="green",
        ))
    else:
        console.print(Panel(
            f"[bold red]❌ 未完全通過  {result.score}/{result.max_score} 分[/bold red]\n"
            f"[dim]通過 {result.passed_checks}/{result.total_checks} 項檢查[/dim]",
            border_style="red",
        ))
    show_check_results(result.check_results)
    console.print(f"[dim]作答時間: {result.elapsed_seconds:.0f} 秒[/dim]")
    console.print()


def show_session_summary(session: SessionResult) -> None:
    """顯示本次練習總結。"""
    s = session.summary()
    console.print()
    console.print(Rule("[bold]本次練習結果[/bold]"))

    # 分數圓餅指示
    pct = s["percentage"]
    bar_filled = int(pct / 5)
    bar = "█" * bar_filled + "░" * (20 - bar_filled)
    pct_color = "green" if pct >= 66 else "yellow" if pct >= 50 else "red"

    summary_text = (
        f"\n"
        f"  [{pct_color}]{bar}[/{pct_color}]  {pct}%\n\n"
        f"  得分:     {s['total_score']} / {s['max_possible']} pts\n"
        f"  通過題數: {s['passed_questions']} / {s['total_questions']}\n"
        f"  總時間:   {s['elapsed_minutes']} 分鐘\n"
        f"  考試及格線: 66%\n"
    )
    if s["exam_pass"]:
        summary_text += "\n  [bold green]🎉 達到及格標準！繼續保持！[/bold green]\n"
    else:
        summary_text += "\n  [bold red]📚 尚未達到及格標準，繼續練習！[/bold red]\n"

    console.print(Panel(summary_text, title="[bold]總分報告[/bold]", border_style=pct_color))

    # 逐題明細
    table = Table(box=box.SIMPLE, show_header=True, header_style="bold dim")
    table.add_column("題號", width=8)
    table.add_column("標題", max_width=30)
    table.add_column("Domain", max_width=20)
    table.add_column("得分", justify="right", width=10)
    table.add_column("結果", justify="center", width=6)
    table.add_column("時間", justify="right", width=8)

    for r in session.results:
        color = DOMAIN_COLORS.get(r.question.domain, "white")
        icon = "✅" if r.passed else "❌"
        table.add_row(
            r.question.id,
            r.question.title[:30],
            f"[{color}]{r.question.domain.value[:20]}[/{color}]",
            f"{r.score}/{r.max_score}",
            icon,
            f"{r.elapsed_seconds:.0f}s",
        )

    console.print(table)
    console.print()


def show_cluster_status(info: dict) -> None:
    """顯示叢集狀態。"""
    if not info.get("running"):
        console.print(Panel(
            "[bold red]❌ Kind cluster 未運行[/bold red]\n"
            "請先執行: [cyan]bash kind/setup.sh[/cyan]",
            title="Cluster 狀態",
            border_style="red",
        ))
        return

    nodes_text = ""
    for n in info.get("nodes", []):
        status_color = "green" if n["status"] == "Ready" else "red"
        nodes_text += f"  [{status_color}]●[/{status_color}] {n['name']}  {n['status']}  ({n['role']})\n"

    console.print(Panel(
        f"[bold green]✅ Cluster 運行中[/bold green]\n\n{nodes_text}",
        title=f"[bold]kind-{info['cluster_name']}[/bold]",
        border_style="green",
    ))


def confirm_verify() -> bool:
    return Confirm.ask("\n[bold cyan]準備好了嗎？開始驗證答案？[/bold cyan]")


def wait_for_enter(msg: str = "按 Enter 繼續...") -> None:
    console.input(f"[dim]{msg}[/dim]")


def wait_with_live_timer(prompt: str = "在叢集完成操作後，按 Enter 進行驗證...") -> float:
    """顯示即時計時器並等待 Enter，回傳已用秒數。"""
    start = time.time()
    entered = threading.Event()

    def _read_enter() -> None:
        sys.stdin.readline()
        entered.set()

    t = threading.Thread(target=_read_enter, daemon=True)
    t.start()

    console.print(f"[dim]{prompt}[/dim]")

    with Live("", refresh_per_second=2, console=console, transient=True) as live:
        while not entered.is_set():
            elapsed = time.time() - start
            mins = int(elapsed // 60)
            secs = int(elapsed % 60)
            live.update(f"  [bold yellow]⏱  {mins:02d}:{secs:02d}[/bold yellow]")
            time.sleep(0.5)

    return time.time() - start


def show_spinner(msg: str) -> Progress:
    """回傳一個可用於 with 語句的 spinner progress。"""
    return Progress(
        SpinnerColumn(),
        TextColumn(f"[cyan]{msg}[/cyan]"),
        transient=True,
    )
