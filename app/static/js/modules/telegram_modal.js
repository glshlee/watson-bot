/**
 * Watson AI Agent - Telegram Bot Menu Commands Management Modal Controller (ADR-041, ADR-050)
 */
(function() {
    let telegramInitialized = false;
    let telegramCommandsState = [];

    async function loadTelegramCommands() {
        const tgStatusConfigured = document.getElementById("tg-status-configured");
        const tgChatIdBadge = document.getElementById("tg-chat-id-badge");

        try {
            const fetchFn = window.WatsonAPI?.fetchWithRetry || window.fetchWithRetry || fetch;
            const [cmdsRes, statusRes] = await Promise.all([
                fetchFn("/api/telegram/commands"),
                fetchFn("/api/telegram/status")
            ]);

            if (statusRes.ok) {
                const sData = await statusRes.json();
                if (tgStatusConfigured) {
                    tgStatusConfigured.textContent = sData.configured ? "정상 연동" : "토큰 미설정";
                    tgStatusConfigured.className = sData.configured ? "text-success" : "text-muted";
                }
                if (tgChatIdBadge) {
                    const ids = sData.allowed_chat_ids || [];
                    tgChatIdBadge.textContent = ids.length > 0 ? ids.join(", ") : "전체 허용";
                }
            }

            if (cmdsRes.ok) {
                const data = await cmdsRes.json();
                telegramCommandsState = (data.commands || []).map(cmd => ({
                    command: (cmd.command || "").toLowerCase().replace(/^\//, ""),
                    description: cmd.description || "",
                    enabled: cmd.enabled !== false
                }));

                renderTelegramCommands();
                updateTelegramBadge();
            }
        } catch (e) {
            console.error("[Telegram] Failed to load telegram commands:", e);
        }
    }

    function updateTelegramBadge() {
        const telegramMenuText = document.getElementById("telegram-menu-text");
        const tgActiveCountBadge = document.getElementById("tg-active-count-badge");
        const tgTotalCountBadge = document.getElementById("tg-total-count-badge");
        const commandsListCount = document.getElementById("commands-list-count");

        const activeCount = telegramCommandsState.filter(c => c.enabled).length;
        if (telegramMenuText) {
            telegramMenuText.textContent = `메뉴: ${activeCount}개`;
        }
        if (tgActiveCountBadge) {
            tgActiveCountBadge.textContent = activeCount;
        }
        if (tgTotalCountBadge) {
            tgTotalCountBadge.textContent = telegramCommandsState.length;
        }
        if (commandsListCount) {
            commandsListCount.textContent = telegramCommandsState.length;
        }
    }

    function updateTelegramPreview() {
        const mockTgMenuPopup = document.getElementById("mock-tg-menu-popup");
        if (!mockTgMenuPopup) return;
        const escapeHtml = window.WatsonModal?.escapeHtml || window.escapeHtml || (s => s);
        const activeList = telegramCommandsState.filter(c => c.enabled);
        if (activeList.length === 0) {
            mockTgMenuPopup.innerHTML = '<div style="padding: 16px; text-align: center; color: #7f91a4; font-size: 0.75rem;">활성화된 명령어가 없습니다.</div>';
            return;
        }

        mockTgMenuPopup.innerHTML = activeList.map(item => `
            <div class="mock-tg-item" data-cmd="${escapeHtml(item.command)}">
                <span class="mock-tg-cmd">/${escapeHtml(item.command)}</span>
                <span class="mock-tg-desc">${escapeHtml(item.description)}</span>
            </div>
        `).join("");
    }

    function renderTelegramCommands() {
        const telegramCommandsList = document.getElementById("telegram-commands-list");
        if (!telegramCommandsList) return;
        const escapeHtml = window.WatsonModal?.escapeHtml || window.escapeHtml || (s => s);
        telegramCommandsList.innerHTML = "";

        telegramCommandsState.forEach((item, index) => {
            const row = document.createElement("div");
            row.className = `cmd-row-item ${item.enabled ? "" : "disabled"}`;
            row.dataset.index = index;

            row.innerHTML = `
                <label class="cmd-toggle-label" title="${item.enabled ? '메뉴에서 제외하기' : '메뉴에 포함하기'}">
                    <input type="checkbox" class="cmd-toggle-chk" ${item.enabled ? "checked" : ""}>
                </label>
                <div class="cmd-name-input-group">
                    <span class="prefix">/</span>
                    <input type="text" class="cmd-name-input" value="${escapeHtml(item.command)}" maxlength="32" placeholder="명령어">
                </div>
                <input type="text" class="cmd-desc-input" value="${escapeHtml(item.description)}" maxlength="256" placeholder="설명">
                <button type="button" class="cmd-delete-btn" title="명령어 삭제"><i class="fa-solid fa-trash-can"></i></button>
            `;

            const chk = row.querySelector(".cmd-toggle-chk");
            const nameInput = row.querySelector(".cmd-name-input");
            const descInput = row.querySelector(".cmd-desc-input");
            const delBtn = row.querySelector(".cmd-delete-btn");

            chk.addEventListener("change", () => {
                telegramCommandsState[index].enabled = chk.checked;
                row.classList.toggle("disabled", !chk.checked);
                updateTelegramBadge();
                updateTelegramPreview();
            });

            nameInput.addEventListener("input", () => {
                const cleaned = nameInput.value.trim().toLowerCase().replace(/[^a-z0-9_]/g, "").slice(0, 32);
                telegramCommandsState[index].command = cleaned;
                updateTelegramPreview();
            });

            descInput.addEventListener("input", () => {
                telegramCommandsState[index].description = descInput.value.trim();
                updateTelegramPreview();
            });

            delBtn.addEventListener("click", () => {
                if (confirm(`'/${item.command}' 명령어를 목록에서 삭제하시겠습니까?`)) {
                    telegramCommandsState.splice(index, 1);
                    renderTelegramCommands();
                    updateTelegramBadge();
                    updateTelegramPreview();
                }
            });

            telegramCommandsList.appendChild(row);
        });

        updateTelegramBadge();
        updateTelegramPreview();
    }

    function openTelegramMenuModal() {
        const telegramMenuModal = document.getElementById("telegram-menu-modal");
        telegramMenuModal?.classList.remove("hidden");
        loadTelegramCommands();
    }

    function closeTelegramMenuModal() {
        const telegramMenuModal = document.getElementById("telegram-menu-modal");
        telegramMenuModal?.classList.add("hidden");
    }

    function initTelegramModal() {
        if (telegramInitialized) return;
        telegramInitialized = true;

        const telegramMenuModal = document.getElementById("telegram-menu-modal");
        const telegramMenuBadge = document.getElementById("telegram-menu-badge");
        const openTelegramMenuBtn = document.getElementById("open-telegram-menu-btn");
        const btnTelegramMenuView = document.getElementById("btn-telegram-menu-view");
        const closeTelegramMenuModalBtn = document.getElementById("close-telegram-menu-modal-btn");
        const cancelTelegramMenuBtn = document.getElementById("cancel-telegram-menu-btn");
        const saveTelegramMenuBtn = document.getElementById("save-telegram-menu-btn");
        const btnResetTelegramCommands = document.getElementById("btn-reset-telegram-commands");
        const btnAddCommand = document.getElementById("btn-add-command");
        const newCmdName = document.getElementById("new-cmd-name");
        const newCmdDesc = document.getElementById("new-cmd-desc");
        const telegramCommandsList = document.getElementById("telegram-commands-list");

        function addNewCommand() {
            if (!newCmdName || !newCmdDesc) return;
            const rawCmd = newCmdName.value.trim().toLowerCase().replace(/^\//, "");
            const cleanCmd = rawCmd.replace(/[^a-z0-9_]/g, "").slice(0, 32);
            const desc = newCmdDesc.value.trim().slice(0, 256);

            if (!cleanCmd) {
                alert("명령어 이름을 영문 소문자/숫자/언더스코어로 입력해 주세요. (1~32자)");
                newCmdName.focus();
                return;
            }

            if (telegramCommandsState.some(c => c.command === cleanCmd)) {
                alert(`이미 등록된 명령어 '/${cleanCmd}' 입니다.`);
                newCmdName.focus();
                return;
            }

            telegramCommandsState.push({
                command: cleanCmd,
                description: desc || cleanCmd,
                enabled: true
            });

            newCmdName.value = "";
            newCmdDesc.value = "";

            renderTelegramCommands();
            updateTelegramBadge();
            updateTelegramPreview();

            if (telegramCommandsList) {
                telegramCommandsList.scrollTop = telegramCommandsList.scrollHeight;
            }
        }

        async function saveTelegramCommands() {
            if (!saveTelegramMenuBtn) return;
            saveTelegramMenuBtn.disabled = true;
            saveTelegramMenuBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> 텔레그램 동기화 중...';

            try {
                const payload = {
                    commands: telegramCommandsState,
                    sync_to_telegram: true
                };

                const fetchFn = window.WatsonAPI?.fetchWithRetry || window.fetchWithRetry || fetch;
                const res = await fetchFn("/api/telegram/commands", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(payload)
                });

                if (res.ok) {
                    const data = await res.json();
                    const activeCount = data.active_count || 0;
                    alert(`✅ 텔레그램 봇 메뉴 설정이 성공적으로 저장되었습니다!\n\n• 총 명령어: ${data.saved_count}개\n• 텔레그램 활성 메뉴: ${activeCount}개\n• 텔레그램 API 동기화: ${data.synced ? "성공 (반영 완료)" : "토큰 미설정 또는 미반영"}`);
                    closeTelegramMenuModal();
                    loadTelegramCommands();
                } else {
                    const err = await res.json();
                    alert(`⚠️ 저장 실패: ${err.detail || "알 수 없는 오류"}`);
                }
            } catch (e) {
                alert(`⚠️ 서버 통신 오류: ${e.message}`);
            } finally {
                saveTelegramMenuBtn.disabled = false;
                saveTelegramMenuBtn.innerHTML = '<i class="fa-solid fa-cloud-arrow-up"></i> 텔레그램에 즉시 반영';
            }
        }

        async function resetTelegramCommands() {
            if (!confirm("텔레그램 봇 메뉴를 기본 14종 표준 명령어로 복원하시겠습니까?")) {
                return;
            }

            if (!btnResetTelegramCommands) return;
            btnResetTelegramCommands.disabled = true;

            try {
                const fetchFn = window.WatsonAPI?.fetchWithRetry || window.fetchWithRetry || fetch;
                const res = await fetchFn("/api/telegram/commands/reset", {
                    method: "POST"
                });

                if (res.ok) {
                    alert(`✅ 기본 14종 명령어로 초기화 및 텔레그램 동기화가 완료되었습니다!`);
                    await loadTelegramCommands();
                } else {
                    alert("⚠️ 기본값 복원 실패");
                }
            } catch (e) {
                alert(`⚠️ 통신 오류: ${e.message}`);
            } finally {
                btnResetTelegramCommands.disabled = false;
            }
        }

        telegramMenuBadge?.addEventListener("click", openTelegramMenuModal);
        openTelegramMenuBtn?.addEventListener("click", (e) => {
            e.stopPropagation();
            openTelegramMenuModal();
        });
        btnTelegramMenuView?.addEventListener("click", openTelegramMenuModal);
        closeTelegramMenuModalBtn?.addEventListener("click", closeTelegramMenuModal);
        cancelTelegramMenuBtn?.addEventListener("click", closeTelegramMenuModal);
        saveTelegramMenuBtn?.addEventListener("click", saveTelegramCommands);
        btnResetTelegramCommands?.addEventListener("click", resetTelegramCommands);
        btnAddCommand?.addEventListener("click", addNewCommand);
        newCmdName?.addEventListener("keydown", (e) => {
            if (e.key === "Enter") {
                e.preventDefault();
                addNewCommand();
            }
        });
        newCmdDesc?.addEventListener("keydown", (e) => {
            if (e.key === "Enter") {
                e.preventDefault();
                addNewCommand();
            }
        });

        loadTelegramCommands();
    }

    window.WatsonTelegram = {
        initTelegramModal,
        openTelegramMenuModal,
        closeTelegramMenuModal,
        loadTelegramCommands
    };
})();
