/**
 * Watson AI Agent - API & Network Resilience Utilities (ADR-021, ADR-050 / Phase 2)
 */
(function() {
    let currentConnectionState = "online";
    let isReconnecting = false;

    function updateConnectionUI(state, message = "") {
        currentConnectionState = state;
        const statusIndicator = document.querySelector(".status-indicator");
        const systemStatus = document.querySelector(".system-status");
        const statusTitle = document.querySelector(".status-title");
        const statusSub = document.querySelector(".status-sub");
        const connectionBanner = document.getElementById("connection-banner");
        const connectionBannerText = document.getElementById("connection-banner-text");

        if (statusIndicator) {
            statusIndicator.className = `status-indicator ${state}`;
        }
        if (systemStatus) {
            systemStatus.className = `system-status ${state !== "online" ? state : ""}`;
        }

        if (state === "online") {
            if (statusTitle) statusTitle.innerText = "Agent 24/7 Active";
            if (statusSub) statusSub.innerText = "Git Sync & Context Memory";
            if (connectionBanner) connectionBanner.classList.add("hidden");
        } else if (state === "warning") {
            if (statusTitle) statusTitle.innerText = "재연결 시도 중...";
            if (statusSub) statusSub.innerText = message || "네트워크 상태 확인 중";
            if (connectionBanner) {
                connectionBanner.className = "connection-banner warning";
                if (connectionBannerText) connectionBannerText.innerText = message || "서버 연결이 불안정하여 재연결 중입니다.";
                connectionBanner.classList.remove("hidden");
            }
        } else if (state === "offline") {
            if (statusTitle) statusTitle.innerText = "연결 끊김 (Offline)";
            if (statusSub) statusSub.innerText = "인터넷 또는 터널 연결 확인 필요";
            if (connectionBanner) {
                connectionBanner.className = "connection-banner offline";
                if (connectionBannerText) connectionBannerText.innerText = "네트워크 연결이 끊겼습니다. 인터넷 연결을 확인해 주세요.";
                connectionBanner.classList.remove("hidden");
            }
        }
    }

    async function fetchWithRetry(url, options = {}, retries = 2, delay = 1200) {
        for (let attempt = 0; attempt <= retries; attempt++) {
            try {
                let signal = options.signal;
                if (!signal && typeof AbortSignal !== "undefined" && AbortSignal.timeout) {
                    signal = AbortSignal.timeout(65000);
                }
                const res = await fetch(url, { ...options, signal });
                if ([502, 503, 504].includes(res.status) && attempt < retries) {
                    console.warn(`[Connection] Transient HTTP ${res.status} on ${url}. Retrying (${attempt + 1}/${retries})...`);
                    updateConnectionUI("warning", "서버 응답 지연 중... 재연결 시도 중");
                    await new Promise(r => setTimeout(r, delay * (attempt + 1)));
                    continue;
                }
                return res;
            } catch (err) {
                if (attempt < retries) {
                    console.warn(`[Connection] Network drop on ${url}. Retrying (${attempt + 1}/${retries})...`, err);
                    updateConnectionUI("warning", "일시적 연결 끊김. 자동 재연결 중...");
                    await new Promise(r => setTimeout(r, delay * (attempt + 1)));
                } else {
                    throw err;
                }
            }
        }
    }

    async function checkHealth(onRestore = null) {
        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 6000);
            const res = await fetch("/api/health", { signal: controller.signal });
            clearTimeout(timeoutId);
            if (res.ok) {
                if (isReconnecting || currentConnectionState !== "online") {
                    console.log("[Connection] Restored online status.");
                    isReconnecting = false;
                    updateConnectionUI("online");
                    if (typeof onRestore === "function") {
                        await onRestore();
                    }
                } else {
                    updateConnectionUI("online");
                }
            } else {
                updateConnectionUI("warning", `서버 응답 이상 (HTTP ${res.status})`);
                isReconnecting = true;
            }
        } catch (e) {
            updateConnectionUI("offline");
            isReconnecting = true;
        }
    }

    // Export to global window namespace
    window.WatsonAPI = {
        updateConnectionUI,
        fetchWithRetry,
        checkHealth,
        getConnectionState: () => currentConnectionState
    };
    window.fetchWithRetry = fetchWithRetry;
    window.updateConnectionUI = updateConnectionUI;
})();
