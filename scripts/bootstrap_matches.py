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

OUTPUT_PATH = Path(__file__).resolve().parent.parent / "matches.json"


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


def convert_event(event):
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

        "highlights": {
            "soop": None,
            "chzzk": None,
            "youtube": None
        }
    }


def main():
    matches_by_id = {}

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

            converted = convert_event(event)

            # 같은 경기 ID가 여러 페이지에 있어도 한 번만 저장
            matches_by_id[converted["id"]] = converted

        print(
            f"  → 현재까지 {len(matches_by_id)}개 "
            f"{TARGET_YEAR} 경기 확보"
        )

        older_token = schedule.get("pages", {}).get("older")

        # 더 과거 페이지가 없음
        if not older_token:
            break

        # 이미 2025년 이하 데이터만 나오는 페이지까지 도달했다면 종료
        if years_on_page and max(years_on_page) < TARGET_YEAR:
            break

        page_token = older_token
        page_number += 1

        # API 이상으로 무한 반복되는 상황 방지
        if page_number > 20:
            print("페이지가 너무 많아 안전을 위해 중단합니다.")
            break

    matches = list(matches_by_id.values())

    # 시간순 정렬
    matches.sort(key=lambda m: m["start_time"])

    output = {
        "matches": matches
    }

    with open(
        OUTPUT_PATH,
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
    print(f"{TARGET_YEAR} LCK Bootstrap 완료")
    print(f"총 경기 수: {len(matches)}")
    print(f"파일: {OUTPUT_PATH}")
    print("==============================")


if __name__ == "__main__":
    main()