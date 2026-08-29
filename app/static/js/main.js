document.addEventListener("DOMContentLoaded", () => {
    let currentSessionId = "web_default_session";

    const chatMessages = document.getElementById("chat-messages");
    const chatInput = document.getElementById("chat-input");
    const sendBtn = document.getElementById("send-btn");
    const categorySelect = document.getElementById("category-select");
    const sessionList = document.getElementById("session-list");
    const newSessionBtn = document.getElementById("new-session-btn");

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

    // Send Message Handler
    sendBtn.addEventListener("click", async () => {
        const text = chatInput.value.trim();
        if (!text) return;

        appendMessage("user", text);
        chatInput.value = "";

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
                if (data.git_pushed) {
                    appendMessage("assistant", `✅ [Git Push 완료] ${data.filepath} 저장됨.`);
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
            sendBtn.innerHTML = '<i class="fa-solid fa-paper-plane"></i> 전송';
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
        switchSession(newId);
    });

    // Initial Load
    loadSessions();
});
