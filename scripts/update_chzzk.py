import json
import re
import requests

from pathlib import Path
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo


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

MAX_DELAY = timedelta(hours=8)

CHZZK_CHANNEL_ID = (
    "9381e7d6816e6d915a44a13c0195b202"
)

CHZZK_API = (
    "https://api.chzzk.naver.com/service/v1/channels/"
    f"{CHZZK_CHANNEL_ID}/videos"
)

CHZZK_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": (
        f"https://chzzk.naver.com/"
        f"{CHZZK_CHANNEL_ID}/videos"
    ),
    "Accept": "application/json, text/plain, */*"
}

MAX_PAGES = 8


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


def parse_chzzk_time(value):

    if not value:
        return None

    try:
        dt = datetime.fromisoformat(value)

        if dt.tzinfo is None:
            dt = dt.replace(
                tzinfo=KST
            )

        return dt

    except ValueError:
        return None


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

        # 이미 치지직 링크가 있으면 건드리지 않음
        if highlights.get("chzzk"):
            continue

        targets.append(match)

    targets.sort(
        key=lambda m: m["start_time"],
        reverse=True
    )

    return targets


# =========================================================
# CHZZK 영상 목록
# =========================================================

def fetch_chzzk_videos():

    videos = []

    for page in range(MAX_PAGES):

        print(
            f"[CHZZK] 영상 목록 "
            f"{page + 1}페이지 불러오는 중..."
        )

        params = {
            "sortType": "LATEST",
            "pagingType": "PAGE",
            "page": page,
            "size": 18,
            "publishDateAt": "",
            "videoType": "UPLOAD"
        }

        response = requests.get(
            CHZZK_API,
            headers=CHZZK_HEADERS,
            params=params,
            timeout=20
        )

        response.raise_for_status()

        data = response.json()

        content = data.get(
            "content",
            {}
        )

        page_videos = (
            content.get("data")
            or
            content.get("videos")
            or
            []
        )

        if not page_videos:
            break

        videos.extend(
            page_videos
        )

    return videos


# =========================================================
# 경기 ↔ 영상 매칭
# =========================================================

def find_video(match, videos):

    match_start = parse_match_time(
        match["start_time"]
    ).astimezone(KST)

    candidates = []

    for video in videos:

        title = video.get(
            "videoTitle",
            ""
        )

        if not title:
            continue

        if not is_match_highlight(title):
            continue

        if not teams_match(
            title,
            match
        ):
            continue

        upload_time = parse_chzzk_time(
            video.get("publishDate")
        )

        if not upload_time:
            continue

        diff = (
            upload_time
            - match_start
        )

        if diff <= timedelta(0):
            continue

        if diff > MAX_DELAY:
            continue

        video_no = video.get(
            "videoNo"
        )

        if not video_no:
            continue

        candidates.append(
            (
                diff,
                title,
                video_no,
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
    print("CHZZK Highlight Update")
    print("==============================")
    print(
        f"링크 없는 완료 경기: {len(targets)}"
    )

    if not targets:
        print("업데이트 대상 없음")
        return

    videos = fetch_chzzk_videos()

    print(
        f"[CHZZK] 불러온 영상: {len(videos)}개"
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
            f"[CHZZK] {team_a} vs {team_b}"
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
            videos
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
            video_no,
            upload_time
        ) = result

        url = (
            "https://chzzk.naver.com/"
            f"video/{video_no}"
        )

        print(
            "  → 매칭:",
            title
        )

        print(
            "  업로드:",
            upload_time.strftime(
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

        match["highlights"]["chzzk"] = url

        changed += 1

    print()
    print("==============================")

    if changed == 0:

        print("CHZZK 변경사항 없음")
        print("==============================")
        return

    save_matches(
        data
    )

    print(
        f"CHZZK 링크 추가: {changed}개"
    )

    print(
        "matches.json 업데이트 완료"
    )

    print("==============================")


if __name__ == "__main__":
    main()