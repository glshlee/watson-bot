document.addEventListener("DOMContentLoaded", () => {
    let currentSessionId = "web_default_session";
    let allSessions = [];
    let currentFilter = "all";
    let searchQuery = "";
    let targetActionSessionId = null;

    const chatMessages = document.getElementById("chat-messages");
    const chatInput = document.getElementById("chat-input");
    const sendBtn = document.getElementById("send-btn");
    const categorySelect = document.getElementById("category-select");
    const sessionList = document.getElementById("session-list");
    const newSessionBtn = document.getElementById("new-session-btn");
    const sessionSearchInput = document.getElementById("session-search-input");
    const clearSearchBtn = document.getElementById("clear-search-btn");
    const filterTabs = document.querySelectorAll(".filter-tab");
    const mobileMenuBtn = document.getElementById("mobile-menu-btn");
    const closeSidebarBtn = document.getElementById("close-sidebar-btn");
    const sidebar = document.getElementById("sidebar");
    const sidebarBackdrop = document.getElementById("sidebar-backdrop");
    const activeSessionTitle = document.getElementById("active-session-title");
    const mobileSessionTitle = document.getElementById("mobile-session-title");
    const activeSessionMeta = document.getElementById("active-session-meta");
    const clearChatBtn = document.getElementById("clear-chat-btn");

    // Modals
    const renameModal = document.getElementById("rename-modal");
    const closeRenameModalBtn = document.getElementById("close-rename-modal-btn");
    const cancelRenameBtn = document.getElementById("cancel-rename-btn");
    const saveRenameBtn = document.getElementById("save-rename-btn");
    const renameSessionInput = document.getElementById("rename-session-input");

    const deleteModal = document.getElementById("delete-modal");
    const closeDeleteModalBtn = document.getElementById("close-delete-modal-btn");
    const cancelDeleteBtn = document.getElementById("cancel-delete-btn");
    const confirmDeleteBtn = document.getElementById("confirm-delete-btn");
    const deleteModalMsg = document.getElementById("delete-modal-msg");

    const clearModal = document.getElementById("clear-modal");
    const closeClearModalBtn = document.getElementById("close-clear-modal-btn");
    const cancelClearBtn = document.getElementById("cancel-clear-btn");
    const confirmClearBtn = document.getElementById("confirm-clear-btn");

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

    async function checkHealth() {
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
                renderHistory(data.history);
                if (activeSessionTitle && data.title) {
                    activeSessionTitle.innerText = data.title;
                }
            }
        } catch (e) {
            console.debug("Failed to sync session history:", e);
        }
    }

    // Relative Time Formatter
    function formatRelativeTime(dateStr) {
        if (!dateStr) return "";
        try {
            const d = new Date(dateStr);
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

    // Off-canvas mobile drawer handlers
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

    // Fetch session list from API
    async function loadSessions(autoSelect = false) {
        try {
            const res = await fetch("/api/sessions");
            if (res.ok) {
                allSessions = await res.json();
                renderSessionList();

                if (autoSelect && allSessions.length > 0) {
                    const exists = allSessions.some(s => s.id === currentSessionId);
                    const targetId = exists ? currentSessionId : allSessions[0].id;
                    await switchSession(targetId);
                }
            }
        } catch (e) {
            console.error("Failed to load sessions", e);
        }
    }

    // Render session cards with search and channel filter
    function renderSessionList() {
        sessionList.innerHTML = "";

        const filtered = allSessions.filter(s => {
            const matchesChannel = currentFilter === "all" || s.channel === currentFilter;
            const matchesQuery = !searchQuery ||
                (s.title && s.title.toLowerCase().includes(searchQuery)) ||
                (s.id && s.id.toLowerCase().includes(searchQuery)) ||
                (s.last_message && s.last_message.toLowerCase().includes(searchQuery));
            return matchesChannel && matchesQuery;
        });

        if (filtered.length === 0) {
            const emptyDiv = document.createElement("div");
            emptyDiv.className = "session-empty-state";
            emptyDiv.innerHTML = `
                <i class="fa-solid fa-comments"></i>
                <p>${searchQuery ? '검색된 세션이 없습니다.' : '대화 세션이 없습니다.'}</p>
            `;
            sessionList.appendChild(emptyDiv);
            return;
        }

        filtered.forEach(s => {
            const item = document.createElement("div");
            item.className = `session-item ${s.id === currentSessionId ? 'active' : ''}`;
            item.dataset.id = s.id;

            const isTelegram = s.channel === "telegram";
            const channelIcon = isTelegram ? 'fa-brands fa-telegram' : 'fa-solid fa-globe';
            const displayTitle = s.title || s.id;
            const timeStr = formatRelativeTime(s.updated_at);
            const msgCount = s.message_count || 0;

            item.innerHTML = `
                <div class="session-item-header">
                    <span class="session-channel-badge ${s.channel}" title="${isTelegram ? '텔레그램 세션' : '웹 콘솔 세션'}">
                        <i class="${channelIcon}"></i>
                    </span>
                    <span class="session-title" title="${displayTitle}">${displayTitle}</span>
                    <div class="session-actions">
                        <button class="session-action-btn edit-btn" title="이름 변경"><i class="fa-solid fa-pen"></i></button>
                        <button class="session-action-btn delete delete-btn" title="세션 삭제"><i class="fa-solid fa-trash"></i></button>
                    </div>
                </div>
                <div class="session-item-footer">
                    <span class="session-meta-time"><i class="fa-regular fa-clock"></i> ${timeStr}</span>
                    <span class="session-msg-count">${msgCount}개</span>
                </div>
            `;

            // Click card to switch session
            item.addEventListener("click", (e) => {
                if (e.target.closest(".session-actions")) return;
                switchSession(s.id);
            });

            // Edit button handler
            const editBtn = item.querySelector(".edit-btn");
            editBtn?.addEventListener("click", (e) => {
                e.stopPropagation();
                openRenameModal(s.id, displayTitle);
            });

            // Delete button handler
            const deleteBtn = item.querySelector(".delete-btn");
            deleteBtn?.addEventListener("click", (e) => {
                e.stopPropagation();
                openDeleteModal(s.id, displayTitle);
            });

            sessionList.appendChild(item);
        });
    }

    // Switch Session and load history
    async function switchSession(sessionId) {
        currentSessionId = sessionId;
        if (window.innerWidth <= 768) {
            closeSidebar();
        }

        // Highlight active session item in sidebar
        document.querySelectorAll(".session-item").forEach(el => {
            el.classList.toggle("active", el.dataset.id === sessionId);
        });

        try {
            const res = await fetch(`/api/sessions/${sessionId}/history`);
            if (res.ok) {
                const data = await res.json();
                renderHistory(data.history);

                // Update Header with Session Name
                const title = data.title || sessionId;
                if (activeSessionTitle) activeSessionTitle.innerText = title;
                if (mobileSessionTitle) mobileSessionTitle.innerText = title.length > 14 ? title.slice(0, 14) + "..." : title;
                if (activeSessionMeta) {
                    const channelLabel = data.channel === "telegram" ? "📱 텔레그램 연동 세션" : "🌐 웹 대화 세션";
                    activeSessionMeta.innerText = `${channelLabel} • 메시지 ${data.history.length}개 • ${sessionId}`;
                }
            }
        } catch (e) {
            console.error("Failed to load session history", e);
        }
    }

    // Search filter listeners
    sessionSearchInput?.addEventListener("input", (e) => {
        searchQuery = e.target.value.trim().toLowerCase();
        if (clearSearchBtn) {
            clearSearchBtn.classList.toggle("hidden", !searchQuery);
        }
        renderSessionList();
    });

    clearSearchBtn?.addEventListener("click", () => {
        sessionSearchInput.value = "";
        searchQuery = "";
        clearSearchBtn.classList.add("hidden");
        renderSessionList();
    });

    // Channel filter tabs
    filterTabs.forEach(tab => {
        tab.addEventListener("click", () => {
            filterTabs.forEach(t => t.classList.remove("active"));
            tab.classList.add("active");
            currentFilter = tab.dataset.channel || "all";
            renderSessionList();
        });
    });

    // Rename Session Modal Logic
    function openRenameModal(sessionId, currentTitle) {
        targetActionSessionId = sessionId;
        renameSessionInput.value = currentTitle;
        renameModal.classList.remove("hidden");
        setTimeout(() => renameSessionInput.focus(), 100);
    }

    function closeRenameModal() {
        renameModal.classList.add("hidden");
        targetActionSessionId = null;
    }

    closeRenameModalBtn?.addEventListener("click", closeRenameModal);
    cancelRenameBtn?.addEventListener("click", closeRenameModal);

    saveRenameBtn?.addEventListener("click", async () => {
        const newTitle = renameSessionInput.value.trim();
        if (!newTitle) {
            alert("세션 이름을 입력해 주세요.");
            return;
        }

        saveRenameBtn.disabled = true;
        saveRenameBtn.innerText = "변경 중...";

        try {
            const res = await fetch(`/api/sessions/${targetActionSessionId}`, {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ title: newTitle })
            });

            if (res.ok) {
                closeRenameModal();
                await loadSessions();
                if (currentSessionId === targetActionSessionId) {
                    if (activeSessionTitle) activeSessionTitle.innerText = newTitle;
                    if (mobileSessionTitle) mobileSessionTitle.innerText = newTitle.length > 14 ? newTitle.slice(0, 14) + "..." : newTitle;
                }
            } else {
                alert("세션 이름 변경에 실패했습니다.");
            }
        } catch (e) {
            console.error(e);
            alert("서버 연결 중 오류가 발생했습니다.");
        } finally {
            saveRenameBtn.disabled = false;
            saveRenameBtn.innerText = "변경 완료";
        }
    });

    renameSessionInput?.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
            e.preventDefault();
            saveRenameBtn.click();
        }
    });

    // Delete Session Modal Logic
    function openDeleteModal(sessionId, title) {
        targetActionSessionId = sessionId;
        if (deleteModalMsg) {
            deleteModalMsg.innerText = `세션 '${title}' (${sessionId}) 및 모든 대화 기록을 완전히 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.`;
        }
        deleteModal.classList.remove("hidden");
    }

    function closeDeleteModal() {
        deleteModal.classList.add("hidden");
        targetActionSessionId = null;
    }

    closeDeleteModalBtn?.addEventListener("click", closeDeleteModal);
    cancelDeleteBtn?.addEventListener("click", closeDeleteModal);

    confirmDeleteBtn?.addEventListener("click", async () => {
        confirmDeleteBtn.disabled = true;
        confirmDeleteBtn.innerText = "삭제 중...";

        try {
            const res = await fetch(`/api/sessions/${targetActionSessionId}`, {
                method: "DELETE"
            });

            if (res.ok) {
                closeDeleteModal();
                await loadSessions();
                // If deleted session was active, switch to next available or default
                if (currentSessionId === targetActionSessionId) {
                    const nextSession = allSessions.find(s => s.id !== targetActionSessionId);
                    const newId = nextSession ? nextSession.id : "web_default_session";
                    await switchSession(newId);
                }
            } else {
                alert("세션 삭제에 실패했습니다.");
            }
        } catch (e) {
            console.error(e);
            alert("서버 연결 중 오류가 발생했습니다.");
        } finally {
            confirmDeleteBtn.disabled = false;
            confirmDeleteBtn.innerHTML = '<i class="fa-solid fa-trash"></i> 삭제';
        }
    });

    // Clear Chat Messages Modal Logic
    clearChatBtn?.addEventListener("click", () => {
        clearModal.classList.remove("hidden");
    });

    closeClearModalBtn?.addEventListener("click", () => clearModal.classList.add("hidden"));
    cancelClearBtn?.addEventListener("click", () => clearModal.classList.add("hidden"));

    confirmClearBtn?.addEventListener("click", async () => {
        confirmClearBtn.disabled = true;
        confirmClearBtn.innerText = "비우는 중...";

        try {
            const res = await fetch(`/api/sessions/${currentSessionId}/clear`, {
                method: "POST"
            });

            if (res.ok) {
                clearModal.classList.add("hidden");
                chatMessages.innerHTML = "";
                appendMessage("assistant", "대화 내용이 초기화되었습니다. 새로운 기록을 남겨보세요! 🤖");
                await loadSessions();
                if (activeSessionMeta) {
                    activeSessionMeta.innerText = `웹 대화 세션 • 메시지 0개 • ${currentSessionId}`;
                }
            } else {
                alert("대화 내용 비우기에 실패했습니다.");
            }
        } catch (e) {
            console.error(e);
            alert("서버 연결 중 오류가 발생했습니다.");
        } finally {
            confirmClearBtn.disabled = false;
            confirmClearBtn.innerHTML = '<i class="fa-solid fa-broom"></i> 비우기';
        }
    });

    function renderHistory(history) {
        chatMessages.innerHTML = "";
        if (!history || history.length === 0) {
            appendMessage("assistant", "안녕하세요! 새 세션이 시작되었습니다. 무엇이든 기록해 주세요! 🤖");
            return;
        }
        history.forEach(msg => {
            appendMessage(msg.role, msg.content);
        });
        scrollToBottom();
    }

    function appendMessage(role, text) {
        const msgDiv = document.createElement("div");
        msgDiv.className = `message ${role}`;

        const avatar = document.createElement("div");
        avatar.className = "avatar";
        avatar.innerHTML = role === "user" ? '<i class="fa-solid fa-user"></i>' : '<i class="fa-solid fa-robot"></i>';

        const bubble = document.createElement("div");
        bubble.className = "bubble";
        bubble.innerText = text;

        msgDiv.appendChild(avatar);
        msgDiv.appendChild(bubble);
        chatMessages.appendChild(msgDiv);
        scrollToBottom();
    }

    function scrollToBottom() {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function appendQuickActions() {
        const actionDiv = document.createElement("div");
        actionDiv.className = "quick-actions-container";
        actionDiv.innerHTML = `
            <button class="btn-quick approve" id="btn-quick-approve"><i class="fa-solid fa-check"></i> 응, 기록해줘</button>
            <button class="btn-quick reject" id="btn-quick-reject"><i class="fa-solid fa-xmark"></i> 아니야</button>
        `;
        chatMessages.appendChild(actionDiv);
        scrollToBottom();

        document.getElementById("btn-quick-approve")?.addEventListener("click", () => {
            actionDiv.remove();
            sendTextMessage("응 좋아");
        });

        document.getElementById("btn-quick-reject")?.addEventListener("click", () => {
            actionDiv.remove();
            sendTextMessage("아니 괜찮아");
        });
    }

    async function sendTextMessage(text) {
        if (!text) return;
        appendMessage("user", text);
        chatInput.value = "";
        chatInput.style.height = "";

        sendBtn.disabled = true;
        sendBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';

        try {
            const res = await fetchWithRetry("/api/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    session_id: currentSessionId,
                    message: text,
                    category: categorySelect.value
                })
            }, 2, 1500);

            if (res.ok) {
                updateConnectionUI("online");
                const data = await res.json();
                appendMessage("assistant", data.ai_response);
                if (data.intent === "log_suggest") {
                    appendQuickActions();
                }
                if (data.git_pushed) {
                    appendMessage("assistant", `✅ [Git 커밋 완료] ${data.filepath} 저장됨.`);
                }
                await loadSessions();
            } else {
                appendMessage("assistant", "⚠️ 처리 중 오류가 발생했습니다.");
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
                        renderHistory(hist);
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
            sendBtn.innerHTML = '<i class="fa-solid fa-paper-plane"></i> <span class="desktop-only">전송</span>';
        }
    }

    // Auto-resize textarea on input
    chatInput.addEventListener("input", () => {
        chatInput.style.height = "auto";
        chatInput.style.height = Math.min(chatInput.scrollHeight, 120) + "px";
    });

    // Send Message Handler
    sendBtn.addEventListener("click", () => {
        const text = chatInput.value.trim();
        if (text) {
            sendTextMessage(text);
        }
    });

    // Watson Quick Shortcut Chips (ADR-022)
    const watsonChips = document.querySelectorAll(".watson-chip-btn");
    watsonChips.forEach(chip => {
        chip.addEventListener("click", () => {
            const cmd = chip.dataset.cmd;
            if (cmd) sendTextMessage(cmd);
        });
    });

    chatInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            sendBtn.click();
        }
    });

    newSessionBtn.addEventListener("click", () => {
        const newId = `web_session_${Date.now()}`;
        if (window.innerWidth <= 768) {
            closeSidebar();
        }
        switchSession(newId);
    });

    // GTD Directory Management (ADR-007)
    const gtdStorageBadge = document.getElementById("gtd-storage-badge");
    const gtdPathText = document.getElementById("gtd-path-text");
    const changeGtdBtn = document.getElementById("change-gtd-btn");
    const gtdModal = document.getElementById("gtd-modal");
    const closeGtdModalBtn = document.getElementById("close-gtd-modal-btn");
    const cancelGtdBtn = document.getElementById("cancel-gtd-btn");
    const saveGtdBtn = document.getElementById("save-gtd-btn");
    const gtdPathInput = document.getElementById("gtd-path-input");
    const gtdModalStatus = document.getElementById("gtd-modal-status");

    async function loadGTDStatus() {
        try {
            const res = await fetch("/api/settings/gtd-path");
            if (res.ok) {
                const data = await res.json();
                const shortPath = data.gtd_path.split("/").slice(-2).join("/");
                gtdPathText.innerText = `GTD: ${shortPath} ${data.is_git_repo ? '⚡Git' : '📁Local'}`;
                gtdPathText.title = `경로: ${data.gtd_path} (${data.is_git_repo ? '독립 Git 레포지토리 연동' : '로컬 보관'})`;

                if (data.is_git_repo) {
                    gtdStorageBadge.classList.add("git-active");
                } else {
                    gtdStorageBadge.classList.remove("git-active");
                }

                gtdPathInput.value = data.gtd_path;
                updateModalStatusBox(data);
            }
        } catch (e) {
            console.error("Failed to load GTD status", e);
            gtdPathText.innerText = "GTD: 경로 오류";
        }
    }

    function updateModalStatusBox(data) {
        gtdModalStatus.innerHTML = `
            <strong>현재 연동 정보:</strong><br>
            • 전체 경로: <code>${data.gtd_path}</code><br>
            • Git 버전 관리: ${data.is_git_repo ? '<span style="color:#34d399">✅ 활성화 (독립 커밋/푸시)</span>' : '<span style="color:#94a3b8">📁 로컬 파일 전용 (Git 미연동)</span>'}<br>
            • 격리 모드: ${data.is_external ? '<span style="color:#60a5fa">외부 분리 저장소 (External)</span>' : '봇 소스코드 기본'}<br>
            • 구조 체계: <code>${data.structure_type}</code> (Inbox: ${data.has_inbox ? '있음' : '없음'}, Daily Logs: ${data.has_daily_logs ? '있음' : '없음'})
        `;
    }

    function openGTDModal() {
        gtdModal.classList.remove("hidden");
    }

    function closeGTDModal() {
        gtdModal.classList.add("hidden");
    }

    changeGtdBtn?.addEventListener("click", (e) => {
        e.stopPropagation();
        openGTDModal();
    });

    gtdStorageBadge?.addEventListener("click", () => {
        openGTDModal();
    });

    closeGtdModalBtn?.addEventListener("click", closeGTDModal);
    cancelGtdBtn?.addEventListener("click", closeGTDModal);

    gtdModal?.addEventListener("click", (e) => {
        if (e.target === gtdModal) {
            closeGTDModal();
        }
    });

    saveGtdBtn?.addEventListener("click", async () => {
        const newPath = gtdPathInput.value.trim();
        if (!newPath) {
            alert("디렉토리 경로를 입력해 주세요.");
            return;
        }

        saveGtdBtn.disabled = true;
        saveGtdBtn.innerText = "저장 중...";

        try {
            const res = await fetch("/api/settings/gtd-path", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ path: newPath, create_if_missing: true })
            });

            const result = await res.json();
            if (res.ok) {
                alert(`✅ GTD 관리 경로가 성공적으로 설정되었습니다!\n경로: ${result.data.gtd_path}`);
                await loadGTDStatus();
                closeGTDModal();
            } else {
                alert(`⚠️ 설정 실패: ${result.detail || "경로를 확인해 주세요."}`);
            }
        } catch (e) {
            console.error(e);
            alert("⚠️ 서버 통신 중 오류가 발생했습니다.");
        } finally {
            saveGtdBtn.disabled = false;
            saveGtdBtn.innerText = "저장 및 적용";
        }
    });

    // Lifecycle & Connection Event Listeners (ADR-021)
    document.addEventListener("visibilitychange", () => {
        if (!document.hidden) {
            console.log("[Connection] Tab became visible. Checking health & syncing history...");
            checkHealth();
        }
    });

    window.addEventListener("online", () => {
        console.log("[Connection] Browser reported online.");
        updateConnectionUI("warning", "네트워크 복구 감지됨. 연결 확인 중...");
        checkHealth();
    });

    window.addEventListener("offline", () => {
        console.log("[Connection] Browser reported offline.");
        updateConnectionUI("offline");
    });

    reconnectBtn?.addEventListener("click", () => {
        updateConnectionUI("warning", "수동 재연결 시도 중...");
        checkHealth();
    });

    // Initial Load & Heartbeat (every 25 seconds)
    loadSessions(true);
    loadGTDStatus();
    checkHealth();
    setInterval(checkHealth, 25000);
});
