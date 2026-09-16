/**
 * Watson AI Agent - Main Application Controller (Session & Chat Engine)
 * Modular Architecture (ADR-048, ADR-050 / Phase 2)
 */
document.addEventListener("DOMContentLoaded", () => {
    // Shared Utilities from WatsonDate & WatsonAPI
    const formatRelativeTime = window.WatsonDate?.formatRelativeTime || window.formatRelativeTime;
    const fetchWithRetry = window.WatsonAPI?.fetchWithRetry || window.fetchWithRetry || fetch;
    const updateConnectionUI = window.WatsonAPI?.updateConnectionUI || window.updateConnectionUI || (() => {});
    const checkHealth = window.WatsonAPI?.checkHealth || (() => {});

    // State Variables
    let currentSessionId = "web_default_session";
    let allSessions = [];
    let currentFilter = "all";
    let searchQuery = "";
    let targetActionSessionId = null;

    // DOM Elements - Chat & Input
    const chatMessages = document.getElementById("chat-messages");
    const chatInput = document.getElementById("chat-input");
    const sendBtn = document.getElementById("send-btn");
    const categorySelect = document.getElementById("category-select");

    // DOM Elements - Sidebar & Sessions
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

    // DOM Elements - Session Modals
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

    // Connection Banner Reconnect
    const reconnectBtn = document.getElementById("reconnect-btn");

    // Sync active session history upon reconnect
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
                if (data.history && data.history.length > 0 && data.history[data.history.length - 1].role === "assistant") {
                    sendBtn.disabled = false;
                    sendBtn.innerHTML = '<i class="fa-solid fa-paper-plane"></i> <span class="desktop-only">전송</span>';
                }
            }
        } catch (e) {
            console.debug("Failed to sync session history:", e);
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
        if (!sessionList) return;
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

        document.querySelectorAll(".session-item").forEach(el => {
            el.classList.toggle("active", el.dataset.id === sessionId);
        });

        try {
            const res = await fetch(`/api/sessions/${sessionId}/history`);
            if (res.ok) {
                const data = await res.json();
                renderHistory(data.history);

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
        if (renameSessionInput) renameSessionInput.value = currentTitle;
        renameModal?.classList.remove("hidden");
        setTimeout(() => renameSessionInput?.focus(), 100);
    }

    function closeRenameModal() {
        renameModal?.classList.add("hidden");
        targetActionSessionId = null;
    }

    closeRenameModalBtn?.addEventListener("click", closeRenameModal);
    cancelRenameBtn?.addEventListener("click", closeRenameModal);

    saveRenameBtn?.addEventListener("click", async () => {
        const newTitle = renameSessionInput?.value.trim();
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
            saveRenameBtn?.click();
        }
    });

    // Delete Session Modal Logic
    function openDeleteModal(sessionId, title) {
        targetActionSessionId = sessionId;
        if (deleteModalMsg) {
            deleteModalMsg.innerText = `세션 '${title}' (${sessionId}) 및 모든 대화 기록을 완전히 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.`;
        }
        deleteModal?.classList.remove("hidden");
    }

    function closeDeleteModal() {
        deleteModal?.classList.add("hidden");
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
        clearModal?.classList.remove("hidden");
    });

    closeClearModalBtn?.addEventListener("click", () => clearModal?.classList.add("hidden"));
    cancelClearBtn?.addEventListener("click", () => clearModal?.classList.add("hidden"));

    confirmClearBtn?.addEventListener("click", async () => {
        confirmClearBtn.disabled = true;
        confirmClearBtn.innerText = "비우는 중...";

        try {
            const res = await fetch(`/api/sessions/${currentSessionId}/clear`, {
                method: "POST"
            });

            if (res.ok) {
                clearModal?.classList.add("hidden");
                if (chatMessages) chatMessages.innerHTML = "";
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

    // Chat Message Rendering & Scroll
    function renderHistory(history) {
        if (!chatMessages) return;
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
        if (!chatMessages) return;
        const msgDiv = document.createElement("div");
        msgDiv.className = `message ${role}`;

        const avatar = document.createElement("div");
        avatar.className = "avatar";
        avatar.innerHTML = role === "user" ? '<i class="fa-solid fa-user"></i>' : '<i class="fa-solid fa-robot"></i>';

        const bubble = document.createElement("div");
        bubble.className = "bubble";

        const textContent = document.createElement("div");
        textContent.className = "bubble-text";
        textContent.innerText = text;
        bubble.appendChild(textContent);

        // Real-time bus arrival inline refresh (ADR-039)
        const isBusCard = role === "assistant" && typeof text === "string" && (
            text.includes("[실시간 출근 버스 도착 정보]") ||
            text.includes("출근길 버스 현황") ||
            text.includes("출근길 버스 정보") ||
            text.includes("• 🚌 **출근길 버스")
        );

        if (isBusCard) {
            const actionBar = document.createElement("div");
            actionBar.className = "bus-refresh-bar";
            actionBar.innerHTML = `
                <button type="button" class="btn-bus-refresh" title="실시간 버스 도착 정보 즉시 갱신">
                    <i class="fa-solid fa-arrows-rotate"></i> 버스 도착 갱신
                </button>
                <span class="bus-refresh-badge"></span>
            `;
            const refreshBtn = actionBar.querySelector(".btn-bus-refresh");
            const badgeSpan = actionBar.querySelector(".bus-refresh-badge");

            refreshBtn.addEventListener("click", async () => {
                refreshBtn.disabled = true;
                refreshBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> 갱신 중...';
                badgeSpan.innerHTML = "";
                try {
                    const res = await fetchWithRetry("/api/settings/commute/bus-card", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" }
                    }, 1, 1000);
                    if (res.ok) {
                        const data = await res.json();
                        if (data.success) {
                            if (textContent.innerText.includes("[실시간 출근 버스 도착 정보]")) {
                                textContent.innerText = data.markdown;
                            } else if (data.transit_line && textContent.innerText.includes("• 🚌 **출근길 버스")) {
                                textContent.innerText = textContent.innerText.replace(/•\s*🚌\s*\*\*출근길 버스.*$/m, data.transit_line);
                            } else if (data.markdown) {
                                textContent.innerText = data.markdown;
                            }
                            badgeSpan.innerHTML = `<span class="refresh-success"><i class="fa-solid fa-check"></i> ${data.updated_time} 갱신됨</span>`;
                        } else {
                            badgeSpan.innerHTML = `<span class="refresh-fail">갱신 실패</span>`;
                        }
                    } else {
                        badgeSpan.innerHTML = `<span class="refresh-fail">서버 오류</span>`;
                    }
                } catch (err) {
                    console.error("Bus refresh error:", err);
                    badgeSpan.innerHTML = `<span class="refresh-fail">연결 지연</span>`;
                } finally {
                    refreshBtn.disabled = false;
                    refreshBtn.innerHTML = '<i class="fa-solid fa-arrows-rotate"></i> 버스 도착 갱신';
                }
            });

            bubble.appendChild(actionBar);
        }

        msgDiv.appendChild(avatar);
        msgDiv.appendChild(bubble);
        chatMessages.appendChild(msgDiv);
        scrollToBottom();
    }

    function scrollToBottom() {
        if (chatMessages) chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function appendQuickActions() {
        if (!chatMessages) return;
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
        if (chatInput) {
            chatInput.value = "";
            chatInput.style.height = "";
        }

        if (sendBtn) {
            sendBtn.disabled = true;
            sendBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';
        }

        try {
            const res = await fetchWithRetry("/api/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    session_id: currentSessionId,
                    message: text,
                    category: categorySelect ? categorySelect.value : "Daily Notes & Diary"
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
            if (sendBtn) {
                sendBtn.disabled = false;
                sendBtn.innerHTML = '<i class="fa-solid fa-paper-plane"></i> <span class="desktop-only">전송</span>';
            }
        }
    }

    // Auto-resize textarea on input
    chatInput?.addEventListener("input", () => {
        chatInput.style.height = "auto";
        chatInput.style.height = Math.min(chatInput.scrollHeight, 120) + "px";
    });

    // Send Message Handler
    sendBtn?.addEventListener("click", () => {
        const text = chatInput?.value.trim();
        if (text) sendTextMessage(text);
    });

    // Watson Quick Shortcut Chips (ADR-022)
    const watsonChips = document.querySelectorAll(".watson-chip-btn");
    watsonChips.forEach(chip => {
        chip.addEventListener("click", () => {
            const cmd = chip.dataset.cmd;
            if (cmd) sendTextMessage(cmd);
        });
    });

    chatInput?.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            sendBtn?.click();
        }
    });

    newSessionBtn?.addEventListener("click", () => {
        const newId = `web_session_${Date.now()}`;
        if (window.innerWidth <= 768) closeSidebar();
        switchSession(newId);
    });

    // URL parameter auto opener (?edit=YYYY-MM-DD)
    function checkUrlEditParam() {
        const params = new URLSearchParams(window.location.search);
        const editDate = params.get("edit");
        if (editDate && window.WatsonEditor?.openEditorModal) {
            const cleanDate = (editDate === "today" || !editDate.match(/^\d{4}-\d{2}-\d{2}$/)) ? null : editDate;
            window.WatsonEditor.openEditorModal(cleanDate);
        }
    }

    // Lifecycle & Connection Event Listeners (ADR-021)
    document.addEventListener("visibilitychange", async () => {
        if (!document.hidden) {
            console.log("[Connection] Tab became visible. Checking health & syncing history...");
            checkHealth(syncActiveSessionHistory);
        }
    });

    window.addEventListener("online", () => {
        console.log("[Connection] Browser reported online.");
        updateConnectionUI("warning", "네트워크 복구 감지됨. 연결 확인 중...");
        checkHealth(syncActiveSessionHistory);
    });

    window.addEventListener("offline", () => {
        console.log("[Connection] Browser reported offline.");
        updateConnectionUI("offline");
    });

    reconnectBtn?.addEventListener("click", () => {
        updateConnectionUI("warning", "수동 재연결 시도 중...");
        checkHealth(syncActiveSessionHistory);
    });

    // Initialize all modular controllers
    window.WatsonGTD?.initGTDModal();
    window.WatsonSchedule?.initScheduleModal({
        onTriggerCommand: (cmd) => sendTextMessage(cmd)
    });
    window.WatsonCommute?.initCommuteModal();
    window.WatsonTelegram?.initTelegramModal();
    window.WatsonEditor?.initEditorModal();

    // Initial Load & Heartbeat
    loadSessions(true);
    checkUrlEditParam();
    window.WatsonDate?.updateLiveClock();
    setInterval(() => window.WatsonDate?.updateLiveClock(), 1000);
    checkHealth();
    setInterval(() => checkHealth(syncActiveSessionHistory), 25000);
});
