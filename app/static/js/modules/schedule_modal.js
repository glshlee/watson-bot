/**
 * Watson AI Agent - Schedule & Briefing Timeline Modal Controller (ADR-025, ADR-026, ADR-050)
 */
(function() {
    let scheduleInitialized = false;
    let onTriggerCommandCallback = null;

    async function openScheduleModal() {
        const scheduleModal = document.getElementById("schedule-modal");
        const scheduleModalBody = document.getElementById("schedule-modal-body");
        if (!scheduleModal || !scheduleModalBody) return;

        scheduleModal.classList.remove("hidden");
        scheduleModalBody.innerHTML = `
            <div class="schedule-loading" style="text-align:center; padding:30px; color:var(--text-secondary);">
                <i class="fa-solid fa-spinner fa-spin fa-2x"></i>
                <p style="margin-top:10px; font-size:0.9rem;">스케줄 정보를 불러오는 중...</p>
            </div>
        `;

        try {
            const fetchFn = window.WatsonAPI?.fetchWithRetry || window.fetchWithRetry || fetch;
            const res = await fetchFn("/api/briefing/schedule");
            if (res.ok) {
                const json = await res.json();
                renderScheduleModalContent(json.data);
            } else {
                scheduleModalBody.innerHTML = `<p style="color:#ef4444; padding:20px;">스케줄 정보를 불러오지 못했습니다. (${res.status})</p>`;
            }
        } catch (e) {
            scheduleModalBody.innerHTML = `<p style="color:#ef4444; padding:20px;">스케줄 로딩 오류: ${e.message}</p>`;
        }
    }

    function renderScheduleModalContent(data) {
        const scheduleModalBody = document.getElementById("schedule-modal-body");
        if (!scheduleModalBody) return;
        const schedules = data.schedules || [];
        const todaySchedules = data.today_schedules || [];
        const escapeHtml = window.WatsonModal?.escapeHtml || window.escapeHtml || (s => s);

        let scheduleCardsHtml = schedules.map(s => `
            <div class="schedule-card ${s.is_active ? 'active' : ''}">
                <div class="schedule-card-top">
                    <div class="schedule-card-title">
                        ${s.id === 'morning' ? '🌅' : '🌇'} ${s.title}
                        ${s.is_active ? '<span class="schedule-active-badge" style="font-size:0.7rem; padding:2px 7px;">현재 모드</span>' : ''}
                    </div>
                    <span class="schedule-card-time"><i class="fa-regular fa-clock"></i> ${s.scheduled_time}</span>
                </div>
                <div class="schedule-card-desc">
                    <strong>자동 감지 구간:</strong> ${s.active_range}<br>
                    ${s.summary}
                </div>
                <div class="schedule-card-action">
                    <button class="btn-schedule-trigger" onclick="window.triggerScheduleBriefing('${s.command}')">
                        <i class="fa-solid fa-play"></i> 지금 실행하기
                    </button>
                </div>
            </div>
        `).join("");

        let todayScheduleHtml = "";
        if (todaySchedules.length > 0) {
            todayScheduleHtml = `
                <div class="schedule-today-box" style="margin-top: 14px;">
                    <div class="schedule-today-title"><i class="fa-solid fa-calendar-day"></i> 오늘 일일 로그 주요 일정 (${todaySchedules.length}건)</div>
                    <ul class="schedule-today-list">
                        ${todaySchedules.map(item => `<li class="schedule-today-item">${escapeHtml(item)}</li>`).join("")}
                    </ul>
                </div>
            `;
        } else {
            todayScheduleHtml = `
                <div class="schedule-today-box" style="margin-top: 14px;">
                    <div class="schedule-today-title"><i class="fa-solid fa-calendar-day"></i> 오늘 일일 로그 주요 일정</div>
                    <p style="font-size:0.82rem; color:var(--text-secondary); margin:0;">오늘 작성된 시간별 일정이 없습니다.</p>
                </div>
            `;
        }

        const tgPush = data.telegram_push || {};
        let tgPushHtml = "";
        if (tgPush.enabled) {
            const recipientsStr = (tgPush.recipients || []).join(", ");
            tgPushHtml = `
                <div class="schedule-tg-box" style="margin-top: 14px; background: rgba(44, 165, 224, 0.08); border: 1px solid rgba(44, 165, 224, 0.25); border-radius: 10px; padding: 12px 14px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
                        <div style="font-size: 0.88rem; font-weight: 600; color: #2ca5e0;">
                            <i class="fa-brands fa-telegram"></i> 텔레그램 자동 푸시 알림 (08:30 / 20:00 KST)
                        </div>
                        <span style="font-size: 0.75rem; background: #2ca5e0; color: #fff; padding: 2px 8px; border-radius: 12px;">✅ 활성</span>
                    </div>
                    <div style="font-size: 0.82rem; color: var(--text-secondary); margin-top: 6px; line-height: 1.4;">
                        정기 시각에 왓슨이 텔레그램으로 브리핑을 자동 발송합니다. (수신 Chat ID: <code>${recipientsStr}</code>)
                    </div>
                    <div style="margin-top: 10px; display: flex; align-items: center; gap: 10px; flex-wrap: wrap;">
                        <button id="btn-trigger-push" class="btn-primary" style="font-size: 0.8rem; padding: 6px 12px; background: #2ca5e0; border-color: #2ca5e0;" onclick="window.triggerTelegramTestPush()">
                            <i class="fa-solid fa-paper-plane"></i> 텔레그램으로 지금 즉시 발송
                        </button>
                        <span id="trigger-push-status" style="font-size: 0.8rem; color: var(--text-secondary);"></span>
                    </div>
                </div>
            `;
        }

        scheduleModalBody.innerHTML = `
            <div class="schedule-header-card">
                <div class="schedule-header-time">
                    <span class="schedule-current-time"><i class="fa-regular fa-clock"></i> ${data.current_time}</span>
                    <span class="schedule-current-date">${data.current_date}</span>
                </div>
                <div class="schedule-active-badge">
                    <i class="fa-solid fa-circle-check"></i> ${data.active_mode_label} 가동 중
                </div>
            </div>
            <div class="schedule-cards-grid">
                ${scheduleCardsHtml}
            </div>
            ${todayScheduleHtml}
            ${tgPushHtml}
        `;
    }

    function initScheduleModal(options = {}) {
        if (scheduleInitialized) return;
        scheduleInitialized = true;

        if (typeof options.onTriggerCommand === "function") {
            onTriggerCommandCallback = options.onTriggerCommand;
        }

        const scheduleModal = document.getElementById("schedule-modal");
        const btnScheduleView = document.getElementById("btn-schedule-view");
        const closeScheduleModalBtn = document.getElementById("close-schedule-modal-btn");
        const closeScheduleBtn = document.getElementById("close-schedule-btn");

        if (btnScheduleView) btnScheduleView.addEventListener("click", openScheduleModal);
        if (closeScheduleModalBtn) closeScheduleModalBtn.addEventListener("click", () => scheduleModal?.classList.add("hidden"));
        if (closeScheduleBtn) closeScheduleBtn.addEventListener("click", () => scheduleModal?.classList.add("hidden"));

        scheduleModal?.addEventListener("click", (e) => {
            if (e.target === scheduleModal) scheduleModal.classList.add("hidden");
        });

        window.triggerTelegramTestPush = async function() {
            const statusEl = document.getElementById("trigger-push-status");
            const btn = document.getElementById("btn-trigger-push");
            if (btn) btn.disabled = true;
            if (statusEl) {
                statusEl.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> 텔레그램 발송 중...';
                statusEl.style.color = "var(--text-secondary)";
            }
            try {
                const res = await fetch("/api/briefing/trigger-push", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ mode: "auto" })
                });
                const json = await res.json();
                if (res.ok && json.status === "success") {
                    if (statusEl) {
                        statusEl.innerHTML = `✅ 텔레그램 발송 완료! (${json.data.sent_count}명 수신)`;
                        statusEl.style.color = "#10b981";
                    }
                } else {
                    if (statusEl) {
                        statusEl.innerHTML = `❌ 발송 실패: ${json.detail || "오류"}`;
                        statusEl.style.color = "#ef4444";
                    }
                }
            } catch (e) {
                if (statusEl) {
                    statusEl.innerHTML = `❌ 오류: ${e.message}`;
                    statusEl.style.color = "#ef4444";
                }
            } finally {
                if (btn) btn.disabled = false;
            }
        };

        window.triggerScheduleBriefing = function(cmd) {
            scheduleModal?.classList.add("hidden");
            if (typeof onTriggerCommandCallback === "function") {
                onTriggerCommandCallback(cmd);
            } else {
                const chatInput = document.getElementById("chat-input");
                const sendBtn = document.getElementById("send-btn");
                if (chatInput) {
                    chatInput.value = cmd;
                    sendBtn?.click();
                }
            }
        };
    }

    window.WatsonSchedule = {
        initScheduleModal,
        openScheduleModal,
        renderScheduleModalContent
    };
})();
