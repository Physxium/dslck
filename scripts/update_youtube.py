import json
import re

from pathlib import Path
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import yt_dlp


# =========================================================
# 설정
# =========================================================

MATCHES_PATH = (
    Path(__file__).resolve().parent.parent
    / "matches.json"
)

KST = ZoneInfo("Asia/Seoul")

MATCHING_START = datetime(
    2026,
    4,
    1,
    tzinfo=timezone.utc
)

RECENT_LIMIT = timedelta(hours=30)

YOUTUBE_PLAYLIST = (
    "https://www.youtube.com/playlist"
    "?list=PLIWtfvmBcNocpzEpM2WLn-Unptgj4qTD3"
)


# =========================================================
# matches.json
# =========================================================

def load_matches():

    with open(
        MATCHES_PATH,
        "r",
        encoding="utf-8"
    ) as f:
        return json.load(f)


def save_matches(data):

    with open(
        MATCHES_PATH,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2
        )


# =========================================================
# 시간
# =========================================================

def parse_match_time(value):

    return datetime.fromisoformat(
        value.replace("Z", "+00:00")
    )


# =========================================================
# 팀명 판정
# =========================================================

def contains_team(title, team):

    pattern = (
        rf"(?<![A-Z0-9])"
        rf"{re.escape(team.upper())}"
        rf"(?![A-Z0-9])"
    )

    return bool(
        re.search(
            pattern,
            title.upper()
        )
    )


def teams_match(title, match):

    return (
        contains_team(
            title,
            match["team_a"]
        )
        and
        contains_team(
            title,
            match["team_b"]
        )
    )


# =========================================================
# 제목 판정
# =========================================================

def is_regular_season(match):

    return (
        "주 차"
        in match.get("category", "")
    )


def get_regular_match_number(title):

    match = re.search(
        r"매치\s*(\d+)\s*하이라이트",
        title
    )

    if not match:
        return None

    return int(
        match.group(1)
    )


def is_postseason_highlight(title):

    # 반드시 매치 하이라이트 포함
    if "매치 하이라이트" not in title:
        return False

    # 정규리그 형식:
    # 매치 49 하이라이트
    # 매치130 하이라이트
    # → 제외
    if re.search(
        r"매치\s*\d+\s*하이라이트",
        title
    ):
        return False

    return True


# =========================================================
# 대상 경기
# =========================================================

def get_targets(matches):

    targets = []

    now = datetime.now(
        timezone.utc
    )

    for match in matches:

        if match.get("status") != "completed":
            continue

        match_start = parse_match_time(
            match["start_time"]
        )

        if match_start < MATCHING_START:
            continue

        if match_start > now:
            continue

        # 경기 시작 후 30시간까지만 자동 탐색
        if now - match_start > RECENT_LIMIT:
            continue

        highlights = match.get(
            "highlights",
            {}
        )

        if highlights.get("youtube"):
            continue

        targets.append(match)

    targets.sort(
        key=lambda m: m["start_time"]
    )

    return targets


# =========================================================
# YouTube 재생목록
# =========================================================

def fetch_playlist():

    options = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
        "skip_download": True
    }

    print(
        "[YOUTUBE] 재생목록 불러오는 중..."
    )

    with yt_dlp.YoutubeDL(
        options
    ) as ydl:

        info = ydl.extract_info(
            YOUTUBE_PLAYLIST,
            download=False
        )

    entries = info.get(
        "entries",
        []
    )

    return [
        entry
        for entry in entries
        if entry
    ]


# =========================================================
# 정규리그 매칭
# =========================================================

def build_regular_matches(matches):

    regular = []

    for match in matches:

        if match.get("status") != "completed":
            continue

        match_start = parse_match_time(
            match["start_time"]
        )

        if match_start < MATCHING_START:
            continue

        if not is_regular_season(
            match
        ):
            continue

        regular.append(match)

    regular.sort(
        key=lambda m: m["start_time"]
    )

    return regular


