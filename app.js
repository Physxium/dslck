const TEAMS = [
            "BFX",
            "BRO",
            "DK",
            "DNS",
            "GEN",
            "HLE",
            "KRX",
            "KT",
            "NS",
            "T1"
        ];


        const state = {
            tab: "recent",
            team: "전체",
            revealed: new Set(),
            visibleCount: 20
        };


        let allMatches = [];


        const filtersEl =
            document.getElementById("filters");

        const matchesEl =
            document.getElementById("matches");

        const moreWrapEl =
            document.getElementById("moreWrap");


        /* ------------------------------
           Time
        ------------------------------ */

        function kstParts(startTime) {

            const parts =
                new Intl.DateTimeFormat(
                    "en-CA",
                    {
                        timeZone: "Asia/Seoul",

                        year: "numeric",
                        month: "2-digit",
                        day: "2-digit",

                        hour: "2-digit",
                        minute: "2-digit",

                        hourCycle: "h23"
                    }
                )
                    .formatToParts(
                        new Date(startTime)
                    );


            const get = type =>
                parts.find(
                    p => p.type === type
                )?.value ?? "";


            return {
                date:
                    `${get("year")}-${get("month")}-${get("day")}`,

                time:
                    `${get("hour")}:${get("minute")}`
            };
        }


        function getTodayKstDate() {

            return kstParts(
                new Date().toISOString()
            ).date;
        }


        function formatDate(dateString) {

            const [year, month, day] =
                dateString
                    .split("-")
                    .map(Number);


            const d =
                new Date(
                    Date.UTC(
                        year,
                        month - 1,
                        day
                    )
                );


            return new Intl.DateTimeFormat(
                "ko-KR",
                {
                    timeZone: "UTC",

                    month: "long",
                    day: "numeric",
                    weekday: "short"
                }
            ).format(d);
        }


        function displayCategory(m) {
            return `${m.competition} · ${m.category}`;
        }


        function isTodayMatch(m) {

            return (
                kstParts(m.start_time).date ===
                getTodayKstDate()
            );
        }


        /* ------------------------------
           Filters
        ------------------------------ */

        function renderFilters() {

            const all =
                ["전체", ...TEAMS];


            filtersEl.innerHTML =
                all.map(team => `
                    <button
                        class="
                            filter-btn
                            ${state.team === team ? "active" : ""}
                        "
                        data-team="${team}"
                    >
                        ${team}
                    </button>
                `).join("");


            filtersEl
                .querySelectorAll(".filter-btn")
                .forEach(btn => {

                    btn.addEventListener(
                        "click",
                        () => {

                            state.team =
                                btn.dataset.team;

                            state.visibleCount = 20;

                            renderFilters();
                            render();
                        }
                    );

                });
        }


        /* ------------------------------
           Tabs
        ------------------------------ */

        function renderTabs() {

            document
                .querySelectorAll(".tab-btn")
                .forEach(btn => {

                    btn.classList.toggle(
                        "active",
                        btn.dataset.tab === state.tab
                    );

                });
        }


        document
            .querySelectorAll(".tab-btn")
            .forEach(btn => {

                btn.addEventListener(
                    "click",
                    () => {

                        state.tab =
                            btn.dataset.tab;

                        state.visibleCount = 20;

                        renderTabs();
                        render();
                    }
                );

            });


        /* ------------------------------
           Media Buttons
        ------------------------------ */

        function platformButton(label, url) {

            return url

                ? `
                    <a
                        class="highlight-button"
                        href="${url}"
                        target="_blank"
                        rel="noopener noreferrer"
                    >
                        ${label}
                    </a>
                `

                : `
                    <div
                        class="pending"
                        title="${label} 영상 준비 중"
                    >
                        <span>
                            ${label}
                        </span>

                        <small>
                            준비 중
                        </small>
                    </div>
                `;
        }


        function pendingPlatform(label) {

            return `
                <div
                    class="pending"
                    title="${label} 영상 준비 중"
                >
                    <span>
                        ${label}
                    </span>

                    <small>
                        준비 중
                    </small>
                </div>
            `;
        }


        function fullVodButton(url) {

            return url

                ? `
                    <div class="full-vod-box">

                        <span class="full-vod-text">
                            FULL VOD
                        </span>

                        <a
                            class="play-button"
                            href="${url}"
                            target="_blank"
                            rel="noopener noreferrer"
                            aria-label="Full VOD 재생"
                        >
                            <span class="play-icon"></span>
                        </a>

                    </div>
                `

                : pendingFullVod();
        }


        function pendingFullVod() {

            return `
                <div class="full-vod-box pending-vod">

                    <div class="full-vod-info">

                        <span class="full-vod-text">
                            FULL VOD
                        </span>

                        <span class="full-vod-pending">
                            준비 중
                        </span>

                    </div>

                    <span
                        class="play-button disabled"
                        aria-hidden="true"
                    >
                        <span class="play-icon"></span>
                    </span>

                </div>
            `;
        }


        /* ------------------------------
           Completed Card
        ------------------------------ */

        function recentCard(m) {

            const revealed =
                state.revealed.has(m.id);


            return `
                <article class="match-card">

                    <div class="meta">

                        <span>
                            ${displayCategory(m)}
                        </span>

                        <span>
                            BO${m.best_of}
                        </span>

                    </div>


                    <div class="teams">

                        <div class="team">
                            ${m.team_a}
                        </div>

                        <div class="versus">
                            VS
                        </div>

                        <div class="team right">
                            ${m.team_b}
                        </div>

                    </div>


                    <div class="score-row">

                        <button
                            class="score-btn"
                            data-match-id="${m.id}"
                        >
                            ${revealed
                    ? `${m.score_a} : ${m.score_b}`
                    : "결과 보기"
                }
                        </button>

                    </div>


                    <div class="media-area">

                        <div class="media-column">

                            <div class="media-label">
                                풀영상
                            </div>

                            ${fullVodButton(m.full_vod)}

                        </div>


                        <div class="media-column">

                            <div class="media-label">
                                하이라이트
                            </div>

                            <div class="highlight-grid">

                                ${platformButton(
                    "SOOP",
                    m.highlights?.soop
                )}

                                ${platformButton(
                    "치지직",
                    m.highlights?.chzzk
                )}

                                ${platformButton(
                    "YouTube",
                    m.highlights?.youtube
                )}

                            </div>

                        </div>

                    </div>

                </article>
            `;
        }


        /* ------------------------------
           LIVE Card
        ------------------------------ */

        function liveCard(m) {

            return `
                <article class="match-card live-card">

                    <div class="meta">

                        <span>
                            ${displayCategory(m)}
                        </span>

                        <span>
                            BO${m.best_of}
                        </span>

                    </div>


                    <div class="teams">

                        <div class="team">
                            ${m.team_a}
                        </div>

                        <div class="versus">
                            VS
                        </div>

                        <div class="team right">
                            ${m.team_b}
                        </div>

                    </div>


                    <div class="score-row">

                        <a
                            class="live-status"
                            href="https://lolesports.com/live/lck"
                            target="_blank"
                            rel="noopener noreferrer"
                            aria-label="LCK 라이브 보기"
                        >
                            <span class="live-dot"></span>
                            LIVE
                            <span class="live-play">▶</span>
                        </a>

                    </div>


                    <div class="media-area">

                        <div class="media-column">

                            <div class="media-label">
                                풀영상
                            </div>

                            ${pendingFullVod()}

                        </div>


                        <div class="media-column">

                            <div class="media-label">
                                하이라이트
                            </div>

                            <div class="highlight-grid">

                                ${pendingPlatform("SOOP")}
                                ${pendingPlatform("치지직")}
                                ${pendingPlatform("YouTube")}

                            </div>

                        </div>

                    </div>

                </article>
            `;
        }


        /* ------------------------------
           Upcoming Card
        ------------------------------ */

        function upcomingCard(m) {

            const { time } =
                kstParts(m.start_time);


            return `
                <article
                    class="
                        match-card
                        upcoming-card
                    "
                >

                    <div class="meta">

                        <span>
                            ${displayCategory(m)}
                        </span>

                        <span>
                            BO${m.best_of}
                        </span>

                    </div>


                    <div class="teams">

                        <div class="team">
                            ${m.team_a}
                        </div>

                        <div class="versus">
                            VS
                        </div>

                        <div class="team right">
                            ${m.team_b}
                        </div>

                    </div>


                    <div class="upcoming-time">
                        ${time}
                    </div>

                </article>
            `;
        }


        /* ------------------------------
           Card Selector
        ------------------------------ */

        function recentTabCard(m) {

            if (m.status === "inProgress") {
                return liveCard(m);
            }

            if (
                m.status === "unstarted" ||
                m.status === "scheduled"
            ) {
                return upcomingCard(m);
            }

            return recentCard(m);
        }


        /* ------------------------------
           Group
        ------------------------------ */

        function groupByDate(items) {

            const groups = {};


            items.forEach(m => {

                const { date } =
                    kstParts(m.start_time);


                if (!groups[date]) {
                    groups[date] = [];
                }


                groups[date].push(m);
            });


            return groups;
        }


        function teamMatchesFilter(m) {

            return (
                state.team === "전체" ||
                m.team_a === state.team ||
                m.team_b === state.team
            );
        }


        /* ------------------------------
           Recent
        ------------------------------ */

        function renderRecent() {

            const today =
                getTodayKstDate();


            const filtered =
                allMatches

                    .filter(m => {

                        const matchDate =
                            kstParts(m.start_time).date;


                        if (matchDate === today) {
                            return true;
                        }


                        return (
                            matchDate < today &&
                            m.status === "completed"
                        );
                    })

                    .filter(teamMatchesFilter)

                    .sort((a, b) => {

                        const dateA =
                            kstParts(a.start_time).date;

                        const dateB =
                            kstParts(b.start_time).date;


                        if (dateA !== dateB) {
                            return dateB.localeCompare(dateA);
                        }


                        if (dateA === today) {

                            return (
                                new Date(a.start_time) -
                                new Date(b.start_time)
                            );
                        }


                        return (
                            new Date(b.start_time) -
                            new Date(a.start_time)
                        );
                    });


            const visible =
                filtered.slice(
                    0,
                    state.visibleCount
                );


            if (!visible.length) {

                matchesEl.innerHTML = `
                    <div class="empty">
                        해당 팀의 최근 경기가 없습니다.
                    </div>
                `;

                moreWrapEl.innerHTML = "";

                return;
            }


            const groups =
                groupByDate(visible);


            matchesEl.innerHTML =
                Object.entries(groups)

                    .sort(
                        ([a], [b]) =>
                            b.localeCompare(a)
                    )

                    .map(
                        ([date, items]) => `

                            <div class="date-group">

                                <div class="date-title">
                                    ${formatDate(date)}
                                </div>

                                ${items
                                .map(recentTabCard)
                                .join("")
                            }

                            </div>

                        `
                    )
                    .join("");


            matchesEl
                .querySelectorAll(".score-btn")
                .forEach(btn => {

                    btn.addEventListener(
                        "click",
                        () => {

                            const id =
                                btn.dataset.matchId;


                            if (state.revealed.has(id)) {
                                state.revealed.delete(id);
                            } else {
                                state.revealed.add(id);
                            }


                            render();
                        }
                    );

                });


            moreWrapEl.innerHTML =
                filtered.length > state.visibleCount

                    ? `
                        <button
                            class="more-btn"
                            id="moreBtn"
                        >
                            이전 경기 더 보기
                        </button>
                    `

                    : "";


            const moreBtn =
                document.getElementById("moreBtn");


            if (moreBtn) {

                moreBtn.addEventListener(
                    "click",
                    () => {

                        state.visibleCount += 20;

                        render();
                    }
                );

            }
        }


        /* ------------------------------
           Upcoming
        ------------------------------ */

        function renderUpcoming() {

            const filtered =
                allMatches

                    .filter(
                        m =>
                            m.status === "unstarted" ||
                            m.status === "scheduled"
                    )

                    .filter(teamMatchesFilter)

                    .sort(
                        (a, b) =>
                            new Date(a.start_time) -
                            new Date(b.start_time)
                    );


            if (!filtered.length) {

                matchesEl.innerHTML = `
                    <div class="empty">
                        해당 팀의 예정 경기가 없습니다.
                    </div>
                `;

                moreWrapEl.innerHTML = "";

                return;
            }


            const groups =
                groupByDate(filtered);


            matchesEl.innerHTML =
                Object.entries(groups)

                    .sort(
                        ([a], [b]) =>
                            a.localeCompare(b)
                    )

                    .map(
                        ([date, items]) => `

                            <div class="date-group">

                                <div class="date-title">
                                    ${formatDate(date)}
                                </div>

                                ${items
                                .map(upcomingCard)
                                .join("")
                            }

                            </div>

                        `
                    )
                    .join("");


            moreWrapEl.innerHTML = "";
        }


        /* ------------------------------
           Render
        ------------------------------ */

        function render() {

            if (state.tab === "recent") {
                renderRecent();
            } else {
                renderUpcoming();
            }
        }


        /* ------------------------------
           Load Data
        ------------------------------ */

        async function loadMatches() {

            matchesEl.innerHTML = `
                <div class="empty">
                    경기 데이터를 불러오는 중입니다.
                </div>
            `;


            try {

                const response =
                    await fetch(
                        "./matches.json",
                        {
                            cache: "no-store"
                        }
                    );


                if (!response.ok) {

                    throw new Error(
                        `HTTP ${response.status}`
                    );

                }


                const data =
                    await response.json();


                if (!Array.isArray(data.matches)) {

                    throw new Error(
                        "matches 배열이 없습니다."
                    );

                }


                allMatches =
                    data.matches;


                renderTabs();
                renderFilters();
                render();


            } catch (error) {

                console.error(error);


                matchesEl.innerHTML = `
                    <div class="empty">

                        경기 데이터를 불러오지 못했습니다.
                        <br>

                        잠시 후 다시 시도해 주세요.

                    </div>
                `;


                moreWrapEl.innerHTML = "";
            }
        }


        loadMatches();

const supportLink = document.getElementById("supportLink");
const cteeSupport = document.getElementById("cteeSupport");

supportLink?.addEventListener("click", () => {
    const bmcButton = document.getElementById("bmc-wbtn");

    if (bmcButton) {
        bmcButton.click();
        cteeSupport.hidden = false;
    }
});
