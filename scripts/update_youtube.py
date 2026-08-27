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

MIN_DELAY = timedelta(hours=18)
MAX_DELAY = timedelta(hours=30)

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
# 제목 판정
# =========================================================

def contains_team(title, team):

    title_upper = title.upper()

    pattern = (
        rf"(?<![A-Z0-9])"
        rf"{re.escape(team.upper())}"
        rf"(?![A-Z0-9])"
    )

    return bool(
        re.search(
            pattern,
            title_upper
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


def is_match_highlight(title):

    if "하이라이트" not in title:
        return False

    title_lower = title.lower()

    # GAME 1 / Game 2 / game3 등 제외
    if re.search(
        r"\bgame\s*\d+\b",
        title_lower
    ):
        return False

    # 게임 1 / 게임2 등 제외
    if re.search(
        r"게임\s*\d+",
        title
    ):
        return False

    return True


# =========================================================
# 매칭 대상 경기
# =========================================================

def get_targets(matches):

    targets = []

    for match in matches:

        if match.get("status") != "completed":
            continue

        match_start = parse_match_time(
            match["start_time"]
        )

        if match_start < MATCHING_START:
            continue

        highlights = match.get(
            "highlights",
            {}
        )

        # 이미 YouTube 링크가 있으면 건드리지 않음
        if highlights.get("youtube"):
            continue

        targets.append(match)

    targets.sort(
        key=lambda m: m["start_time"],
        reverse=True
    )

    return targets


# =========================================================
# YouTube
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


VIDEO_DETAIL_CACHE = {}


def fetch_video_detail(video_id):

    if video_id in VIDEO_DETAIL_CACHE:
        return VIDEO_DETAIL_CACHE[
            video_id
        ]

    url = (
        "https://www.youtube.com/watch?v="
        f"{video_id}"
    )

    options = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True
    }

    try:

        with yt_dlp.YoutubeDL(
            options
        ) as ydl:

            detail = ydl.extract_info(
                url,
                download=False
            )

    except Exception as error:

        print(
            f"  [YOUTUBE] 상세정보 조회 실패 "
            f"{video_id}: {error}"
        )

        detail = None

    VIDEO_DETAIL_CACHE[
        video_id
    ] = detail

    return detail


# =========================================================
# 경기 ↔ 영상 매칭
# =========================================================

def find_video(match, playlist):

    match_start = parse_match_time(
        match["start_time"]
    )

    title_candidates = []

    # 먼저 제목만으로 후보를 좁힘
    for video in playlist:

        title = video.get(
            "title",
            ""
        )

        if not title:
            continue

        if not is_match_highlight(
            title
        ):
            continue

        if not teams_match(
            title,
            match
        ):
            continue

        video_id = video.get(
            "id"
        )

        if not video_id:
            continue

        title_candidates.append(
            (
                video_id,
                title
            )
        )

    if not title_candidates:
        return None

    candidates = []

    # 제목 후보에 대해서만 실제 업로드 시간 확인
    for (
        video_id,
        title
    ) in title_candidates:

        detail = fetch_video_detail(
            video_id
        )

        if not detail:
            continue

        timestamp = detail.get(
            "timestamp"
        )

        if timestamp is None:
            continue

        upload_time = datetime.fromtimestamp(
            timestamp,
            tz=timezone.utc
        )

        diff = (
            upload_time
            - match_start
        )

        if diff < MIN_DELAY:
            continue

        if diff > MAX_DELAY:
            continue

        candidates.append(
            (
                diff,
                title,
                video_id,
                upload_time
            )
        )

    if not candidates:
        return None

    candidates.sort(
        key=lambda item: item[0]
    )

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
        f"링크 없는 완료 경기: {len(targets)}"
    )

    if not targets:
        print("업데이트 대상 없음")
        return

    playlist = fetch_playlist()

    print(
        f"[YOUTUBE] 재생목록 영상: "
        f"{len(playlist)}개"
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

        result = find_video(
            match,
            playlist
        )

        if not result:

            print(
                "  → 조건에 맞는 "
                "하이라이트 없음"
            )

            continue

        (
            diff,
            title,
            video_id,
            upload_time
        ) = result

        url = (
            "https://www.youtube.com/"
            f"watch?v={video_id}"
        )

        print(
            "  → 매칭:",
            title
        )

        print(
            "  업로드:",
            upload_time
            .astimezone(KST)
            .strftime(
                "%Y-%m-%d %H:%M KST"
            )
        )

        print(
            "  경기 후:",
            round(
                diff.total_seconds()
                / 3600,
                2
            ),
            "시간"
        )

        print(
            "  URL:",
            url
        )

        if "highlights" not in match:
            match["highlights"] = {}

        match["highlights"]["youtube"] = url

        changed += 1

    print()
    print("==============================")

    if changed == 0:

        print("YouTube 변경사항 없음")
        print("==============================")
        return

    save_matches(
        data
    )

    print(
        f"YouTube 링크 추가: {changed}개"
    )

    print(
        "matches.json 업데이트 완료"
    )

    print("==============================")


if __name__ == "__main__":
    main()