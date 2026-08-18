import requests
import json
from pathlib import Path
from datetime import datetime

API_URL = "https://esports-api.lolesports.com/persisted/gw/getSchedule"

HEADERS = {
    "x-api-key": "0TvQnueqKa5mxJntVWt0w4LpLfEkrV1Ta8rQBb9Z"
}

LEAGUE_ID = "98767991310872058"
TARGET_YEAR = 2026

MATCHES_PATH = Path(__file__).resolve().parent.parent / "matches.json"


def fetch_schedule(page_token=None):
    params = {
        "hl": "ko-KR",
        "leagueId": LEAGUE_ID
    }

    if page_token:
        params["pageToken"] = page_token

    response = requests.get(
        API_URL,
        headers=HEADERS,
        params=params,
        timeout=20
    )

    response.raise_for_status()
    return response.json()


def get_year(start_time):
    return datetime.fromisoformat(
        start_time.replace("Z", "+00:00")
    ).year


def load_existing_matches():
    if not MATCHES_PATH.exists():
        return {}

    with open(MATCHES_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    return {
        match["id"]: match
        for match in data.get("matches", [])
    }


def convert_event(event, existing_match=None):
    match = event["match"]
    teams = match["teams"]

    team_a = teams[0]
    team_b = teams[1]

    status = event["state"]
    match_id = match["id"]

    score_a = None
    score_b = None

    if status == "completed":
        if team_a.get("result"):
            score_a = team_a["result"].get("gameWins")

        if team_b.get("result"):
            score_b = team_b["result"].get("gameWins")

    full_vod = None

    if "hasVod" in match.get("flags", []):
        full_vod = f"https://lolesports.com/vod/{match_id}/1"

    # 기존 하이라이트 링크가 있으면 보존
    highlights = {
        "soop": None,
        "chzzk": None,
        "youtube": None
    }

    if existing_match:
        existing_highlights = existing_match.get("highlights", {})

        highlights["soop"] = existing_highlights.get("soop")
        highlights["chzzk"] = existing_highlights.get("chzzk")
        highlights["youtube"] = existing_highlights.get("youtube")

    return {
        "id": match_id,
        "start_time": event["startTime"],
        "status": status,

        "competition": event["league"]["name"],
        "category": event["blockName"],
        "best_of": match["strategy"]["count"],

        "team_a": team_a["code"],
        "team_b": team_b["code"],

        "score_a": score_a,
        "score_b": score_b,

        "full_vod": full_vod,

        "highlights": highlights
    }


def main():
    existing_matches = load_existing_matches()

    updated_matches = {}
    page_token = None
    page_number = 1

    while True:
        print(f"{page_number}페이지 불러오는 중...")

        data = fetch_schedule(page_token)

        schedule = data["data"]["schedule"]
        events = schedule["events"]

        years_on_page = []

        for event in events:
            if event.get("type") != "match":
                continue

            if event.get("league", {}).get("slug") != "lck":
                continue

            year = get_year(event["startTime"])
            years_on_page.append(year)

            if year != TARGET_YEAR:
                continue

            match_id = event["match"]["id"]

            converted = convert_event(
                event,
                existing_matches.get(match_id)
            )

            updated_matches[match_id] = converted

        print(
            f"  → 현재까지 {len(updated_matches)}개 "
            f"{TARGET_YEAR} 경기 확보"
        )

        older_token = schedule.get("pages", {}).get("older")

        if not older_token:
            break

        if years_on_page and max(years_on_page) < TARGET_YEAR:
            break

        page_token = older_token
        page_number += 1

        if page_number > 20:
            print("페이지가 너무 많아 안전을 위해 중단합니다.")
            break

    matches = list(updated_matches.values())
    matches.sort(key=lambda m: m["start_time"])

    output = {
        "matches": matches
    }

    # 기존 파일과 내용이 완전히 같으면 쓰지 않음
    old_output = None

    if MATCHES_PATH.exists():
        with open(MATCHES_PATH, "r", encoding="utf-8") as f:
            old_output = json.load(f)

    if old_output == output:
        print()
        print("변경사항 없음")
        return

    with open(
        MATCHES_PATH,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            output,
            f,
            ensure_ascii=False,
            indent=2
        )

    print()
    print("==============================")
    print("matches.json 업데이트 완료")
    print(f"총 경기 수: {len(matches)}")
    print("==============================")


if __name__ == "__main__":
    main()