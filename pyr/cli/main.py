"""PYR CLI — AI-native narrative game generator."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

app = typer.Typer(
    name="pyr",
    help="PYR — AI-native narrative game generator. Prompt → Playable EXE.",
    add_completion=False,
)
console = Console()

GAMES_DIR = Path("games")


def _games_dir() -> Path:
    GAMES_DIR.mkdir(exist_ok=True)
    return GAMES_DIR


def _progress_printer(msg: str) -> None:
    console.print(f"  [dim]{msg}[/dim]")


@app.command("generate-game")
def generate_game(
    prompt: str = typer.Argument(help="Natural language prompt describing the game"),
    output: Path = typer.Option(None, "--output", "-o", help="Output directory (default: games/<title>)"),
    refine_cycles: int = typer.Option(3, "--refine", "-r", help="Max auto-refinement cycles"),
    skip_test: bool = typer.Option(False, "--skip-test", help="Skip headless testing"),
):
    """Generate a complete narrative game from a text prompt."""
    from pyr.generator.pipeline import GenerationPipeline

    console.print(Panel.fit(f"[bold magenta]PYR Game Generator[/bold magenta]\n[dim]Prompt: {prompt}[/dim]"))

    out_dir = output or _games_dir()

    pipeline = GenerationPipeline(
        output_dir=out_dir,
        max_refinement_cycles=0 if skip_test else refine_cycles,
        progress_callback=_progress_printer,
    )

    try:
        game = pipeline.run(prompt)
        game_dir = out_dir / _slugify(game.title)
        console.print(f"\n[bold green]Done![/bold green] Game '{game.title}' saved to {game_dir}")
        console.print(f"  Scenes:     {len(game.scenes)}")
        console.print(f"  Characters: {len(game.characters)}")
        endings = sum(1 for s in game.scenes.values() if s.is_ending)
        console.print(f"  Endings:    {endings}")
        console.print(f"\nRun with: [bold]pyr run-game {game_dir}[/bold]")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(1)


@app.command("run-game")
def run_game(
    game_dir: Path = typer.Argument(help="Path to game directory containing game.json"),
    assets: Path = typer.Option(None, "--assets", "-a", help="Assets directory override"),
):
    """Launch a generated game in the pygame runtime."""
    game_json = game_dir / "game.json"
    if not game_json.exists():
        console.print(f"[red]Error:[/red] No game.json found in {game_dir}")
        raise typer.Exit(1)

    from pyr.models.game import GameDefinition
    from pyr.runtime.engine import GameEngine

    data = json.loads(game_json.read_text(encoding="utf-8"))
    game = GameDefinition.model_validate(data)

    assets_dir = assets or game_dir / "assets"
    engine = GameEngine(game, assets_dir=assets_dir if assets_dir.exists() else None)

    console.print(f"Launching [bold]{game.title}[/bold]...")
    console.print("  [dim]F5: Quicksave  F9: Quickload  J: Journal  ESC: Quit[/dim]")
    engine.run()


@app.command("validate-game")
def validate_game(
    game_dir: Path = typer.Argument(help="Path to game directory or game.json file"),
):
    """Validate a game definition for structural errors."""
    game_json = game_dir / "game.json" if game_dir.is_dir() else game_dir
    if not game_json.exists():
        console.print(f"[red]Error:[/red] {game_json} not found")
        raise typer.Exit(1)

    from pyr.models.game import GameDefinition
    from pyr.pipeline.validator import GameValidator

    data = json.loads(game_json.read_text(encoding="utf-8"))
    game = GameDefinition.model_validate(data)
    validator = GameValidator(game)

    console.print(validator.report())


@app.command("run-headless-tests")
def run_headless_tests(
    game_dir: Path = typer.Argument(help="Path to game directory or game.json file"),
    playthroughs: int = typer.Option(20, "--playthroughs", "-n"),
    replay: bool = typer.Option(False, "--replay", help="Print a deterministic replay log"),
):
    """Run headless playthrough tests and report coverage and issues."""
    game_json = game_dir / "game.json" if game_dir.is_dir() else game_dir
    if not game_json.exists():
        console.print(f"[red]Error:[/red] {game_json} not found")
        raise typer.Exit(1)

    from pyr.models.game import GameDefinition
    from pyr.pipeline.tester import HeadlessTester

    data = json.loads(game_json.read_text(encoding="utf-8"))
    game = GameDefinition.model_validate(data)

    tester = HeadlessTester(game, playthroughs=playthroughs)

    console.print(f"Running {playthroughs} playthroughs...")
    results = tester.run()

    table = Table(title="Test Results")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="bold")
    table.add_row("Playthroughs", str(results.playthrough_count))
    table.add_row("Scene Coverage", f"{results.scene_coverage:.0%}")
    table.add_row("Scenes Reached", str(len(results.scenes_reached)))
    table.add_row("Endings Reached", str(len(results.endings_reached)))
    table.add_row("Issues Found", str(len(results.issues)))
    console.print(table)

    if results.issues:
        console.print("\n[bold yellow]Issues:[/bold yellow]")
        for issue in results.issues:
            console.print(f"  - {issue}")

    if replay:
        console.print("\n[bold]Replay Log:[/bold]")
        log = tester.replay_log()
        for i, entry in enumerate(log):
            console.print(f"  [{i:02d}] {entry['scene']} — {entry['title']}")
            if entry["choices"]:
                console.print(f"       → chose: {entry['choices'][0]}")


@app.command("package-exe")
def package_exe(
    game_dir: Path = typer.Argument(help="Path to game directory"),
    output: Path = typer.Option(None, "--output", "-o"),
):
    """Package a game into a standalone Windows EXE."""
    from pyr.pipeline.packager import GamePackager

    packager = GamePackager(game_dir, output_dir=output)

    console.print(f"Packaging [bold]{game_dir.name}[/bold] into EXE...")
    try:
        exe_path = packager.package(progress_callback=_progress_printer)
        console.print(f"\n[bold green]Success![/bold green] EXE built at: {exe_path}")
    except Exception as e:
        console.print(f"[bold red]Packaging failed:[/bold red] {e}")
        raise typer.Exit(1)


@app.command("generate-assets")
def generate_assets(
    game_dir: Path = typer.Argument(help="Path to game directory containing game.json"),
    output: Path = typer.Option(None, "--output", "-o", help="Output path for manifest (default: <game_dir>/assets_manifest.json)"),
):
    """Generate an asset manifest with image/audio generation prompts for a game."""
    game_json = game_dir / "game.json"
    if not game_json.exists():
        console.print(f"[red]Error:[/red] No game.json found in {game_dir}")
        raise typer.Exit(1)

    from pyr.generator.asset_manifest import generate_asset_manifest
    from pyr.models.game import GameDefinition

    data = json.loads(game_json.read_text(encoding="utf-8"))
    game = GameDefinition.model_validate(data)

    console.print(Panel.fit(
        f"[bold magenta]PYR Asset Manifest Generator[/bold magenta]\n"
        f"[dim]Game: {game.title}[/dim]\n"
        f"[dim]Scenes: {len(game.scenes)}  Characters: {len(game.characters)}[/dim]"
    ))

    try:
        manifest = generate_asset_manifest(
            game,
            game_dir=str(game_dir),
            progress_callback=_progress_printer,
        )
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(1)

    out_path = output or game_dir / "assets_manifest.json"
    out_path.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")

    summary = manifest.summary()
    console.print(f"\n[bold green]Asset manifest saved to:[/bold green] {out_path}\n")

    table = Table(title="Assets to Generate")
    table.add_column("Type", style="cyan")
    table.add_column("Count", justify="right", style="bold")
    table.add_row("Backgrounds", str(summary["backgrounds"]))
    table.add_row("Portraits", str(summary["portraits"]))
    table.add_row("Music tracks", str(summary["music"]))
    table.add_row("Sound effects", str(summary["sfx"]))
    table.add_row("Character barks", str(summary["barks"]))
    table.add_row("[bold]Total[/bold]", str(summary["total"]))
    console.print(table)

    console.print(
        f"\nReview and edit [bold]{out_path.name}[/bold], then generate each asset "
        f"using its [italic]generation_prompt[/italic].\n"
        f"Place finished files in [bold]{game_dir}/assets/[/bold] matching the filenames in the manifest."
    )


@app.command("list-games")
def list_games(
    games_dir: Path = typer.Option(GAMES_DIR, "--dir", "-d"),
):
    """List all generated games."""
    if not games_dir.exists():
        console.print("No games directory found.")
        return

    table = Table(title="Generated Games")
    table.add_column("Name", style="cyan")
    table.add_column("Scenes", justify="right")
    table.add_column("Characters", justify="right")
    table.add_column("Endings", justify="right")
    table.add_column("Path", style="dim")

    found = False
    for game_json in sorted(games_dir.rglob("game.json")):
        try:
            from pyr.models.game import GameDefinition
            data = json.loads(game_json.read_text(encoding="utf-8"))
            game = GameDefinition.model_validate(data)
            endings = sum(1 for s in game.scenes.values() if s.is_ending)
            table.add_row(
                game.title,
                str(len(game.scenes)),
                str(len(game.characters)),
                str(endings),
                str(game_json.parent),
            )
            found = True
        except Exception:
            table.add_row(str(game_json.parent.name), "?", "?", "?", str(game_json.parent))

    if found:
        console.print(table)
    else:
        console.print("No games found. Run [bold]pyr generate-game \"your prompt\"[/bold] to create one.")


def _slugify(text: str) -> str:
    import re
    return re.sub(r"[^\w-]", "_", text.lower())[:40].strip("_")


if __name__ == "__main__":
    app()
