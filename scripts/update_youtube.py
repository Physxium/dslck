import json
import re
from pathlib import Path

import yt_dlp


PLAYLIST_URL = (
    "https://youtube.com/playlist?"
    "list=PLIWtfvmBcNocpzEpM2WLn-Unptgj4qTD3"
)

MATCHES_PATH = Path(__file__).resolve().parent.parent / "matches.json"

# 2026 LCK 매치 1 시작점
REGULAR_SEASON_START = "2026-04-01T00:00:00Z"


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


def fetch_playlist():
    options = {
        "quiet": True,
        "extract_flat": True,
        "skip_download": True,
    }

    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info(
            PLAYLIST_URL,
            download=False
        )

    return info.get("entries", [])


def main():
    data = load_matches()
    matches = data.get("matches", [])

    playlist = fetch_playlist()

    print(f"YouTube 재생목록 영상 수: {len(playlist)}")
    print()

    # 2026 LCK 정규리그만 추출
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

    for video in playlist:
        video_id = video.get("id")
        title = video.get("title")

        if not video_id or not title:
            continue

        match_number = extract_match_number(title)

        if match_number is None:
            continue

        index = match_number - 1

        if index < 0 or index >= len(regular_matches):
            print(
                f"[SKIP] 매치 {match_number}: "
                f"경기 목록 범위 밖"
            )
            continue

        match = regular_matches[index]

        team_a = match["team_a"]
        team_b = match["team_b"]

        # 매치 번호뿐 아니라 팀까지 일치하는지 검증
        if not (
            contains_team(title, team_a)
            and contains_team(title, team_b)
        ):
            print(
                f"[MISMATCH] 매치 {match_number}: "
                f"JSON={team_a} vs {team_b}"
            )
            print(f"           YouTube={title}")

            mismatch_count += 1
            continue

        youtube_url = (
            f"https://www.youtube.com/watch?v={video_id}"
        )

        # 기존 링크가 있더라도 올바른 값으로 덮어씀
        match.setdefault("highlights", {})
        old_url = match["highlights"].get("youtube")

        match["highlights"]["youtube"] = youtube_url

        if old_url != youtube_url:
            updated_count += 1

            print(
                f"[MATCH] 매치 {match_number}: "
                f"{team_a} vs {team_b}"
            )

    save_matches(data)

    print()
    print("==============================")
    print(f"YouTube 링크 변경: {updated_count}개")
    print(f"팀 불일치: {mismatch_count}개")
    print("==============================")


if __name__ == "__main__":
    main()