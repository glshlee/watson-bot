document.addEventListener("DOMContentLoaded", () => {
    let currentSessionId = "web_default_session";

    const chatMessages = document.getElementById("chat-messages");
    const chatInput = document.getElementById("chat-input");
    const sendBtn = document.getElementById("send-btn");
    const categorySelect = document.getElementById("category-select");
    const sessionList = document.getElementById("session-list");
    const newSessionBtn = document.getElementById("new-session-btn");
    const mobileMenuBtn = document.getElementById("mobile-menu-btn");
    const closeSidebarBtn = document.getElementById("close-sidebar-btn");
    const sidebar = document.getElementById("sidebar");
    const sidebarBackdrop = document.getElementById("sidebar-backdrop");

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

    // Fetch and render session list
    async function loadSessions() {
        try {
            const res = await fetch("/api/sessions");
            if (res.ok) {
                const sessions = await res.json();
                sessionList.innerHTML = "";
                sessions.forEach(s => {
                    const item = document.createElement("div");
                    item.className = `session-item ${s.id === currentSessionId ? 'active' : ''}`;
                    item.innerText = s.title || s.id;
                    item.onclick = () => switchSession(s.id);
                    sessionList.appendChild(item);
                });
            }
        } catch (e) {
            console.error("Failed to load sessions", e);
        }
    }

    // Switch Session and load history
    async function switchSession(sessionId) {
        currentSessionId = sessionId;
        if (window.innerWidth <= 768) {
            closeSidebar();
        }
        await loadSessions();
        try {
            const res = await fetch(`/api/sessions/${sessionId}/history`);
            if (res.ok) {
                const data = await res.json();
                renderHistory(data.history);
            }
        } catch (e) {
            console.error("Failed to load session history", e);
        }
    }

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
            const res = await fetch("/api/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    session_id: currentSessionId,
                    message: text,
                    category: categorySelect.value
                })
            });

            if (res.ok) {
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
            appendMessage("assistant", "⚠️ 서버 연결 오류가 발생했습니다.");
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

    // Initial Load
    loadSessions();
    loadGTDStatus();
});
