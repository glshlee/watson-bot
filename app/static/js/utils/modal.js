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
        const doClose = () => {
            closeModal(modalEl);
            if (typeof onClose === "function") onClose();
        };

        if (closeBtnEl) closeBtnEl.addEventListener("click", doClose);
        if (cancelBtnEl) cancelBtnEl.addEventListener("click", doClose);

        modalEl.addEventListener("click", (e) => {
            if (e.target === modalEl) doClose();
        });

        document.addEventListener("keydown", (e) => {
            if (e.key === "Escape" && !modalEl.classList.contains("hidden")) {
                doClose();
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
