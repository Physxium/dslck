import json
import re
from pathlib import Path

import requests


CHANNEL_ID = "9381e7d6816e6d915a44a13c0195b202"

API_URL = (
    f"https://api.chzzk.naver.com/service/v1/channels/"
    f"{CHANNEL_ID}/videos"
)

MATCHES_PATH = Path(__file__).resolve().parent.parent / "matches.json"

REGULAR_SEASON_START = "2026-04-01T00:00:00Z"
CHZZK_REGULAR_SEASON_START = "2026-04-01 00:00:00"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/151.0.0.0 Safari/537.36"
    ),
    "Referer": (
        f"https://chzzk.naver.com/{CHANNEL_ID}/videos"
    ),
    "Accept": "application/json, text/plain, */*",
}


def load_matches():
    with open(MATCHES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_matches(data):
    with open(MATCHES_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def contains_team(title, team):
    pattern = rf"(?<![A-Z0-9]){re.escape(team.upper())}(?![A-Z0-9])"
    return re.search(pattern, title.upper()) is not None


def extract_match_number(title):
    match = re.search(r"매치\s*(\d+)", title)

    if not match:
        return None

    return int(match.group(1))


def fetch_page(page):
    params = {
        "sortType": "LATEST",
        "pagingType": "PAGE",
        "page": page,
        "size": 18,
        "publishDateAt": "",
        "videoType": "UPLOAD",
    }

    response = requests.get(
        API_URL,
        params=params,
        headers=HEADERS,
        timeout=60
    )

    response.raise_for_status()

    return response.json()


def find_video_list(data):
    content = data.get("content")

    if isinstance(content, dict):
        for key in [
            "data",
            "videos",
            "items",
            "videoList",
            "content"
        ]:
            value = content.get(key)

            if isinstance(value, list):
                return value

    if isinstance(content, list):
        return content

    for key in [
        "data",
        "videos",
        "items",
        "videoList"
    ]:
        value = data.get(key)

        if isinstance(value, list):
            return value

    return []


def main():
    data = load_matches()
    matches = data.get("matches", [])

    regular_matches = [
        m for m in matches
        if m.get("status") == "completed"
        and m.get("start_time", "") >= REGULAR_SEASON_START
        and "주 차" in m.get("category", "")
    ]

    regular_matches.sort(
        key=lambda m: m["start_time"]
    )

    print(f"매치 번호 대상 경기 수: {len(regular_matches)}")

    if regular_matches:
        first = regular_matches[0]

        print(
            f"매치 1 기준 확인: "
            f"{first['start_time']} "
            f"{first['team_a']} vs {first['team_b']}"
        )

    print()

    updated_count = 0
    mismatch_count = 0
    found_match_numbers = set()

    page = 0
    max_pages = 100
    stop_search = False

    while page < max_pages:
        print(f"치지직 page {page} 확인 중...")

        try:
            response_data = fetch_page(page)

        except requests.exceptions.RequestException as e:
            print(f"[ERROR] page {page} 요청 실패")
            print(e)
            break

        videos = find_video_list(response_data)

        if not videos:
            print("영상이 없어 종료합니다.")
            break

        for video in videos:
            video_no = video.get("videoNo")
            title = video.get("videoTitle")
            publish_date = video.get("publishDate")

            # 2026 정규리그 시작 이전 영상까지 내려가면 탐색 종료
            if (
                publish_date
                and publish_date < CHZZK_REGULAR_SEASON_START
            ):
                print(
                    "2026 정규리그 이전 영상에 도달해 "
                    "탐색을 종료합니다."
                )

                stop_search = True
                break

            if not video_no or not title:
                continue

            # 매치 전체 하이라이트만 대상
            if "매치" not in title:
                continue

            if "하이라이트" not in title:
                continue

            if "2026 LCK" not in title:
                continue

            match_number = extract_match_number(title)

            if match_number is None:
                continue

            index = match_number - 1

            if index < 0 or index >= len(regular_matches):
                continue

            match = regular_matches[index]

            team_a = match["team_a"]
            team_b = match["team_b"]

            if not (
                contains_team(title, team_a)
                and contains_team(title, team_b)
            ):
                print(
                    f"[MISMATCH] 매치 {match_number}: "
                    f"JSON={team_a} vs {team_b}"
                )
                print(
                    f"           CHZZK={title}"
                )

                mismatch_count += 1
                continue

            chzzk_url = (
                f"https://chzzk.naver.com/video/{video_no}"
            )

            match.setdefault("highlights", {})

            old_url = match["highlights"].get("chzzk")

            match["highlights"]["chzzk"] = chzzk_url

            found_match_numbers.add(match_number)

            if old_url != chzzk_url:
                updated_count += 1

                print(
                    f"[MATCH] 매치 {match_number}: "
                    f"{team_a} vs {team_b}"
                )

        if stop_search:
            break

        if len(found_match_numbers) >= len(regular_matches):
            print(
                "모든 정규리그 매치 하이라이트를 찾았습니다."
            )
            break

        page += 1

    save_matches(data)

    print()
    print("==============================")
    print(f"치지직 링크 변경: {updated_count}개")
    print(
        f"이번 실행에서 찾은 매치: "
        f"{len(found_match_numbers)}개"
    )
    print(f"팀 불일치: {mismatch_count}개")
    print("==============================")


if __name__ == "__main__":
    main()