def find_regular_video(
    match,
    playlist,
    regular_matches
):

    try:
        match_index = next(
            i
            for i, item in enumerate(
                regular_matches
            )
            if item["id"] == match["id"]
        )

    except StopIteration:
        return None

    expected_number = (
        match_index + 1
    )

    candidates = []

    for video in playlist:

        title = video.get(
            "title",
            ""
        )

        if not title:
            continue

        if not teams_match(
            title,
            match
        ):
            continue

        match_number = (
            get_regular_match_number(
                title
            )
        )

        if (
            match_number
            != expected_number
        ):
            continue

        video_id = video.get(
            "id"
        )

        if not video_id:
            continue

        candidates.append(
            (
                video_id,
                title
            )
        )

    if not candidates:
        return None

    return candidates[0]


# =========================================================
# 플레이-인 / 플레이오프 / 결승 등
# =========================================================

def find_postseason_video(
    match,
    playlist
):

    candidates = []

    for video in playlist:

        title = video.get(
            "title",
            ""
        )

        if not title:
            continue

        if not teams_match(
            title,
            match
        ):
            continue

        if not is_postseason_highlight(
            title
        ):
            continue

        video_id = video.get(
            "id"
        )

        if not video_id:
            continue

        candidates.append(
            (
                video_id,
                title
            )
        )

    if not candidates:
        return None

    # 재생목록의 최신 후보 우선
    return candidates[0]


# =========================================================
# 실행
# =========================================================

def main():

    data = load_matches()

    matches = data.get(
        "matches",
        []
    )

    targets = get_targets(
        matches
    )

    print()
    print("==============================")
    print("YouTube Highlight Update")
    print("==============================")

    print(
        f"최근 30시간 내 "
        f"링크 없는 완료 경기: "
        f"{len(targets)}"
    )

    if not targets:
        print(
            "업데이트 대상 없음"
        )
        return

    playlist = fetch_playlist()

    print(
        f"[YOUTUBE] 재생목록 영상: "
        f"{len(playlist)}개"
    )

    regular_matches = (
        build_regular_matches(
            matches
        )
    )

    changed = 0

    for match in targets:

        team_a = match["team_a"]
        team_b = match["team_b"]

        start = parse_match_time(
            match["start_time"]
        ).astimezone(KST)

        print()
        print(
            f"[YOUTUBE] "
            f"{team_a} vs {team_b}"
        )

        print(
            "  경기 시작:",
            start.strftime(
                "%Y-%m-%d %H:%M KST"
            )
        )

        print(
            "  구분:",
            match.get(
                "category",
                ""
            )
        )

        if is_regular_season(
            match
        ):

            result = (
                find_regular_video(
                    match,
                    playlist,
                    regular_matches
                )
            )

            mode = "정규리그"

        else:

            result = (
                find_postseason_video(
                    match,
                    playlist
                )
            )

            mode = "포스트시즌"

        print(
            "  매칭 방식:",
            mode
        )

        if not result:

            print(
                "  → 조건에 맞는 "
                "하이라이트 없음"
            )

            continue

        video_id, title = result

        url = (
            "https://www.youtube.com/"
            f"watch?v={video_id}"
        )

        print(
            "  → 매칭:",
            title
        )

        print(
            "  URL:",
            url
        )

        if "highlights" not in match:
            match["highlights"] = {}

        match["highlights"][
            "youtube"
        ] = url

        changed += 1

    print()
    print("==============================")

    if changed == 0:

        print(
            "YouTube 변경사항 없음"
        )

        print(
            "=============================="
        )

        return

    save_matches(
        data
    )

    print(
        f"YouTube 링크 추가: "
        f"{changed}개"
    )

    print(
        "matches.json 업데이트 완료"
    )

    print(
        "=============================="
    )


if __name__ == "__main__":
    main()