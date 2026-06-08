import re
import time
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright


EVENTS = {
    "americas_stage_1": "https://www.vlr.gg/event/agents/2860/vct-2026-americas-stage-1",
    "china_stage_1": "https://www.vlr.gg/event/agents/2864/vct-2026-china-stage-1",
    "pacific_stage_1": "https://www.vlr.gg/event/agents/2775/vct-2026-pacific-stage-1",
    "emea_stage_1": "https://www.vlr.gg/event/agents/2863/vct-2026-emea-stage-1",
}


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", str(value)).strip()


def agent_from_src(src: str) -> str:
    return src.split("/")[-1].replace(".png", "").strip().lower()


def normalize_raw_map(raw_map: str) -> str:
    raw_map = clean_text(raw_map)

    if raw_map == "" or raw_map.lower() == "nan":
        return "All Maps"

    # Ex: "L Lotus" -> "Lotus"
    parts = raw_map.split(" ", 1)
    if len(parts) == 2 and len(parts[0]) == 1:
        return parts[1]

    return raw_map


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

    agents = [
        agent_from_src(img["src"])
        for img in header_row.select("th.mod-center img[src*='/agents/']")
    ]

    records = []
    map_names = []

    for row in table.select("tr.pr-global-row"):
        cells = row.find_all("td")
        if len(cells) < 4 + len(agents):
            continue

        raw_map = clean_text(cells[0].get_text(" ", strip=True))
        map_name = normalize_raw_map(raw_map)

        if map_name != "All Maps":
            map_names.append(map_name)

        for agent, cell in zip(agents, cells[4 : 4 + len(agents)]):
            records.append(
                {
                    "event": event_name,
                    "raw_map": raw_map,
                    "raw_maps_played": clean_text(cells[1].get_text(strip=True)),
                    "raw_atk_win_rate": clean_text(cells[2].get_text(strip=True)),
                    "raw_def_win_rate": clean_text(cells[3].get_text(strip=True)),
                    "agent": agent,
                    "raw_pick_rate": clean_text(cell.get_text(strip=True)),
                }
            )

    return pd.DataFrame(records), map_names


def extract_map_from_container(container) -> str | None:
    try:
        header_text = clean_text(container.locator("th").first.inner_text(timeout=5000))
    except Exception:
        return None

    return normalize_raw_map(header_text)


def scrape_matrix_container(
    event_name: str,
    map_name: str,
    container,
) -> list[dict]:
    records = []

    agent_imgs = container.locator("img[src*='/agents/']")
    agents = [
        agent_from_src(agent_imgs.nth(i).get_attribute("src"))
        for i in range(agent_imgs.count())
    ]

    if not agents:
        return records

    rows = container.locator("tr")
    current_team = None

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
            agent_cells_start = cell_count - len(agents)

            for agent_index, agent in enumerate(agents):
                cell = cells.nth(agent_cells_start + agent_index)
                class_attr = cell.get_attribute("class") or ""

                picked = int(
                    "mod-picked" in class_attr
                    or "mod-picked-lite" in class_attr
                )

                if picked == 1:
                    records.append(
                        {
                            "event": event_name,
                            "map": map_name,
                            "team": current_team,
                            "opponent": opponent,
                            "agent": agent,
                        }
                    )
        else:
            current_team = row_label

    return records


def scrape_event_matrix(
    event_name: str,
    url: str,
    map_names: list[str],
) -> pd.DataFrame:
    records = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent="Mozilla/5.0")
        page.goto(url, wait_until="networkidle", timeout=60000)

        containers = page.locator(".pr-matrix-map")
        container_count = containers.count()

        print(event_name, "matrix containers:", container_count)

        for c in range(container_count):
            container = containers.nth(c)

            map_name = extract_map_from_container(container)
            if map_name is None:
                map_name = f"unknown_map_{c + 1}"

            map_records = scrape_matrix_container(event_name, map_name, container)
            records.extend(map_records)

            print(
                f"  [{c + 1}/{container_count}] {map_name}: "
                f"{len(map_records)} picked-agent rows"
            )

        browser.close()

    return pd.DataFrame(records)


def main() -> None:
    Path("data/raw").mkdir(parents=True, exist_ok=True)

    summary_dfs = []
    matrix_dfs = []

    start_time = time.time()
    total_events = len(EVENTS)

    for i, (event_name, url) in enumerate(EVENTS.items(), start=1):
        event_start = time.time()

        summary_df, map_names = scrape_event_agents(event_name, url)
        matrix_df = scrape_event_matrix(event_name, url, map_names)

        summary_dfs.append(summary_df)
        matrix_dfs.append(matrix_df)

        elapsed = time.time() - start_time
        avg_time_per_event = elapsed / i
        remaining_events = total_events - i
        eta = remaining_events * avg_time_per_event
        event_time = time.time() - event_start

        print(
            f"[{i}/{total_events}] {event_name} done in {event_time:.1f}s | "
            f"elapsed: {elapsed:.1f}s | ETA: {eta:.1f}s"
        )

    summary_df = pd.concat(summary_dfs, ignore_index=True)
    matrix_df = pd.concat(matrix_dfs, ignore_index=True)

    summary_df.to_csv("data/raw/vlr_agents_summary_raw.csv", index=False)
    matrix_df.to_csv("data/raw/vlr_agents_matrix_raw.csv", index=False)

    print(f"\nSaved summary raw dataset: {summary_df.shape[0]} rows")
    print(f"Saved matrix raw dataset: {matrix_df.shape[0]} rows")


if __name__ == "__main__":
    main()