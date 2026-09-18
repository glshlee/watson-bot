/**
 * ==========================================================================
 * Watson Command Palette Controller (ADR-054 / Phase 1-2)
 * 슬랙/ChatGPT 스타일 [/] 팝오버 명령어 팔레트 및 실시간 필터링 엔진
 * ==========================================================================
 */

(function () {
    "use strict";

    let isPaletteOpen = false;
    let selectedIndex = -1;
    let visibleItems = [];
    let triggerCommandCallback = null;

    function initCommandPalette(options = {}) {
        triggerCommandCallback = options.onTriggerCommand || null;

        const btnCommandPalette = document.getElementById("btn-command-palette");
        const palette = document.getElementById("command-palette");
        const chatInput = document.getElementById("chat-input");
        const paletteBody = document.getElementById("palette-body");
        const paletteEmpty = document.getElementById("palette-empty");
        const paletteCount = document.getElementById("palette-count");

        if (!palette || !chatInput) return;

        const allItems = Array.from(palette.querySelectorAll(".palette-item"));
        const allGroups = Array.from(palette.querySelectorAll(".palette-group"));

        function updateVisibleItems(query = "") {
            const cleanQuery = query.toLowerCase().trim();
            visibleItems = [];

            allItems.forEach(item => {
                const cmd = (item.dataset.cmd || "").toLowerCase();
                const name = (item.querySelector(".item-name")?.textContent || "").toLowerCase();
                const desc = (item.querySelector(".item-desc")?.textContent || "").toLowerCase();

                const isMatch = !cleanQuery || cmd.includes(cleanQuery) || name.includes(cleanQuery) || desc.includes(cleanQuery);

                if (isMatch) {
                    item.style.display = "flex";
                    visibleItems.push(item);
                } else {
                    item.style.display = "none";
                }
            });

            // Toggle group headers based on item visibility
            allGroups.forEach(group => {
                const hasVisibleChildren = Array.from(group.querySelectorAll(".palette-item")).some(
                    it => it.style.display !== "none"
                );
                group.style.display = hasVisibleChildren ? "block" : "none";
            });

            // Empty state toggle
            if (paletteEmpty) {
                if (visibleItems.length === 0) {
                    paletteEmpty.classList.remove("hidden");
                } else {
                    paletteEmpty.classList.add("hidden");
                }
            }

            if (paletteCount) {
                paletteCount.textContent = `${visibleItems.length}개`;
            }

            // Reset selection to first item
            if (visibleItems.length > 0) {
                setSelectedIndex(0);
            } else {
                setSelectedIndex(-1);
            }
        }

        function setSelectedIndex(index) {
            allItems.forEach(it => it.classList.remove("selected"));

            if (index >= 0 && index < visibleItems.length) {
                selectedIndex = index;
                const activeItem = visibleItems[selectedIndex];
                activeItem.classList.add("selected");
                activeItem.scrollIntoView({ block: "nearest", behavior: "smooth" });
            } else {
                selectedIndex = -1;
            }
        }

        const paletteBackdrop = document.getElementById("command-palette-backdrop");
        const btnClosePalette = document.getElementById("btn-close-palette");

        function openPalette(initialQuery = "") {
            palette.classList.remove("hidden");
            paletteBackdrop?.classList.remove("hidden");
            btnCommandPalette?.classList.add("active");
            isPaletteOpen = true;
            updateVisibleItems(initialQuery);
        }

        function closePalette() {
            palette.classList.add("hidden");
            paletteBackdrop?.classList.add("hidden");
            btnCommandPalette?.classList.remove("active");
            isPaletteOpen = false;
            setSelectedIndex(-1);
        }

        function togglePalette() {
            if (isPaletteOpen) {
                closePalette();
            } else {
                let query = "";
                if (chatInput.value.startsWith("/")) {
                    query = chatInput.value.slice(1);
                }
                openPalette(query);
                chatInput.focus();
            }
        }

        function executeItem(item) {
            if (!item) return;

            const action = item.dataset.action;
            const cmd = item.dataset.cmd;

            closePalette();

            if (action) {
                switch (action) {
                    case "modal-schedule":
                        window.WatsonSchedule?.openScheduleModal?.();
                        break;
                    case "modal-commute":
                        window.WatsonCommute?.openCommuteModal?.();
                        break;
                    case "modal-editor":
                        window.WatsonEditor?.openEditorModal?.();
                        break;
                    case "modal-telegram":
                        window.WatsonTelegram?.openTelegramMenuModal?.();
                        break;
                    default:
                        console.warn("[Palette] Unknown action:", action);
                }
                return;
            }

            if (cmd) {
                if (cmd.endsWith(" ")) {
                    // Fill input for typing query
                    chatInput.value = cmd;
                    chatInput.focus();
                    chatInput.selectionStart = chatInput.selectionEnd = chatInput.value.length;
                } else {
                    // Direct command execution
                    chatInput.value = "";
                    if (triggerCommandCallback) {
                        triggerCommandCallback(cmd);
                    } else if (window.WatsonChat?.sendTextMessage) {
                        window.WatsonChat.sendTextMessage(cmd);
                    }
                }
            }
        }

        // Toggle button listener
        btnCommandPalette?.addEventListener("click", (e) => {
            e.stopPropagation();
            togglePalette();
        });

        // Close button listener (ADR-054 Mobile Fix)
        function handleClosePalette(e) {
            e.preventDefault();
            e.stopPropagation();
            closePalette();
        }
        btnClosePalette?.addEventListener("click", handleClosePalette);
        btnClosePalette?.addEventListener("touchstart", handleClosePalette, { passive: false });

        // Backdrop click/touch to close
        paletteBackdrop?.addEventListener("click", handleClosePalette);
        paletteBackdrop?.addEventListener("touchstart", handleClosePalette, { passive: false });

        // Item click listener
        allItems.forEach(item => {
            item.addEventListener("click", (e) => {
                e.stopPropagation();
                executeItem(item);
            });
        });

        // Keyboard & typing listeners on chatInput
        chatInput.addEventListener("input", () => {
            const val = chatInput.value;
            if (val.startsWith("/")) {
                const query = val.slice(1);
                if (!isPaletteOpen) {
                    openPalette(query);
                } else {
                    updateVisibleItems(query);
                }
            } else if (isPaletteOpen) {
                closePalette();
            }
        });

        chatInput.addEventListener("keydown", (e) => {
            if (!isPaletteOpen) {
                // Open on '/' if input is empty
                if (e.key === "/" && chatInput.value === "") {
                    // Let '/' be typed, input event will trigger openPalette
                    return;
                }
                return;
            }

            switch (e.key) {
                case "ArrowDown":
                    e.preventDefault();
                    if (visibleItems.length > 0) {
                        const next = (selectedIndex + 1) % visibleItems.length;
                        setSelectedIndex(next);
                    }
                    break;

                case "ArrowUp":
                    e.preventDefault();
                    if (visibleItems.length > 0) {
                        const prev = (selectedIndex - 1 + visibleItems.length) % visibleItems.length;
                        setSelectedIndex(prev);
                    }
                    break;

                case "Enter":
                    if (!e.shiftKey && selectedIndex >= 0 && visibleItems[selectedIndex]) {
                        e.preventDefault();
                        e.stopPropagation();
                        executeItem(visibleItems[selectedIndex]);
                    }
                    break;

                case "Escape":
                    e.preventDefault();
                    closePalette();
                    break;

                case "Tab":
                    if (selectedIndex >= 0 && visibleItems[selectedIndex]) {
                        e.preventDefault();
                        executeItem(visibleItems[selectedIndex]);
                    }
                    break;
            }
        });

        // Close on outside click or touch (mobile friendly)
        function handleOutsideInteraction(e) {
            if (isPaletteOpen && !palette.contains(e.target) && e.target !== btnCommandPalette && !btnCommandPalette?.contains(e.target)) {
                closePalette();
            }
        }
        document.addEventListener("click", handleOutsideInteraction);
        document.addEventListener("touchstart", handleOutsideInteraction, { passive: true });

        // Export public methods
        window.WatsonCommandPalette = {
            initCommandPalette,
            openPalette,
            closePalette,
            togglePalette,
            isOpen: () => isPaletteOpen
        };
    }

    // Expose namespace
    window.WatsonCommandPalette = {
        initCommandPalette
    };
})();
