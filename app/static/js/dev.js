document.addEventListener("DOMContentLoaded", () => {
    let currentSessionId = "dev_default_session";
    let devSessions = [];

    const chatMessages = document.getElementById("dev-chat-messages");
    const chatInput = document.getElementById("dev-chat-input");
    const sendBtn = document.getElementById("dev-send-btn");
    const sessionList = document.getElementById("dev-session-list");
    const newSessionBtn = document.getElementById("new-dev-session-btn");
    const mobileMenuBtn = document.getElementById("mobile-menu-btn");
    const closeSidebarBtn = document.getElementById("close-sidebar-btn");
    const sidebar = document.getElementById("sidebar");
    const sidebarBackdrop = document.getElementById("sidebar-backdrop");
    const headerBranch = document.getElementById("header-branch-badge");
    const sidebarBranch = document.getElementById("dev-sidebar-branch");
    const activeDevTitle = document.getElementById("active-dev-title");
    const activeDevMeta = document.getElementById("active-dev-meta");
    const cmdChips = document.querySelectorAll(".cmd-chip");

    // Connection Resilience & Heartbeat Elements (ADR-021)
    const connectionBanner = document.getElementById("connection-banner");
    const connectionBannerText = document.getElementById("connection-banner-text");
    const reconnectBtn = document.getElementById("reconnect-btn");
    const systemStatus = document.querySelector(".system-status");
    const statusIndicator = document.querySelector(".status-indicator");
    const statusTitle = document.querySelector(".status-title");
    const statusSub = document.querySelector(".status-sub");

    let currentConnectionState = "online";
    let isReconnecting = false;

    function updateConnectionUI(state, message = "") {
        currentConnectionState = state;
        if (statusIndicator) {
            statusIndicator.className = `status-indicator ${state}`;
        }
        if (systemStatus) {
            systemStatus.className = `system-status ${state !== "online" ? state : ""}`;
        }

        if (state === "online") {
            if (statusTitle) statusTitle.innerText = "DevBot 24/7 Active";
            if (statusSub) statusSub.innerText = "AGY & Terminal Ready";
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
                    console.warn(`[Dev Connection] Transient HTTP ${res.status} on ${url}. Retrying (${attempt + 1}/${retries})...`);
                    updateConnectionUI("warning", "서버 응답 지연 중... 재연결 시도 중");
                    await new Promise(r => setTimeout(r, delay * (attempt + 1)));
                    continue;
                }
                return res;
            } catch (err) {
                if (attempt < retries) {
                    console.warn(`[Dev Connection] Network drop on ${url}. Retrying (${attempt + 1}/${retries})...`, err);
                    updateConnectionUI("warning", "일시적 연결 끊김. 자동 재연결 중...");
                    await new Promise(r => setTimeout(r, delay * (attempt + 1)));
                } else {
                    throw err;
                }
            }
        }
    }

    async function checkHealth() {
        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 6000);
            const res = await fetch("/api/health", { signal: controller.signal });
            clearTimeout(timeoutId);
            if (res.ok) {
                if (isReconnecting || currentConnectionState !== "online") {
                    console.log("[Dev Connection] Restored online status.");
                    isReconnecting = false;
                    updateConnectionUI("online");
                    await syncActiveSessionHistory();
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

    async function syncActiveSessionHistory() {
        if (!currentSessionId) return;
        try {
            const res = await fetch(`/api/sessions/${currentSessionId}/history`);
            if (res.ok) {
                const data = await res.json();
                chatMessages.innerHTML = "";
                if (!data.history || data.history.length === 0) {
                    appendMessage("assistant", "안녕하세요! 새 개발 세션이 시작되었습니다. 필요한 개발 작업이나 Git 명령을 입력하세요. 💻");
                } else {
                    data.history.forEach(m => appendMessage(m.role, m.content));
                }
                if (activeDevTitle) activeDevTitle.innerText = data.title || "DevBot 콘솔";
                if (activeDevMeta) activeDevMeta.innerText = `개발 태스크 • 메시지 ${data.history.length}개 • ${currentSessionId}`;
                if (data.history && data.history.length > 0 && data.history[data.history.length - 1].role === "assistant") {
                    sendBtn.disabled = false;
                    sendBtn.innerHTML = '<i class="fa-solid fa-paper-plane"></i> <span class="desktop-only">실행</span>';
                }
            }
        } catch (e) {
            console.debug("Failed to sync dev history:", e);
        }
    }

    // Drawer handlers
    function openSidebar() {
        if (sidebar) sidebar.classList.add("open");
        if (sidebarBackdrop) sidebarBackdrop.classList.add("active");
    }

    function closeSidebar() {
        if (sidebar) sidebar.classList.remove("open");
        if (sidebarBackdrop) sidebarBackdrop.classList.remove("active");
    }

    mobileMenuBtn?.addEventListener("click", openSidebar);
    closeSidebarBtn?.addEventListener("click", closeSidebar);
    sidebarBackdrop?.addEventListener("click", closeSidebar);

    // Simple Markdown Formatter
    function formatMarkdown(text) {
        if (!text) return "";
        let escaped = text
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;");

        // Code blocks
        escaped = escaped.replace(/```([a-z]*)\n([\s\S]*?)```/g, (match, lang, code) => {
            return `<pre class="code-block ${lang}"><code>${code.trim()}</code></pre>`;
        });

        // Inline code
        escaped = escaped.replace(/`([^`]+)`/g, '<code class="inline-code">$1</code>');

        // Headers
        escaped = escaped.replace(/^### (.*$)/gim, "<h4>$1</h4>");
        escaped = escaped.replace(/^## (.*$)/gim, "<h3>$1</h3>");

        // Bold
        escaped = escaped.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");

        // Line breaks (outside pre)
        const parts = escaped.split(/(<pre[\s\S]*?<\/pre>)/);
        for (let i = 0; i < parts.length; i++) {
            if (!parts[i].startsWith("<pre")) {
                parts[i] = parts[i].replace(/\n/g, "<br>");
            }
        }
        return parts.join("");
    }

    function appendMessage(role, text) {
        const msgDiv = document.createElement("div");
        msgDiv.className = `message ${role}`;

        const avatar = document.createElement("div");
        avatar.className = "avatar";
        avatar.innerHTML = role === "user" ? '<i class="fa-solid fa-user"></i>' : '<i class="fa-solid fa-code"></i>';

        const bubble = document.createElement("div");
        bubble.className = "bubble";
        bubble.innerHTML = formatMarkdown(text);

        msgDiv.appendChild(avatar);
        msgDiv.appendChild(bubble);
        chatMessages.appendChild(msgDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    // Load dev workspace status
    async function loadDevStatus() {
        try {
            const res = await fetch("/api/dev/status");
            if (res.ok) {
                const data = await res.json();
                if (headerBranch) headerBranch.innerHTML = `<i class="fa-solid fa-code-branch"></i> ${data.branch}`;
                if (sidebarBranch) sidebarBranch.innerText = `Branch: ${data.branch} (${data.changed_files_count} files)`;
            }
        } catch (e) {
            console.error("Failed to load dev status", e);
        }
    }

    // Load dev sessions
    async function loadSessions() {
        try {
            const res = await fetch("/api/dev/sessions");
            if (res.ok) {
                devSessions = await res.json();
                renderSessionList();
                if (devSessions.length > 0) {
                    const exists = devSessions.some(s => s.id === currentSessionId);
                    const targetId = exists ? currentSessionId : devSessions[0].id;
                    await switchSession(targetId);
                }
            }
        } catch (e) {
            console.error("Failed to load dev sessions", e);
        }
    }

    function renderSessionList() {
        sessionList.innerHTML = "";
        if (devSessions.length === 0) {
            sessionList.innerHTML = '<div class="session-empty-state"><p>진행 중인 개발 세션이 없습니다.</p></div>';
            return;
        }

        devSessions.forEach(s => {
            const item = document.createElement("div");
            item.className = `session-item ${s.id === currentSessionId ? "active" : ""}`;
            item.innerHTML = `
                <div class="session-item-header">
                    <span class="session-channel-badge dev"><i class="fa-solid fa-code"></i></span>
                    <span class="session-title">${s.title || s.id}</span>
                </div>
                <div class="session-item-footer">
                    <span class="session-meta-time">${s.message_count || 0}개 메시지</span>
                </div>
            `;
            item.addEventListener("click", () => switchSession(s.id));
            sessionList.appendChild(item);
        });
    }

    async function switchSession(sessionId) {
        currentSessionId = sessionId;
        if (window.innerWidth <= 768) closeSidebar();

        document.querySelectorAll(".session-item").forEach(el => {
            el.classList.toggle("active", el.innerText.includes(sessionId));
        });

        try {
            const res = await fetch(`/api/sessions/${sessionId}/history`);
            if (res.ok) {
                const data = await res.json();
                chatMessages.innerHTML = "";
                if (!data.history || data.history.length === 0) {
                    appendMessage("assistant", "안녕하세요! 새 개발 세션이 시작되었습니다. 필요한 개발 작업이나 Git 명령을 입력하세요. 💻");
                } else {
                    data.history.forEach(m => appendMessage(m.role, m.content));
                }
                if (activeDevTitle) activeDevTitle.innerText = data.title || "DevBot 콘솔";
                if (activeDevMeta) activeDevMeta.innerText = `개발 태스크 • 메시지 ${data.history.length}개 • ${sessionId}`;
            }
        } catch (e) {
            console.error("Failed to load session history", e);
        }
    }

    // Send Message
    async function sendMessage(textToSend = null) {
        const text = (textToSend !== null ? textToSend : chatInput.value).trim();
        if (!text) return;

        appendMessage("user", text);
        if (textToSend === null) chatInput.value = "";

        sendBtn.disabled = true;
        sendBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';

        try {
            const res = await fetchWithRetry("/api/dev/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    session_id: currentSessionId,
                    message: text
                })
            }, 2, 1500);
            if (res.ok) {
                updateConnectionUI("online");
                const data = await res.json();
                appendMessage("assistant", data.ai_response);
                await loadSessions();
                await loadDevStatus();
            } else {
                appendMessage("assistant", "⚠️ 요청 처리 중 오류가 발생했습니다.");
            }
        } catch (e) {
            console.error(e);
            updateConnectionUI("warning", "응답 대기 중 일시적 연결 지연이 발생했습니다.");
            // Recovery: check if the assistant's reply was actually saved to SQLite before socket dropped
            await new Promise(r => setTimeout(r, 1000));
            try {
                const checkRes = await fetch(`/api/sessions/${currentSessionId}/history`);
                if (checkRes.ok) {
                    const data = await checkRes.json();
                    const hist = data.history || [];
                    if (hist.length > 0 && hist[hist.length - 1].role === "assistant") {
                        chatMessages.innerHTML = "";
                        hist.forEach(m => appendMessage(m.role, m.content));
                        updateConnectionUI("online");
                        return;
                    }
                }
            } catch (errSync) {
                console.debug("Recovery sync check failed:", errSync);
            }
            appendMessage("assistant", "⚠️ 네트워크 연결이 일시적으로 끊겼습니다. 상단 재시도 버튼을 누르거나 잠시 후 다시 확인해 주세요.");
        } finally {
            sendBtn.disabled = false;
            sendBtn.innerHTML = '<i class="fa-solid fa-paper-plane"></i> <span class="desktop-only">실행</span>';
        }
    }

    sendBtn?.addEventListener("click", () => sendMessage());
    chatInput?.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    // Quick Command Chips
    cmdChips.forEach(chip => {
        chip.addEventListener("click", () => {
            const cmd = chip.dataset.cmd;
            if (cmd) sendMessage(cmd);
        });
    });

    // New Dev Session
    newSessionBtn?.addEventListener("click", () => {
        const newId = `dev_task_${Date.now()}`;
        currentSessionId = newId;
        chatMessages.innerHTML = "";
        appendMessage("assistant", "새 개발 세션이 생성되었습니다! 워크스페이스 관련 명령이나 코딩 질문을 입력해 주세요. 💻");
        if (activeDevTitle) activeDevTitle.innerText = "새 개발 태스크";
        if (activeDevMeta) activeDevMeta.innerText = `개발 태스크 • 메시지 0개 • ${newId}`;
        if (window.innerWidth <= 768) closeSidebar();
    });

    // Lifecycle & Connection Event Listeners (ADR-021)
    document.addEventListener("visibilitychange", async () => {
        if (!document.hidden) {
            console.log("[Dev Connection] Tab became visible. Checking health & syncing history...");
            checkHealth();
            await syncActiveSessionHistory();
        }
    });

    window.addEventListener("online", () => {
        console.log("[Dev Connection] Browser reported online.");
        updateConnectionUI("warning", "네트워크 복구 감지됨. 연결 확인 중...");
        checkHealth();
    });

    window.addEventListener("offline", () => {
        console.log("[Dev Connection] Browser reported offline.");
        updateConnectionUI("offline");
    });

    reconnectBtn?.addEventListener("click", () => {
        updateConnectionUI("warning", "수동 재연결 시도 중...");
        checkHealth();
    });

    // Initial Load & Heartbeat (every 25 seconds)
    loadDevStatus();
    loadSessions();
    checkHealth();
    setInterval(checkHealth, 25000);
});
