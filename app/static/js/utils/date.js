/**
 * Watson AI Agent - Date & Time Utilities (KST Normalized, ADR-013, ADR-047, ADR-050)
 */
(function() {
    // Helper to get date string formatted in KST (YYYY-MM-DD)
    function getKSTDateString(date = new Date()) {
        try {
            return new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Seoul" }).format(date);
        } catch {
            const year = date.getFullYear();
            const month = String(date.getMonth() + 1).padStart(2, "0");
            const day = String(date.getDate()).padStart(2, "0");
            return `${year}-${month}-${day}`;
        }
    }

    // Relative Time Formatter (KST-aware & timezone robust)
    function formatRelativeTime(dateStr) {
        if (!dateStr) return "";
        try {
            let parseStr = dateStr.trim();
            // If string has no timezone indicator, treat as KST (+09:00)
            if (!parseStr.includes("Z") && !parseStr.includes("+") && !parseStr.match(/-\d{2}:\d{2}$/)) {
                parseStr = parseStr.replace(" ", "T") + "+09:00";
            }
            const d = new Date(parseStr);
            const now = new Date();
            const diffSec = Math.floor((now - d) / 1000);
            if (diffSec < 60) return "방금";
            const diffMin = Math.floor(diffSec / 60);
            if (diffMin < 60) return `${diffMin}분 전`;
            const diffHour = Math.floor(diffMin / 60);
            if (diffHour < 24) return `${diffHour}시간 전`;
            const diffDay = Math.floor(diffHour / 24);
            if (diffDay === 1) return "어제";
            if (diffDay < 7) return `${diffDay}일 전`;
            return `${d.getMonth() + 1}월 ${d.getDate()}일`;
        } catch {
            return "";
        }
    }

    // Live KST Header Clock
    function updateLiveClock(clockElementId = "header-live-clock") {
        const clockEl = document.getElementById(clockElementId);
        if (!clockEl) return;
        try {
            const now = new Date();
            const timePart = new Intl.DateTimeFormat("ko-KR", {
                timeZone: "Asia/Seoul",
                hour: "2-digit",
                minute: "2-digit",
                second: "2-digit",
                hour12: false
            }).format(now);
            clockEl.textContent = `${timePart} KST`;
        } catch {
            const now = new Date();
            clockEl.textContent = `${now.toLocaleTimeString()} KST`;
        }
    }

    // Export to global window namespace
    window.WatsonDate = {
        getKSTDateString,
        formatRelativeTime,
        updateLiveClock
    };
    window.getKSTDateString = getKSTDateString;
    window.formatRelativeTime = formatRelativeTime;
    window.updateLiveClock = updateLiveClock;
})();
