/**
 * Watson AI Agent - GTD Storage Settings Modal Controller (ADR-007, ADR-050)
 */
(function() {
    let gtdInitialized = false;

    async function loadGTDStatus() {
        const gtdPathText = document.getElementById("gtd-path-display");
        const gtdStorageBadge = document.getElementById("gtd-storage-badge");
        const gtdPathInput = document.getElementById("gtd-path-input");
        const gtdModalStatus = document.getElementById("gtd-modal-status");

        try {
            const res = await fetch("/api/settings/gtd-path");
            if (res.ok) {
                const data = await res.json();
                const shortPath = data.gtd_path.split("/").slice(-2).join("/");
                if (gtdPathText) {
                    gtdPathText.innerText = `GTD: ${shortPath} ${data.is_git_repo ? '⚡Git' : '📁Local'}`;
                    gtdPathText.title = `경로: ${data.gtd_path} (${data.is_git_repo ? '독립 Git 레포지토리 연동' : '로컬 보관'})`;
                }

                if (gtdStorageBadge) {
                    if (data.is_git_repo) {
                        gtdStorageBadge.classList.add("git-active");
                    } else {
                        gtdStorageBadge.classList.remove("git-active");
                    }
                }

                if (gtdPathInput) gtdPathInput.value = data.gtd_path;
                if (gtdModalStatus) {
                    gtdModalStatus.innerHTML = `
                        <strong>현재 연동 정보:</strong><br>
                        • 전체 경로: <code>${data.gtd_path}</code><br>
                        • Git 버전 관리: ${data.is_git_repo ? '<span style="color:#34d399">✅ 활성화 (독립 커밋/푸시)</span>' : '<span style="color:#94a3b8">📁 로컬 파일 전용 (Git 미연동)</span>'}<br>
                        • 격리 모드: ${data.is_external ? '<span style="color:#60a5fa">외부 분리 저장소 (External)</span>' : '봇 소스코드 기본'}<br>
                        • 구조 체계: <code>${data.structure_type}</code> (Inbox: ${data.has_inbox ? '있음' : '없음'}, Daily Logs: ${data.has_daily_logs ? '있음' : '없음'})
                    `;
                }
            }
        } catch (e) {
            console.error("Failed to load GTD status", e);
            if (gtdPathText) gtdPathText.innerText = "GTD: 경로 오류";
        }
    }

    function openGTDModal() {
        const gtdModal = document.getElementById("gtd-modal");
        if (gtdModal) gtdModal.classList.remove("hidden");
    }

    function closeGTDModal() {
        const gtdModal = document.getElementById("gtd-modal");
        if (gtdModal) gtdModal.classList.add("hidden");
    }

    function initGTDModal() {
        if (gtdInitialized) return;
        gtdInitialized = true;

        const gtdModal = document.getElementById("gtd-modal");
        const changeGtdBtn = document.getElementById("change-gtd-btn");
        const gtdStorageBadge = document.getElementById("gtd-storage-badge");
        const closeGtdModalBtn = document.getElementById("close-gtd-modal-btn");
        const cancelGtdBtn = document.getElementById("cancel-gtd-btn");
        const saveGtdBtn = document.getElementById("save-gtd-btn");
        const gtdPathInput = document.getElementById("gtd-path-input");

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
            if (e.target === gtdModal) closeGTDModal();
        });

        saveGtdBtn?.addEventListener("click", async () => {
            const newPath = gtdPathInput?.value.trim();
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

        loadGTDStatus();
    }

    window.WatsonGTD = {
        initGTDModal,
        openGTDModal,
        closeGTDModal,
        loadGTDStatus
    };
})();
