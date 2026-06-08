from __future__ import annotations

import typer

from playoff_odds.simulation.run_simulation import main as run_simulation_main
from playoff_odds.simulation.run_what_if import main as run_what_if_main
from playoff_odds.simulation.cli import main as console_main

app = typer.Typer(help="VCT playoff odds simulation tools")


@app.command("simulate")
def simulate() -> None:
    """Run the original playoff simulation CLI.

    This command preserves the original argparse interface, so pass arguments after
    the command exactly as documented in the original project.
    """
    run_simulation_main()


@app.command("what-if")
def what_if() -> None:
    """Run the deterministic what-if snapshot CLI."""
    run_what_if_main()


@app.command("console")
def console() -> None:
    """Run the original console for persisted match updates."""
    console_main()


if __name__ == "__main__":
    app()
