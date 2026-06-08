import typer

from vlr_analytics.api.main import run_api
from vlr_analytics.assets.build import build_assets
from vlr_analytics.marts.build import build_all_marts
from vlr_analytics.modeling.build import build_all_models
from vlr_analytics.processing.transform import process_all
from vlr_analytics.scraping.vlr import scrape_all

app = typer.Typer(help="VLR Analytics pipeline")


@app.command()
def scrape() -> None:
    """Scrape raw VLR tables."""
    scrape_all()


@app.command()
def process() -> None:
    """Clean raw files into stable processed datasets."""
    process_all()


@app.command("build-marts")
def build_marts() -> None:
    """Build analytical marts from processed data."""
    build_all_marts()


@app.command("model")
def model() -> None:
    """Build descriptive modeling outputs and insights."""
    build_all_models()


@app.command("assets")
def assets(download_agents: bool = typer.Option(False, help="Download playable agent PNG icons from valorant-api.com.")) -> None:
    """Build local asset registries for agents and teams."""
    build_assets(download_agents=download_agents)


@app.command("full-run")
def full_run(
    skip_scrape: bool = typer.Option(False, help="Use existing raw files."),
    download_agents: bool = typer.Option(False, help="Download agent PNG icons during the run."),
) -> None:
    """Run the full pipeline."""
    if not skip_scrape:
        scrape_all()
    process_all()
    build_all_marts()
    build_all_models()
    build_assets(download_agents=download_agents)


@app.command("ranker-paths")
def ranker_paths() -> None:
    """Print entrypoints for the merged role-ranker Streamlit apps."""
    typer.echo("Tournament ranker: streamlit run apps/role_ranker_streamlit/tournament_app.py")
    typer.echo("Legacy Elo ranker: streamlit run apps/role_ranker_streamlit/elo_app.py")
    typer.echo("Playoff odds Streamlit: streamlit run apps/playoff_odds_streamlit/app.py")


@app.command("api")
def api(host: str = "127.0.0.1", port: int = 8000) -> None:
    """Start FastAPI backend."""
    run_api(host=host, port=port)


if __name__ == "__main__":
    app()
