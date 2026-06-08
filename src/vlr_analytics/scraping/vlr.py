import os
import time
import warnings
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from vlr_analytics.config import EVENTS, RAW_MATRIX, RAW_SUMMARY
from vlr_analytics.utils import clean_text, normalize_map_name, write_csv


def agent_from_src(src: str | None) -> str:
    if not src:
        return "unknown"
    return src.split("/")[-1].replace(".png", "").strip().lower()


def scrape_event_agents(event_name: str, url: str) -> tuple[pd.DataFrame, list[str]]:
    response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    table = soup.find("table")
    if table is None:
        raise ValueError(f"No table found for {event_name}")
    header_row = table.find("tr")
    if header_row is None:
        raise ValueError(f"No header row found for {event_name}")

    agents = [agent_from_src(img.get("src")) for img in header_row.select("th.mod-center img[src*='/agents/']")]
    records: list[dict[str, object]] = []
    map_names: list[str] = []

    for row in table.select("tr.pr-global-row"):
        cells = row.find_all("td")
        if len(cells) < 4 + len(agents):
            continue
        raw_map = clean_text(cells[0].get_text(" ", strip=True))
        map_name = normalize_map_name(raw_map)
        if map_name != "All Maps":
            map_names.append(map_name)
        for agent, cell in zip(agents, cells[4 : 4 + len(agents)], strict=False):
            records.append({
                "event": event_name,
                "raw_map": raw_map,
                "raw_maps_played": clean_text(cells[1].get_text(strip=True)),
                "raw_atk_win_rate": clean_text(cells[2].get_text(strip=True)),
                "raw_def_win_rate": clean_text(cells[3].get_text(strip=True)),
                "agent": agent,
                "raw_pick_rate": clean_text(cell.get_text(strip=True)),
            })
    return pd.DataFrame(records), sorted(set(map_names))


def extract_map_from_container(container) -> str | None:
    try:
        return normalize_map_name(container.locator("th").first.inner_text(timeout=5000))
    except Exception:
        return None


def scrape_matrix_container(event_name: str, map_name: str, container) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    agent_imgs = container.locator("img[src*='/agents/']")
    agents = [agent_from_src(agent_imgs.nth(i).get_attribute("src")) for i in range(agent_imgs.count())]
    if not agents:
        return records

    rows = container.locator("tr")
    current_team: str | None = None
    for r in range(rows.count()):
        row = rows.nth(r)
        cells = row.locator("td")
        cell_count = cells.count()
        if cell_count < len(agents) + 1:
            continue
        row_label = clean_text(cells.nth(0).inner_text(timeout=5000))
        if not row_label:
            continue
        if row_label.startswith("vs."):
            if current_team is None:
                continue
            opponent = row_label.replace("vs.", "").strip()
            start = cell_count - len(agents)
            for idx, agent in enumerate(agents):
                class_attr = cells.nth(start + idx).get_attribute("class") or ""
                if "mod-picked" in class_attr or "mod-picked-lite" in class_attr:
                    records.append({"event": event_name, "map": map_name, "team": current_team, "opponent": opponent, "agent": agent})
        else:
            current_team = row_label
    return records


def _playwright_timeout_ms() -> int:
    raw_value = os.getenv("VLR_PLAYWRIGHT_TIMEOUT_MS", "90000")
    try:
        return int(raw_value)
    except ValueError:
        warnings.warn(
            f"Invalid VLR_PLAYWRIGHT_TIMEOUT_MS={raw_value!r}; using 90000 ms.",
            RuntimeWarning,
            stacklevel=2,
        )
        return 90000


def _goto_vlr_page(page, event_name: str, url: str, timeout_ms: int) -> bool:
    """Navigate to a VLR page without relying on Playwright's fragile networkidle state.

    VLR pages can keep background requests open, so `wait_until="networkidle"` may
    timeout even when the HTML needed by the scraper is already available. We first
    wait for the DOM, then explicitly wait for the matrix selector. If an event is
    temporarily unavailable, the caller can skip only that matrix instead of failing
    the whole scrape run.
    """

    last_error: Exception | None = None
    for wait_until in ("domcontentloaded", "load"):
        try:
            page.goto(url, wait_until=wait_until, timeout=timeout_ms)
            page.wait_for_selector(".pr-matrix-map", timeout=min(timeout_ms, 20000))
            return True
        except PlaywrightTimeoutError as exc:
            last_error = exc
            warnings.warn(
                f"[{event_name}] Playwright timeout with wait_until={wait_until!r}; retrying/falling back.",
                RuntimeWarning,
                stacklevel=2,
            )

    warnings.warn(
        f"[{event_name}] Matrix page could not be loaded after retries; "
        f"matrix rows will be empty for this event. URL: {url}. Last error: {last_error}",
        RuntimeWarning,
        stacklevel=2,
    )
    return False


def scrape_event_matrix(event_name: str, url: str) -> pd.DataFrame:
    records: list[dict[str, str]] = []
    timeout_ms = _playwright_timeout_ms()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page(user_agent="Mozilla/5.0")
            page.set_default_timeout(timeout_ms)
            page.set_default_navigation_timeout(timeout_ms)

            if not _goto_vlr_page(page, event_name, url, timeout_ms):
                return pd.DataFrame(records)

            containers = page.locator(".pr-matrix-map")
            for c in range(containers.count()):
                container = containers.nth(c)
                map_name = extract_map_from_container(container) or f"unknown_map_{c + 1}"
                records.extend(scrape_matrix_container(event_name, map_name, container))
        finally:
            browser.close()
    return pd.DataFrame(records)


def scrape_all(output_dir: Path | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    if output_dir is None:
        summary_path, matrix_path = RAW_SUMMARY, RAW_MATRIX
    else:
        summary_path, matrix_path = output_dir / RAW_SUMMARY.name, output_dir / RAW_MATRIX.name

    summary_dfs: list[pd.DataFrame] = []
    matrix_dfs: list[pd.DataFrame] = []
    start = time.time()
    for idx, (event_name, url) in enumerate(EVENTS.items(), start=1):
        event_summary, _ = scrape_event_agents(event_name, url)
        event_matrix = scrape_event_matrix(event_name, url)
        summary_dfs.append(event_summary)
        matrix_dfs.append(event_matrix)
        print(f"[{idx}/{len(EVENTS)}] {event_name} scraped in {time.time() - start:.1f}s")

    summary = pd.concat(summary_dfs, ignore_index=True)
    matrix = pd.concat(matrix_dfs, ignore_index=True)
    write_csv(summary, summary_path)
    write_csv(matrix, matrix_path)
    return summary, matrix
