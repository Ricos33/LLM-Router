import json
import sys
from pathlib import Path
from typing import List, Dict, Any

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from app.classifier import RuleBasedClassifier, ModelTier
from app.models import ChatMessage


def load_dataset(filepath: Path) -> List[Dict[str, Any]]:
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def run_benchmark():
    console = Console()
    dataset_path = Path(__file__).resolve().parent / "prompts.json"
    
    if not dataset_path.exists():
        console.print(f"[red]Error: Dataset not found at {dataset_path}[/red]")
        sys.exit(1)

    dataset = load_dataset(dataset_path)
    classifier = RuleBasedClassifier(threshold=0.50)

    console.print(
        Panel.fit(
            f"[bold cyan]⚡ LLM-Router Classifier Evaluation Benchmark[/bold cyan]\n"
            f"[dim]Total Test Prompts: {len(dataset)} | Mode: Rule-Based Heuristic Mock[/dim]",
            border_style="cyan"
        )
    )

    results_table = Table(title="Prompt-Level Routing Decisions", show_header=True, header_style="bold magenta")
    results_table.add_column("ID", style="dim", width=5)
    results_table.add_column("Category", width=14)
    results_table.add_column("Prompt Preview", width=42)
    results_table.add_column("Expected", justify="center", width=10)
    results_table.add_column("Predicted", justify="center", width=10)
    results_table.add_column("Score", justify="right", width=7)
    results_table.add_column("Status", justify="center", width=8)

    correct = 0
    tp_cheap = 0  # True Cheap
    fp_cheap = 0
    fn_cheap = 0
    tp_frontier = 0  # True Frontier
    fp_frontier = 0
    fn_frontier = 0

    mismatches = []

    for item in dataset:
        p_id = item["id"]
        category = item["category"]
        prompt = item["prompt"]
        expected = item["expected_tier"].lower()

        # Classify
        res = classifier.classify([ChatMessage(role="user", content=prompt)])
        predicted = res.tier.value.lower()

        is_match = (predicted == expected)
        if is_match:
            correct += 1
            status_str = "[green]✓ PASS[/green]"
        else:
            status_str = "[red]✗ FAIL[/red]"
            mismatches.append({
                "id": p_id,
                "prompt": prompt,
                "expected": expected,
                "predicted": predicted,
                "score": res.score,
                "reasons": res.reasons
            })

        # Update confusion metrics
        if expected == "cheap" and predicted == "cheap":
            tp_cheap += 1
        elif expected == "cheap" and predicted == "frontier":
            fn_cheap += 1
            fp_frontier += 1
        elif expected == "frontier" and predicted == "frontier":
            tp_frontier += 1
        elif expected == "frontier" and predicted == "cheap":
            fn_frontier += 1
            fp_cheap += 1

        exp_color = "green" if expected == "cheap" else "purple"
        pred_color = "green" if predicted == "cheap" else "purple"

        preview = prompt[:38] + ("..." if len(prompt) > 38 else "")
        results_table.add_row(
            p_id,
            category,
            preview,
            f"[{exp_color}]{expected.upper()}[/{exp_color}]",
            f"[{pred_color}]{predicted.upper()}[/{pred_color}]",
            f"{res.score:.2f}",
            status_str
        )

    console.print(results_table)

    total = len(dataset)
    accuracy = (correct / total) * 100.0 if total > 0 else 0.0

    # Cheap metrics
    prec_cheap = tp_cheap / (tp_cheap + fp_cheap) if (tp_cheap + fp_cheap) > 0 else 0.0
    rec_cheap = tp_cheap / (tp_cheap + fn_cheap) if (tp_cheap + fn_cheap) > 0 else 0.0
    f1_cheap = 2 * (prec_cheap * rec_cheap) / (prec_cheap + rec_cheap) if (prec_cheap + rec_cheap) > 0 else 0.0

    # Frontier metrics
    prec_front = tp_frontier / (tp_frontier + fp_frontier) if (tp_frontier + fp_frontier) > 0 else 0.0
    rec_front = tp_frontier / (tp_frontier + fn_frontier) if (tp_frontier + fn_frontier) > 0 else 0.0
    f1_front = 2 * (prec_front * rec_front) / (prec_front + rec_front) if (prec_front + rec_front) > 0 else 0.0

    summary_table = Table(title="Aggregate Routing Metrics", show_header=True, header_style="bold blue")
    summary_table.add_column("Metric", style="bold")
    summary_table.add_column("Value", justify="right")

    summary_table.add_row("Total Prompts", str(total))
    summary_table.add_row("Correctly Routed", f"{correct} / {total}")
    summary_table.add_row("Overall Accuracy", f"{accuracy:.1f}%")
    summary_table.add_row("Cheap Tier Precision", f"{prec_cheap * 100:.1f}%")
    summary_table.add_row("Cheap Tier Recall", f"{rec_cheap * 100:.1f}%")
    summary_table.add_row("Cheap Tier F1-Score", f"{f1_cheap:.3f}")
    summary_table.add_row("Frontier Tier Precision", f"{prec_front * 100:.1f}%")
    summary_table.add_row("Frontier Tier Recall", f"{rec_front * 100:.1f}%")
    summary_table.add_row("Frontier Tier F1-Score", f"{f1_front:.3f}")

    console.print(summary_table)

    if mismatches:
        console.print("\n[yellow]⚠️  Misclassified Prompts Analysis:[/yellow]")
        for m in mismatches:
            console.print(f"[bold]{m['id']}[/bold]: Expected [bold]{m['expected']}[/bold], got [bold]{m['predicted']}[/bold] (score={m['score']:.2f})")
            console.print(f"  Prompt: \"{m['prompt']}\"")
            console.print(f"  Reasons: {', '.join(m['reasons'])}\n")
    else:
        console.print("\n[bold green]🎉 Perfect 100% Routing Alignment on Benchmark Set![/bold green]\n")


if __name__ == "__main__":
    run_benchmark()
