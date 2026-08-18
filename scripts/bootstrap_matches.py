import requests
import json
from pathlib import Path

API_URL = "https://esports-api.lolesports.com/persisted/gw/getSchedule"

HEADERS = {
    "x-api-key": "0TvQnueqKa5mxJntVWt0w4LpLfEkrV1Ta8rQBb9Z"
}

PARAMS = {
    "hl": "ko-KR",
    "leagueId": "98767991310872058"
}

# 프로젝트 최상위의 matches.json 위치
OUTPUT_PATH = Path(__file__).resolve().parent.parent / "matches.json"


def fetch_schedule():
    response = requests.get(
        API_URL,
        headers=HEADERS,
        params=PARAMS,
        timeout=20
    )
    response.raise_for_status()
    return response.json()


def convert_event(event):
    match = event["match"]
    teams = match["teams"]

    team_a = teams[0]
    team_b = teams[1]

    status = event["state"]

    score_a = None
    score_b = None

    if status == "completed":
        score_a = team_a["result"]["gameWins"]
        score_b = team_b["result"]["gameWins"]

    match_id = match["id"]

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
    data = fetch_schedule()

    events = data["data"]["schedule"]["events"]

    matches = []

    for event in events:
        if event.get("type") != "match":
            continue

        if event["league"]["slug"] != "lck":
            continue

        matches.append(convert_event(event))

    output = {
        "matches": matches
    }

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"{len(matches)}개 경기 저장 완료")
    print(f"파일: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()