/**
 * Web Autonomous Coding Studio Modal Controller (ADR-058)
 * DevBot 웹 콘솔에서 워크스페이스 소스코드 탐색, 브라우저 인플레이스 코드 편집,
 * 실시간 Unified Diff 미리보기, 안전 패치(자동 백업) 및 롤백을 전담합니다.
 */
(function() {
    let currentFilePath = "app/main.py";
    let originalContent = "";
    let fileTreeCache = [];
    let isStudioOpen = false;

    // Elements
    let modal, closeBtn, filenameEl, langBadge, sizeBadge, linesBadge, dirtyBadge;
    let tabEditor, tabDiff, viewEditor, viewDiff;
    let editorTextarea, diffContainer, diffStatsEl, statusMsgEl;
    let fileSearchInput, fileTreeContainer, btnRefreshTree, btnReset;
    let btnRollback, btnPreviewDiff, btnApplyPatch, btnRunTest;

    function initDomElements() {
        modal = document.getElementById("code-studio-modal");
        closeBtn = document.getElementById("close-studio-modal-btn");
        filenameEl = document.getElementById("studio-active-filename");
        langBadge = document.getElementById("studio-lang-badge");
        sizeBadge = document.getElementById("studio-size-badge");
        linesBadge = document.getElementById("studio-lines-badge");
        dirtyBadge = document.getElementById("studio-dirty-badge");

        tabEditor = document.getElementById("tab-studio-editor");
        tabDiff = document.getElementById("tab-studio-diff");
        viewEditor = document.getElementById("studio-view-editor");
        viewDiff = document.getElementById("studio-view-diff");

        editorTextarea = document.getElementById("studio-editor-textarea");
        diffContainer = document.getElementById("studio-diff-container");
        diffStatsEl = document.getElementById("studio-diff-stats");
        statusMsgEl = document.getElementById("studio-status-msg");

        fileSearchInput = document.getElementById("studio-file-search");
        fileTreeContainer = document.getElementById("studio-file-tree");
        btnRefreshTree = document.getElementById("btn-studio-refresh-tree");
        btnReset = document.getElementById("btn-studio-reset");

        btnRollback = document.getElementById("btn-studio-rollback");
        btnPreviewDiff = document.getElementById("btn-studio-preview-diff");
        btnApplyPatch = document.getElementById("btn-studio-apply-patch");
        btnRunTest = document.getElementById("btn-studio-run-test");
    }

    function switchTab(tabName) {
        if (tabName === "editor") {
            tabEditor?.classList.add("active");
            tabDiff?.classList.remove("active");
            viewEditor?.classList.add("active");
            viewDiff?.classList.remove("active");
        } else if (tabName === "diff") {
            tabEditor?.classList.remove("active");
            tabDiff?.classList.add("active");
            viewEditor?.classList.remove("active");
            viewDiff?.classList.add("active");
            previewDiff();
        }
    }

    async function loadFileTree(filterKeyword = "") {
        if (!fileTreeContainer) return;
        try {
            if (fileTreeCache.length === 0) {
                fileTreeContainer.innerHTML = '<div class="studio-loading"><i class="fa-solid fa-spinner fa-spin"></i> 소스 파일 목록 탐색 중...</div>';
                const res = await fetch("/api/dev/code/tree");
                if (res.ok) {
                    const data = await res.json();
                    fileTreeCache = data.files || [];
                }
            }

            const keyword = filterKeyword.trim().toLowerCase();
            const filtered = keyword
                ? fileTreeCache.filter(f => f.path.toLowerCase().includes(keyword) || f.name.toLowerCase().includes(keyword))
                : fileTreeCache;

            if (filtered.length === 0) {
                fileTreeContainer.innerHTML = '<div class="studio-empty-tree">일치하는 파일이 없습니다.</div>';
                return;
            }

            let html = "";
            filtered.forEach(f => {
                const isActive = f.path === currentFilePath ? "active" : "";
                const iconClass = getFileIcon(f.language, f.name);
                html += `
                    <div class="studio-tree-item ${isActive}" data-file-path="${f.path}" title="${f.path} (${f.lines}줄, ${f.size}B)">
                        <span class="tree-file-icon ${f.language}"><i class="${iconClass}"></i></span>
                        <div class="tree-file-info">
                            <span class="tree-file-name">${f.name}</span>
                            <span class="tree-file-path">${f.path}</span>
                        </div>
                        <span class="tree-file-lines">${f.lines}줄</span>
                    </div>
                `;
            });
            fileTreeContainer.innerHTML = html;
        } catch (e) {
            console.error("Failed to load file tree:", e);
            fileTreeContainer.innerHTML = '<div class="studio-empty-tree error">파일 목록을 불러올 수 없습니다.</div>';
        }
    }

    function getFileIcon(lang, filename) {
        if (lang === "python") return "fa-brands fa-python";
        if (lang === "javascript") return "fa-brands fa-js";
        if (lang === "html") return "fa-brands fa-html5";
        if (lang === "css") return "fa-brands fa-css3-alt";
        if (lang === "markdown") return "fa-brands fa-markdown";
        if (lang === "bash" || filename.endsWith(".sh")) return "fa-solid fa-terminal";
        if (lang === "json") return "fa-solid fa-code";
        return "fa-solid fa-file-code";
    }

    async function loadFile(filepath) {
        if (!filepath) return;
        currentFilePath = filepath;
        setStatus("파일 불러오는 중...");

        try {
            const res = await fetch(`/api/dev/code/file?filepath=${encodeURIComponent(filepath)}`);
            if (res.ok) {
                const data = await res.json();
                originalContent = data.content || "";
                if (editorTextarea) {
                    editorTextarea.value = originalContent;
                }
                if (filenameEl) filenameEl.innerText = data.path || filepath;
                if (langBadge) {
                    langBadge.innerText = data.language || "text";
                    langBadge.className = `studio-badge lang ${data.language || 'text'}`;
                }
                if (sizeBadge) sizeBadge.innerText = `${(data.size || 0).toLocaleString()} B`;
                if (linesBadge) linesBadge.innerText = `${data.total_lines || 0}줄`;
                if (dirtyBadge) dirtyBadge.classList.add("hidden");

                // Highlight active item in tree
                document.querySelectorAll(".studio-tree-item").forEach(el => {
                    if (el.dataset.filePath === filepath) el.classList.add("active");
                    else el.classList.remove("active");
                });

                setStatus(`준비됨 (${data.total_lines || 0}줄)`);
                switchTab("editor");
            } else {
                const err = await res.json();
                setStatus(`⚠️ 오류: ${err.detail || "파일을 열 수 없습니다."}`, true);
            }
        } catch (e) {
            console.error("Failed to load file content:", e);
            setStatus("⚠️ 파일 읽기 중 네트워크 오류", true);
        }
    }

    async function previewDiff() {
        if (!editorTextarea || !diffContainer) return;
        const currentContent = editorTextarea.value;
        if (currentContent === originalContent) {
            diffContainer.innerHTML = '<div class="diff-notice">현재 수정된 내용이 없습니다. 원본과 동일합니다.</div>';
            if (diffStatsEl) diffStatsEl.innerText = "🟢 +0줄 / 🔴 -0줄 (동일함)";
            return;
        }

        setStatus("Diff 계산 중...");
        try {
            const res = await fetch("/api/dev/code/patch", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    filepath: currentFilePath,
                    new_content: currentContent,
                    dry_run: true
                })
            });
            if (res.ok) {
                const data = await res.json();
                renderColorizedDiff(data.diff || "", data.lines_added || 0, data.lines_removed || 0);
                setStatus("Diff 프리뷰 생성 완료");
            } else {
                const err = await res.json();
                diffContainer.innerHTML = `<div class="diff-notice error">${err.detail || "Diff 생성 실패"}</div>`;
            }
        } catch (e) {
            console.error("Failed to preview diff:", e);
            setStatus("Diff 생성 중 오류 발생", true);
        }
    }

    function renderColorizedDiff(diffText, added, removed) {
        if (diffStatsEl) {
            diffStatsEl.innerText = `🟢 +${added}줄 / 🔴 -${removed}줄`;
        }
        if (!diffText.trim()) {
            diffContainer.innerHTML = '<div class="diff-notice">변경 사항이 없습니다.</div>';
            return;
        }

        const lines = diffText.split("\n");
        let html = "";
        lines.forEach(line => {
            const escaped = line.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
            if (line.startsWith("+++") || line.startsWith("---")) {
                html += `<div class="diff-line diff-file-header">${escaped}</div>`;
            } else if (line.startsWith("@@")) {
                html += `<div class="diff-line diff-hunk">${escaped}</div>`;
            } else if (line.startsWith("+")) {
                html += `<div class="diff-line diff-add">${escaped}</div>`;
            } else if (line.startsWith("-")) {
                html += `<div class="diff-line diff-del">${escaped}</div>`;
            } else {
                html += `<div class="diff-line diff-ctx">${escaped}</div>`;
            }
        });
        diffContainer.innerHTML = html;
    }

    async function applyPatch() {
        if (!editorTextarea) return;
        const currentContent = editorTextarea.value;
        if (currentContent === originalContent) {
            alert("수정된 변경 사항이 없습니다.");
            return;
        }

        if (btnApplyPatch) {
            btnApplyPatch.disabled = true;
            btnApplyPatch.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> 패치 적용 중...';
        }
        setStatus("디스크 자동 백업 및 패치 적용 중...");

        try {
            const res = await fetch("/api/dev/code/patch", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    filepath: currentFilePath,
                    new_content: currentContent,
                    dry_run: false
                })
            });

            if (res.ok) {
                const data = await res.json();
                originalContent = currentContent;
                if (dirtyBadge) dirtyBadge.classList.add("hidden");
                setStatus(`✨ 패치 성공! (백업: ${data.backup_id || '생성됨'})`);

                // Toast notification
                showStudioToast(`✅ ${currentFilePath} 파일이 안전하게 저장되었습니다!`);

                // Also notify DevBot Chat if available
                if (typeof window.appendDevChatMessage === "function") {
                    window.appendDevChatMessage(
                        "assistant",
                        `### 💻 웹 자율 코딩 스튜디오 패치 적용 완료\n\n` +
                        `* **대상 파일**: \`${currentFilePath}\`\n` +
                        `* **자동 백업 ID**: \`${data.backup_id}\`\n\n` +
                        `변경 사항이 안전하게 반영되었습니다. 단위 테스트(\`/test\`)나 린트(\`/lint\`)로 검증해 보세요! 🚀`
                    );
                }
            } else {
                const err = await res.json();
                alert(`패치 적용 실패: ${err.detail || "알 수 없는 오류"}`);
                setStatus(`⚠️ 패치 실패: ${err.detail}`, true);
            }
        } catch (e) {
            console.error("Failed to apply patch:", e);
            setStatus("패치 적용 중 네트워크 오류", true);
        } finally {
            if (btnApplyPatch) {
                btnApplyPatch.disabled = false;
                btnApplyPatch.innerHTML = '<i class="fa-solid fa-floppy-disk"></i> <span>패치 적용 (Save & Patch)</span>';
            }
        }
    }

    async function rollbackFile() {
        if (!confirm(`정말로 '${currentFilePath}' 파일을 가장 최근 백업 시점으로 롤백 복원하시겠습니까?`)) {
            return;
        }

        setStatus("백업 시점으로 롤백 복원 중...");
        try {
            const res = await fetch("/api/dev/code/rollback", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ filepath: currentFilePath })
            });

            if (res.ok) {
                const data = await res.json();
                await loadFile(currentFilePath);
                setStatus(`🔄 롤백 완료 (${data.restored_from || '복원됨'})`);
                showStudioToast(`🔄 ${currentFilePath} 파일이 백업 시점으로 성공적으로 복원되었습니다.`);
            } else {
                const err = await res.json();
                alert(`롤백 실패: ${err.detail || "사용 가능한 백업이 없습니다."}`);
                setStatus(`⚠️ 롤백 실패: ${err.detail}`, true);
            }
        } catch (e) {
            console.error("Failed to rollback:", e);
            setStatus("롤백 중 네트워크 오류", true);
        }
    }

    function setStatus(msg, isError = false) {
        if (!statusMsgEl) return;
        statusMsgEl.innerText = msg;
        statusMsgEl.className = `studio-status ${isError ? 'error' : ''}`;
    }

    function showStudioToast(msg) {
        const toast = document.createElement("div");
        toast.className = "studio-toast-banner";
        toast.innerHTML = `<i class="fa-solid fa-circle-check"></i> ${msg}`;
        document.body.appendChild(toast);
        setTimeout(() => toast.classList.add("show"), 10);
        setTimeout(() => {
            toast.classList.remove("show");
            setTimeout(() => toast.remove(), 400);
        }, 3000);
    }

    function openStudio(filepath = null) {
        if (!modal) initDomElements();
        if (!modal) return;

        modal.classList.remove("hidden");
        document.body.classList.add("modal-open");
        isStudioOpen = true;

        loadFileTree();
        const target = filepath || currentFilePath || "app/main.py";
        loadFile(target);
    }

    function closeStudio() {
        if (!modal) return;
        modal.classList.add("hidden");
        document.body.classList.remove("modal-open");
        isStudioOpen = false;
    }

    function bindEvents() {
        initDomElements();

        closeBtn?.addEventListener("click", closeStudio);
        modal?.addEventListener("click", (e) => {
            if (e.target === modal) closeStudio();
        });

        // Tab Switching
        tabEditor?.addEventListener("click", () => switchTab("editor"));
        tabDiff?.addEventListener("click", () => switchTab("diff"));
        btnPreviewDiff?.addEventListener("click", () => switchTab("diff"));

        // File Search Filter
        fileSearchInput?.addEventListener("input", (e) => {
            loadFileTree(e.target.value);
        });

        btnRefreshTree?.addEventListener("click", () => {
            fileTreeCache = [];
            loadFileTree(fileSearchInput?.value || "");
        });

        // Click Tree Item
        fileTreeContainer?.addEventListener("click", (e) => {
            const item = e.target.closest(".studio-tree-item");
            if (!item) return;
            const path = item.dataset.filePath;
            if (path && path !== currentFilePath) {
                if (editorTextarea && editorTextarea.value !== originalContent) {
                    if (!confirm("저장되지 않은 변경 사항이 있습니다. 다른 파일을 여시겠습니까?")) {
                        return;
                    }
                }
                loadFile(path);
            }
        });

        // Editor Input & Dirty Badge
        editorTextarea?.addEventListener("input", () => {
            const isDirty = editorTextarea.value !== originalContent;
            if (dirtyBadge) {
                if (isDirty) dirtyBadge.classList.remove("hidden");
                else dirtyBadge.classList.add("hidden");
            }
        });

        // Tab key handling: Indent 4 spaces
        editorTextarea?.addEventListener("keydown", (e) => {
            if (e.key === "Tab") {
                e.preventDefault();
                const start = editorTextarea.selectionStart;
                const end = editorTextarea.selectionEnd;
                editorTextarea.value = editorTextarea.value.substring(0, start) + "    " + editorTextarea.value.substring(end);
                editorTextarea.selectionStart = editorTextarea.selectionEnd = start + 4;
                editorTextarea.dispatchEvent(new Event("input"));
            } else if ((e.ctrlKey || e.metaKey) && e.key === "s") {
                e.preventDefault();
                applyPatch();
            }
        });

        // Reset to original
        btnReset?.addEventListener("click", () => {
            if (editorTextarea) {
                editorTextarea.value = originalContent;
                if (dirtyBadge) dirtyBadge.classList.add("hidden");
                setStatus("원본 소스코드로 복원되었습니다.");
            }
        });

        // Actions
        btnApplyPatch?.addEventListener("click", applyPatch);
        btnRollback?.addEventListener("click", rollbackFile);

        btnRunTest?.addEventListener("click", () => {
            closeStudio();
            const devInput = document.getElementById("dev-chat-input");
            const devSendBtn = document.getElementById("dev-send-btn");
            if (devInput && devSendBtn) {
                devInput.value = "/test";
                devSendBtn.click();
            }
        });

        document.getElementById("btn-studio-refresh-diff")?.addEventListener("click", previewDiff);

        // Global ESC
        document.addEventListener("keydown", (e) => {
            if (e.key === "Escape" && isStudioOpen) {
                closeStudio();
            }
        });
    }

    // Initialize on DOM ready
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", bindEvents);
    } else {
        bindEvents();
    }

    // Expose Global Controller
    window.WatsonCodeStudio = {
        openStudio,
        closeStudio,
        loadFile,
        applyPatch,
        rollbackFile,
        previewDiff
    };
})();
