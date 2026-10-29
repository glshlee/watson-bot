/**
 * Watson AI Agent - Modal Helper Utilities (ADR-048, ADR-050 / Phase 2)
 */
(function() {
    function openModal(modalEl) {
        if (!modalEl) return;
        modalEl.classList.remove("hidden");
    }

    function closeModal(modalEl) {
        if (!modalEl) return;
        modalEl.classList.add("hidden");
    }

    function setupModalDismiss(modalEl, closeBtnEl, cancelBtnEl = null, onClose = null) {
        if (!modalEl) return;
        const doClose = (e) => {
            if (e) {
                e.preventDefault();
                e.stopPropagation();
            }
            closeModal(modalEl);
            if (typeof onClose === "function") onClose();
        };

        if (closeBtnEl) {
            closeBtnEl.addEventListener("click", doClose);
            closeBtnEl.addEventListener("touchstart", doClose, { passive: false });
        }
        if (cancelBtnEl) {
            cancelBtnEl.addEventListener("click", doClose);
            cancelBtnEl.addEventListener("touchstart", doClose, { passive: false });
        }

        modalEl.addEventListener("click", (e) => {
            if (e.target === modalEl) doClose(e);
        });
        modalEl.addEventListener("touchstart", (e) => {
            if (e.target === modalEl) doClose(e);
        }, { passive: false });

        document.addEventListener("keydown", (e) => {
            if (e.key === "Escape" && !modalEl.classList.contains("hidden")) {
                doClose(e);
            }
        });
    }

    function escapeHtml(str) {
        if (!str) return "";
        return String(str)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    function initHeaderSettingsDropdown() {
        const wrapper = document.getElementById("header-settings-wrapper");
        const triggerBtn = document.getElementById("btn-header-settings");
        const dropdown = document.getElementById("header-settings-dropdown");
        if (!wrapper || !triggerBtn || !dropdown) return;

        const closeDropdown = () => {
            dropdown.classList.add("hidden");
            triggerBtn.classList.remove("active");
        };

        triggerBtn.addEventListener("click", (e) => {
            e.preventDefault();
            e.stopPropagation();
            const isHidden = dropdown.classList.contains("hidden");
            if (isHidden) {
                dropdown.classList.remove("hidden");
                triggerBtn.classList.add("active");
            } else {
                closeDropdown();
            }
        });

        dropdown.addEventListener("click", (e) => {
            const item = e.target.closest(".settings-dropdown-item");
            if (item) {
                setTimeout(closeDropdown, 50);
            }
        });

        document.addEventListener("click", (e) => {
            if (!wrapper.contains(e.target)) {
                closeDropdown();
            }
        });

        document.addEventListener("keydown", (e) => {
            if (e.key === "Escape") {
                closeDropdown();
            }
        });
    }

    /**
     * 인라인 마크다운(볼드, 이탤릭, 인라인 코드, 링크, 마감일/우선순위 태그)을 리치 HTML로 변환합니다. (ADR-065)
     */
    function formatInlineMarkdown(escapedText) {
        if (!escapedText) return "";

        // 1. 인라인 코드 (`code`) 보호를 위해 플레이스홀더로 먼저 치환
        const inlineCodes = [];
        let out = escapedText.replace(/`([^`\n]+)`/g, (match, code) => {
            const idx = inlineCodes.length;
            inlineCodes.push(`<code class="md-inline-code">${code}</code>`);
            return `@@MD_INLINE_CODE_${idx}@@`;
        });

        // 2. 마크다운 링크 [label](url)
        out = out.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+|\/[^\s)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer" class="md-link">$1</a>');

        // 3. 굵은 글씨 (**bold**) 및 취소선 (~~strike~~)
        out = out.replace(/\*\*([^*]+)\*\*/g, '<strong class="md-bold">$1</strong>');
        out = out.replace(/~~([^~]+)~~/g, '<del class="md-del">$1</del>');

        // 4. 기울임꼴 (*italic*)
        out = out.replace(/(^|[^*])\*([^*\n]+)\*(?!\*)/g, '$1<em class="md-italic">$2</em>');

        // 5. GTD 마감일 배지 (~YYYY-MM-DD 또는 @due(YYYY-MM-DD))
        out = out.replace(/(~20\d{2}-\d{2}-\d{2}|@due\(20\d{2}-\d{2}-\d{2}\))/g, '<span class="md-due-pill"><i class="fa-regular fa-calendar"></i> $1</span>');

        // 6. 인라인 코드 복원
        out = out.replace(/@@MD_INLINE_CODE_(\d+)@@/g, (m, idx) => inlineCodes[Number(idx)] || m);

        return out;
    }

    /**
     * 마크다운 원문을 구조화된 리치 HTML 뷰어로 변환합니다. (ADR-065)
     * - 코드 블록, 헤더(h1~h4), 인용구, 테이블, GTD 체크리스트(- [ ], - [x]), 타임스탬프([HH:MM]) 배지, 일반 목록 지원
     * - 블록 요소 사이의 불필요한 <br> 중첩을 제거하여 깔끔한 문서 간격 보장
     */
    function renderRichMarkdown(markdown) {
        if (!markdown) return '<p class="preview-placeholder">표시할 내용이 없습니다.</p>';

        const raw = String(markdown).replace(/\r\n/g, "\n");

        // 1. 코드 블록 (```lang ... ```) 분리 보호
        const codeBlocks = [];
        const textWithoutCodeBlocks = raw.replace(/```([a-zA-Z0-9_-]*)\n([\s\S]*?)```/g, (match, lang, code) => {
            const idx = codeBlocks.length;
            const langLabel = lang ? `<div class="md-code-header"><span class="md-code-lang">${escapeHtml(lang)}</span></div>` : "";
            codeBlocks.push(
                `<div class="md-code-block-wrapper">${langLabel}<pre class="md-code-block"><code>${escapeHtml(code.replace(/\n$/, ""))}</code></pre></div>`
            );
            return `\n@@MD_CODE_BLOCK_${idx}@@\n`;
        });

        const lines = textWithoutCodeBlocks.split("\n");
        const htmlParts = [];
        let listType = null; // 'ul' | 'task' | null
        let inBlockquote = false;
        let quoteLines = [];
        let inTable = false;
        let tableRows = [];

        const closeOpenBlocks = () => {
            if (listType === "ul") {
                htmlParts.push("</ul>");
                listType = null;
            } else if (listType === "task") {
                htmlParts.push("</ul>");
                listType = null;
            }
            if (inBlockquote) {
                htmlParts.push(`<blockquote class="md-blockquote">${quoteLines.join("<br>")}</blockquote>`);
                inBlockquote = false;
                quoteLines = [];
            }
            if (inTable) {
                htmlParts.push(renderMarkdownTable(tableRows));
                inTable = false;
                tableRows = [];
            }
        };

        for (let i = 0; i < lines.length; i++) {
            const line = lines[i];
            const trimmed = line.trim();

            // 빈 줄 처리
            if (!trimmed) {
                closeOpenBlocks();
                continue;
            }

            // 코드 블록 플레이스홀더
            const codeMatch = trimmed.match(/^@@MD_CODE_BLOCK_(\d+)@@$/);
            if (codeMatch) {
                closeOpenBlocks();
                htmlParts.push(codeBlocks[Number(codeMatch[1])] || "");
                continue;
            }

            // 수평선 (---, ***)
            if (/^(-{3,}|\*{3,})$/.test(trimmed)) {
                closeOpenBlocks();
                htmlParts.push('<hr class="md-hr" />');
                continue;
            }

            // 마크다운 테이블 행 (| ... |)
            if (/^\|(.+)\|$/.test(trimmed)) {
                if (listType || inBlockquote) closeOpenBlocks();
                inTable = true;
                tableRows.push(trimmed);
                continue;
            } else if (inTable) {
                closeOpenBlocks();
            }

            // 헤더 (# ~ ####)
            const headingMatch = line.match(/^(#{1,4})\s+(.+)$/);
            if (headingMatch) {
                closeOpenBlocks();
                const level = headingMatch[1].length;
                const content = formatInlineMarkdown(escapeHtml(headingMatch[2].trim()));
                htmlParts.push(`<h${level} class="md-heading md-h${level}">${content}</h${level}>`);
                continue;
            }

            // 인용구 (> ...)
            const quoteMatch = line.match(/^\s*>\s?(.*)$/);
            if (quoteMatch) {
                if (listType || inTable) closeOpenBlocks();
                inBlockquote = true;
                quoteLines.push(formatInlineMarkdown(escapeHtml(quoteMatch[1])));
                continue;
            } else if (inBlockquote) {
                closeOpenBlocks();
            }

            // GTD 체크리스트 (- [ ] 또는 - [x] 또는 * [ ])
            const taskMatch = line.match(/^\s*[-*•]\s+\[([ xX])\]\s+(.+)$/);
            if (taskMatch) {
                if (listType !== "task") {
                    closeOpenBlocks();
                    htmlParts.push('<ul class="md-task-list">');
                    listType = "task";
                }
                const isDone = taskMatch[1].toLowerCase() === "x";
                let taskBody = escapeHtml(taskMatch[2].trim());
                // 타임스탬프 [HH:MM] 배지 추출
                taskBody = taskBody.replace(/^\[(\d{2}:\d{2})\]\s*/, '<span class="md-time-badge"><i class="fa-regular fa-clock"></i> $1</span> ');
                const formattedBody = formatInlineMarkdown(taskBody);
                const checkIcon = isDone
                    ? '<span class="md-checkbox checked"><i class="fa-solid fa-check"></i></span>'
                    : '<span class="md-checkbox"><i class="fa-regular fa-square"></i></span>';
                htmlParts.push(
                    `<li class="md-task-item ${isDone ? "done" : "pending"}">${checkIcon}<span class="md-task-text">${formattedBody}</span></li>`
                );
                continue;
            }

            // 일반 불릿 리스트 (- ..., * ..., • ..., ▫️ ..., ▪ ...)
            const bulletMatch = line.match(/^\s*(?:[-*•]|▫️|▪️)\s+(.+)$/);
            if (bulletMatch) {
                if (listType !== "ul") {
                    closeOpenBlocks();
                    htmlParts.push('<ul class="md-list">');
                    listType = "ul";
                }
                let itemBody = escapeHtml(bulletMatch[1].trim());
                // 타임스탬프 [HH:MM] 배지 스타일링
                itemBody = itemBody.replace(/^\[(\d{2}:\d{2})\]\s*/, '<span class="md-time-badge"><i class="fa-regular fa-clock"></i> $1</span> ');
                htmlParts.push(`<li class="md-list-item">${formatInlineMarkdown(itemBody)}</li>`);
                continue;
            }

            // 번호 매기기 리스트 (1. ..., 2. ...)
            const orderedMatch = line.match(/^\s*(\d+)\.\s+(.+)$/);
            if (orderedMatch) {
                if (listType !== "ul") {
                    closeOpenBlocks();
                    htmlParts.push('<ul class="md-list md-ordered-list">');
                    listType = "ul";
                }
                const numBadge = `<span class="md-num-badge">${escapeHtml(orderedMatch[1])}.</span>`;
                const itemBody = formatInlineMarkdown(escapeHtml(orderedMatch[2].trim()));
                htmlParts.push(`<li class="md-list-item md-ordered-item">${numBadge}<span class="md-item-content">${itemBody}</span></li>`);
                continue;
            }

            // 일반 단락 (연속된 일반 줄은 하나의 단락 안에서 줄바꿈으로 묶음)
            closeOpenBlocks();
            let pBody = escapeHtml(line);
            pBody = pBody.replace(/^\[(\d{2}:\d{2})\]\s*/, '<span class="md-time-badge"><i class="fa-regular fa-clock"></i> $1</span> ');
            htmlParts.push(`<p class="md-paragraph">${formatInlineMarkdown(pBody)}</p>`);
        }

        closeOpenBlocks();
        return `<div class="md-viewer-root">${htmlParts.join("")}</div>`;
    }

    function renderMarkdownTable(rows) {
        if (!rows || rows.length === 0) return "";
        const parseCells = (row) =>
            row
                .replace(/^\||\|$/g, "")
                .split("|")
                .map((c) => c.trim());

        const headerCells = parseCells(rows[0]);
        let startIdx = 1;
        if (rows.length > 1 && /^[\s|:-]+$/.test(rows[1])) {
            startIdx = 2;
        }

        const thead = `<thead><tr>${headerCells.map((c) => `<th>${formatInlineMarkdown(escapeHtml(c))}</th>`).join("")}</tr></thead>`;
        const bodyRows = rows.slice(startIdx).map((r) => {
            const cells = parseCells(r);
            return `<tr>${cells.map((c) => `<td>${formatInlineMarkdown(escapeHtml(c))}</td>`).join("")}</tr>`;
        });
        const tbody = bodyRows.length > 0 ? `<tbody>${bodyRows.join("")}</tbody>` : "";
        return `<div class="md-table-wrapper"><table class="md-table">${thead}${tbody}</table></div>`;
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initHeaderSettingsDropdown);
    } else {
        initHeaderSettingsDropdown();
    }

    window.WatsonModal = {
        openModal,
        closeModal,
        setupModalDismiss,
        escapeHtml,
        initHeaderSettingsDropdown,
        renderRichMarkdown
    };
    window.WatsonMarkdown = {
        render: renderRichMarkdown,
        formatInline: formatInlineMarkdown
    };
    window.escapeHtml = escapeHtml;
    window.renderMarkdownToHtml = renderRichMarkdown;
})();
