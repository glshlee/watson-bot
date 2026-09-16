/**
 * Watson AI Agent - Heatmap & Lifelog In-Place Markdown Editor Modal Controller (ADR-045, ADR-050)
 */
(function() {
    let editorInitialized = false;
    let currentEditorDate = "";
    let cachedHeatmapData = null;

    function renderMarkdownToHtml(markdown) {
        if (!markdown) return "<p><em>(작성된 내용이 없습니다)</em></p>";
        let html = markdown
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;");

        // Code blocks
        html = html.replace(/```([\w-]*)\n([\s\S]*?)```/g, (match, lang, code) => {
            return `<pre><code class="language-${lang}">${code}</code></pre>`;
        });

        // Inline code
        html = html.replace(/`([^`]+)`/g, "<code>$1</code>");

        // Headers
        html = html.replace(/^#### (.*$)/gim, "<h4>$1</h4>");
        html = html.replace(/^### (.*$)/gim, "<h3>$1</h3>");
        html = html.replace(/^## (.*$)/gim, "<h2>$1</h2>");
        html = html.replace(/^# (.*$)/gim, "<h1>$1</h1>");

        // Blockquotes
        html = html.replace(/^> (.*$)/gim, "<blockquote>$1</blockquote>");

        // Checkboxes
        html = html.replace(/^[ \t]*-[ \t]+\[[xX]\][ \t]+(.*$)/gim, '<li style="list-style:none;"><input type="checkbox" checked disabled /> $1</li>');
        html = html.replace(/^[ \t]*-[ \t]+\[ \][ \t]+(.*$)/gim, '<li style="list-style:none;"><input type="checkbox" disabled /> $1</li>');

        // Unordered lists
        html = html.replace(/^[ \t]*[\*\-][ \t]+(.*$)/gim, "<li>$1</li>");

        // Bold and Italic
        html = html.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
        html = html.replace(/\*([^*]+)\*/g, "<em>$1</em>");

        // Links
        html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');

        // Horizontal rules
        html = html.replace(/^---$/gim, "<hr />");

        // Paragraphs and breaks
        html = html.replace(/\n\n/g, "</p><p>");
        html = html.replace(/\n/g, "<br />");

        return `<p>${html}</p>`;
    }

    async function loadHeatmapData() {
        const heatmapStreakText = document.getElementById("heatmap-streak-text");
        const statStreak = document.getElementById("stat-streak");
        const statTotalDays = document.getElementById("stat-total-days");
        const statTotalTasks = document.getElementById("stat-total-tasks");
        const statRate = document.getElementById("stat-rate");

        try {
            const fetchFn = window.WatsonAPI?.fetchWithRetry || window.fetchWithRetry || fetch;
            const res = await fetchFn("/api/lifelog/heatmap?days=365");
            if (!res.ok) return;
            const resJson = await res.json();
            if (resJson.status !== "success" || !resJson.data) return;

            cachedHeatmapData = resJson.data;
            const summary = cachedHeatmapData.summary;

            // Update Header Streak Badge
            if (heatmapStreakText) {
                heatmapStreakText.innerText = `연속: ${summary.current_streak}일`;
            }

            // Update Modal Stats Bar
            if (statStreak) statStreak.innerText = summary.current_streak;
            if (statTotalDays) statTotalDays.innerText = summary.total_days_logged;
            if (statTotalTasks) statTotalTasks.innerText = summary.total_completed_tasks;
            if (statRate) statRate.innerText = summary.completion_rate;

            // Render Heatmap Grid
            renderHeatmapGrid(cachedHeatmapData.days);
        } catch (err) {
            console.error("Failed to load heatmap data:", err);
        }
    }

    function renderHeatmapGrid(days) {
        const heatmapGrid = document.getElementById("heatmap-grid");
        const heatmapTooltip = document.getElementById("heatmap-tooltip");
        if (!heatmapGrid || !days || days.length === 0) return;
        heatmapGrid.innerHTML = "";

        const daysOfWeek = ["일", "월", "화", "수", "목", "금", "토"];

        days.forEach(dayInfo => {
            const cell = document.createElement("div");
            cell.className = `heatmap-cell level-${dayInfo.level}`;
            cell.dataset.date = dayInfo.date;

            // Hover tooltip
            cell.addEventListener("mouseenter", (e) => {
                if (!heatmapTooltip) return;
                const d = new Date(dayInfo.date);
                const dayName = daysOfWeek[d.getDay()];
                let text = `<strong>${dayInfo.date} (${dayName})</strong><br>`;
                if (dayInfo.exists) {
                    text += `글자 수: ${dayInfo.char_count.toLocaleString()}자<br>완료 태스크: ${dayInfo.completed_tasks}개`;
                } else {
                    text += `<span style="color:var(--text-secondary)">기록 없음</span>`;
                }
                heatmapTooltip.innerHTML = text;
                heatmapTooltip.style.opacity = "1";

                const rect = cell.getBoundingClientRect();
                heatmapTooltip.style.left = `${rect.left + window.scrollX + rect.width / 2}px`;
                heatmapTooltip.style.top = `${rect.top + window.scrollY - 10}px`;
            });

            cell.addEventListener("mouseleave", () => {
                if (heatmapTooltip) heatmapTooltip.style.opacity = "0";
            });

            // Click cell to jump to date
            cell.addEventListener("click", () => {
                openEditorModal(dayInfo.date);
            });

            heatmapGrid.appendChild(cell);
        });
    }

    async function loadLifelogFile(dateStr) {
        const editorDatePicker = document.getElementById("editor-date-picker");
        const editorFileStatus = document.getElementById("editor-file-status");
        const editorFilePath = document.getElementById("editor-file-path");
        const editorTextarea = document.getElementById("editor-textarea");
        const editorPreviewContent = document.getElementById("editor-preview-content");

        if (!dateStr) {
            const getDateFn = window.WatsonDate?.getKSTDateString || window.getKSTDateString || (() => new Date().toISOString().split("T")[0]);
            dateStr = getDateFn();
        }
        currentEditorDate = dateStr;
        if (editorDatePicker) editorDatePicker.value = dateStr;

        if (editorFileStatus) editorFileStatus.innerText = "불러오는 중...";
        if (editorTextarea) editorTextarea.value = "파일을 불러오는 중입니다...";
        if (editorPreviewContent) editorPreviewContent.innerHTML = "<p><em>로딩 중...</em></p>";

        try {
            const fetchFn = window.WatsonAPI?.fetchWithRetry || window.fetchWithRetry || fetch;
            const res = await fetchFn(`/api/lifelog/file?date=${dateStr}`);
            if (res.ok) {
                const resJson = await res.json();
                if (resJson.status === "success") {
                    const data = resJson.data;
                    if (editorFileStatus) {
                        editorFileStatus.innerText = data.exists ? `기존 파일 (${data.char_count}자)` : "신규 파일 생성 모드";
                        editorFileStatus.className = `editor-status-badge ${data.exists ? 'exists' : 'new'}`;
                    }
                    if (editorFilePath) editorFilePath.innerText = data.relative_path || `logs/daily/${dateStr}.md`;
                    if (editorTextarea) editorTextarea.value = data.content || "";
                    if (editorPreviewContent) editorPreviewContent.innerHTML = renderMarkdownToHtml(data.content || "");
                }
            } else {
                if (editorFileStatus) editorFileStatus.innerText = "로딩 실패";
                alert("일일 로그 파일을 불러오지 못했습니다.");
            }
        } catch (e) {
            console.error(e);
            if (editorFileStatus) editorFileStatus.innerText = "네트워크 오류";
        }
    }

    async function saveLifelogFile() {
        const editorTextarea = document.getElementById("editor-textarea");
        const editorCommitMsg = document.getElementById("editor-commit-msg");
        const editorAutoPushChk = document.getElementById("editor-auto-push-chk");
        const btnSaveEditor = document.getElementById("btn-save-editor");

        if (!currentEditorDate) return;
        const content = editorTextarea?.value || "";
        const commitMsg = editorCommitMsg?.value.trim() || `docs(lifelog): update ${currentEditorDate} daily log via web editor`;
        const autoPush = editorAutoPushChk?.checked ?? true;

        if (btnSaveEditor) {
            btnSaveEditor.disabled = true;
            btnSaveEditor.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> 저장 중...';
        }

        try {
            const fetchFn = window.WatsonAPI?.fetchWithRetry || window.fetchWithRetry || fetch;
            const res = await fetchFn("/api/lifelog/save", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    date: currentEditorDate,
                    content: content,
                    commit_message: commitMsg,
                    auto_push: autoPush
                })
            });

            if (res.ok) {
                const resJson = await res.json();
                if (resJson.status === "success") {
                    alert(`✅ ${currentEditorDate} 일일 로그가 저장되었습니다!\nGit 커밋: ${commitMsg}${autoPush ? ' (원격 푸시 완료)' : ''}`);
                    await loadLifelogFile(currentEditorDate);
                    await loadHeatmapData();
                } else {
                    alert(`저장 실패: ${resJson.detail || "알 수 없는 오류"}`);
                }
            } else {
                const errData = await res.json();
                alert(`저장 실패: ${errData.detail || "서버 오류"}`);
            }
        } catch (err) {
            console.error(err);
            alert("저장 중 서버 연결 오류가 발생했습니다.");
        } finally {
            if (btnSaveEditor) {
                btnSaveEditor.disabled = false;
                btnSaveEditor.innerHTML = '<i class="fa-solid fa-floppy-disk"></i> 저장 및 Git 커밋';
            }
        }
    }

    function openEditorModal(targetDate = null) {
        const editorModal = document.getElementById("lifelog-editor-modal");
        if (!editorModal) return;
        editorModal.classList.remove("hidden");
        const getDateFn = window.WatsonDate?.getKSTDateString || window.getKSTDateString || (() => new Date().toISOString().split("T")[0]);
        const dateToLoad = targetDate || currentEditorDate || getDateFn();
        loadLifelogFile(dateToLoad);
        loadHeatmapData();
    }

    function closeEditorModal() {
        const editorModal = document.getElementById("lifelog-editor-modal");
        if (editorModal) editorModal.classList.add("hidden");
    }

    function changeDateByOffset(offsetDays) {
        if (!currentEditorDate) {
            const getDateFn = window.WatsonDate?.getKSTDateString || window.getKSTDateString || (() => new Date().toISOString().split("T")[0]);
            currentEditorDate = getDateFn();
        }
        const [y, m, d] = currentEditorDate.split("-").map(Number);
        const dateObj = new Date(Date.UTC(y, m - 1, d));
        dateObj.setUTCDate(dateObj.getUTCDate() + offsetDays);

        const newYear = dateObj.getUTCFullYear();
        const newMonth = String(dateObj.getUTCMonth() + 1).padStart(2, "0");
        const newDay = String(dateObj.getUTCDate()).padStart(2, "0");
        const newDateStr = `${newYear}-${newMonth}-${newDay}`;

        loadLifelogFile(newDateStr);
    }

    function initEditorModal() {
        if (editorInitialized) return;
        editorInitialized = true;

        const heatmapBadge = document.getElementById("heatmap-badge");
        const openEditorHeaderBtn = document.getElementById("open-editor-header-btn");
        const btnOpenEditor = document.getElementById("btn-open-editor");
        const editorModal = document.getElementById("lifelog-editor-modal");
        const closeEditorModalBtn = document.getElementById("close-editor-modal-btn");
        const btnCloseEditor = document.getElementById("btn-close-editor");

        const btnEditorPrevDay = document.getElementById("btn-editor-prev-day");
        const btnEditorNextDay = document.getElementById("btn-editor-next-day");
        const btnEditorToday = document.getElementById("btn-editor-today");
        const editorDatePicker = document.getElementById("editor-date-picker");

        const tabEditorWrite = document.getElementById("tab-editor-write");
        const tabEditorPreview = document.getElementById("tab-editor-preview");
        const editorWorkspace = document.getElementById("editor-workspace");
        const editorTextarea = document.getElementById("editor-textarea");
        const editorPreviewContent = document.getElementById("editor-preview-content");
        const btnSaveEditor = document.getElementById("btn-save-editor");

        heatmapBadge?.addEventListener("click", () => openEditorModal());
        openEditorHeaderBtn?.addEventListener("click", (e) => {
            e.stopPropagation();
            openEditorModal();
        });
        btnOpenEditor?.addEventListener("click", () => openEditorModal());

        closeEditorModalBtn?.addEventListener("click", closeEditorModal);
        btnCloseEditor?.addEventListener("click", closeEditorModal);

        editorModal?.addEventListener("click", (e) => {
            if (e.target === editorModal) closeEditorModal();
        });

        btnEditorPrevDay?.addEventListener("click", () => changeDateByOffset(-1));
        btnEditorNextDay?.addEventListener("click", () => changeDateByOffset(1));
        btnEditorToday?.addEventListener("click", () => {
            const getDateFn = window.WatsonDate?.getKSTDateString || window.getKSTDateString || (() => new Date().toISOString().split("T")[0]);
            loadLifelogFile(getDateFn());
        });

        editorDatePicker?.addEventListener("change", (e) => {
            if (e.target.value) loadLifelogFile(e.target.value);
        });

        // Split view tabs for mobile
        tabEditorWrite?.addEventListener("click", () => {
            tabEditorWrite.classList.add("active");
            tabEditorPreview?.classList.remove("active");
            editorWorkspace?.classList.remove("show-preview-only");
            editorWorkspace?.classList.add("show-write-only");
        });

        tabEditorPreview?.addEventListener("click", () => {
            tabEditorPreview.classList.add("active");
            tabEditorWrite?.classList.remove("active");
            editorWorkspace?.classList.remove("show-write-only");
            editorWorkspace?.classList.add("show-preview-only");
            if (editorPreviewContent && editorTextarea) {
                editorPreviewContent.innerHTML = renderMarkdownToHtml(editorTextarea.value);
            }
        });

        // Live preview sync
        editorTextarea?.addEventListener("input", () => {
            if (editorPreviewContent) {
                editorPreviewContent.innerHTML = renderMarkdownToHtml(editorTextarea.value);
            }
        });

        btnSaveEditor?.addEventListener("click", saveLifelogFile);

        loadHeatmapData();
    }

    window.WatsonEditor = {
        initEditorModal,
        openEditorModal,
        closeEditorModal,
        loadLifelogFile,
        loadHeatmapData,
        renderMarkdownToHtml
    };
})();
