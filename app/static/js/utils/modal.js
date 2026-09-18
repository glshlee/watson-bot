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

    window.WatsonModal = {
        openModal,
        closeModal,
        setupModalDismiss,
        escapeHtml
    };
    window.escapeHtml = escapeHtml;
})();
