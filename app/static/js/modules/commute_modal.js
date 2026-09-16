/**
 * Watson AI Agent - Commute & Weather Settings Modal Controller (ADR-030, ADR-034, ADR-037, ADR-038, ADR-050)
 */
(function() {
    let commuteInitialized = false;

    async function loadCommuteSettings() {
        const commuteLocationInput = document.getElementById("commute-location-input");
        const commuteStationInput = document.getElementById("commute-station-input");
        const commuteGridX = document.getElementById("commute-grid-x");
        const commuteGridY = document.getElementById("commute-grid-y");
        const commuteStopName = document.getElementById("commute-stop-name");
        const commuteStopId = document.getElementById("commute-stop-id");
        const commuteRouteName = document.getElementById("commute-route-name");
        const commuteCityCode = document.getElementById("commute-city-code");
        const commuteSendTime = document.getElementById("commute-send-time");
        const commuteEnabled = document.getElementById("commute-enabled");
        const commuteWeekdaysOnly = document.getElementById("commute-weekdays-only");
        const commuteApiKey = document.getElementById("commute-api-key");
        const commuteMockFallback = document.getElementById("commute-mock-fallback");
        const commuteStatusText = document.getElementById("commute-status-text");

        try {
            const fetchFn = window.WatsonAPI?.fetchWithRetry || window.fetchWithRetry || fetch;
            const res = await fetchFn("/api/settings/commute");
            if (res.ok) {
                const json = await res.json();
                const cfg = json.data || {};

                if (commuteLocationInput) commuteLocationInput.value = cfg.location_name || "";
                if (commuteStationInput) commuteStationInput.value = cfg.air_station_name || "";
                if (commuteGridX) commuteGridX.value = cfg.grid_x || 61;
                if (commuteGridY) commuteGridY.value = cfg.grid_y || 125;
                if (commuteStopName) commuteStopName.value = cfg.bus_stop_name || "";
                if (commuteStopId) commuteStopId.value = cfg.bus_stop_id || "";
                if (commuteRouteName) commuteRouteName.value = cfg.bus_route_name || "";
                if (commuteCityCode) commuteCityCode.value = cfg.city_code || "11";
                if (commuteSendTime) commuteSendTime.value = cfg.send_time || "07:30";
                if (commuteEnabled) commuteEnabled.checked = cfg.enabled !== false;
                if (commuteWeekdaysOnly) commuteWeekdaysOnly.checked = cfg.weekdays_only !== false;
                if (commuteApiKey) commuteApiKey.value = cfg.public_data_api_key || "";
                if (commuteMockFallback) commuteMockFallback.checked = cfg.use_mock_fallback !== false;

                if (commuteStatusText) {
                    const statusStr = cfg.enabled ? `출근: ${cfg.send_time || '07:30'}` : '출근 브리핑: 꺼짐';
                    commuteStatusText.textContent = statusStr;
                }
            }
        } catch (e) {
            console.debug("Failed to load commute settings:", e);
        }
    }

    function openCommuteModal() {
        const commuteModal = document.getElementById("commute-modal");
        if (!commuteModal) return;
        commuteModal.classList.remove("hidden");
        loadCommuteSettings();
    }

    function closeCommuteModal() {
        const commuteModal = document.getElementById("commute-modal");
        const commutePreviewSection = document.getElementById("commute-preview-section");
        if (!commuteModal) return;
        commuteModal.classList.add("hidden");
        if (commutePreviewSection) commutePreviewSection.classList.add("hidden");
    }

    function initCommuteModal() {
        if (commuteInitialized) return;
        commuteInitialized = true;

        const commuteSettingsBadge = document.getElementById("commute-settings-badge");
        const changeCommuteBtn = document.getElementById("change-commute-btn");
        const btnCommuteView = document.getElementById("btn-commute-view");
        const commuteModal = document.getElementById("commute-modal");
        const closeCommuteModalBtn = document.getElementById("close-commute-modal-btn");
        const cancelCommuteBtn = document.getElementById("cancel-commute-btn");
        const saveCommuteBtn = document.getElementById("save-commute-btn");
        const btnCommutePreview = document.getElementById("btn-commute-preview");

        const commuteLocationInput = document.getElementById("commute-location-input");
        const commuteStationInput = document.getElementById("commute-station-input");
        const commuteGridX = document.getElementById("commute-grid-x");
        const commuteGridY = document.getElementById("commute-grid-y");
        const commuteStopName = document.getElementById("commute-stop-name");
        const commuteStopId = document.getElementById("commute-stop-id");
        const commuteRouteName = document.getElementById("commute-route-name");
        const commuteCityCode = document.getElementById("commute-city-code");
        const commuteSendTime = document.getElementById("commute-send-time");
        const commuteEnabled = document.getElementById("commute-enabled");
        const commuteWeekdaysOnly = document.getElementById("commute-weekdays-only");
        const commuteApiKey = document.getElementById("commute-api-key");
        const commuteMockFallback = document.getElementById("commute-mock-fallback");

        const commutePreviewSection = document.getElementById("commute-preview-section");
        const commutePreviewContent = document.getElementById("commute-preview-content");

        commuteSettingsBadge?.addEventListener("click", openCommuteModal);
        changeCommuteBtn?.addEventListener("click", (e) => {
            e.stopPropagation();
            openCommuteModal();
        });
        btnCommuteView?.addEventListener("click", openCommuteModal);
        closeCommuteModalBtn?.addEventListener("click", closeCommuteModal);
        cancelCommuteBtn?.addEventListener("click", closeCommuteModal);

        const btnResolveLocation = document.getElementById("btn-resolve-location");
        async function handleAutoResolveLocation() {
            const query = commuteLocationInput?.value.trim();
            if (!query) {
                alert("동네/지역 명칭을 입력해 주세요 (예: 서울 성동구 금호동, 판교동, 상암동)");
                return;
            }

            if (btnResolveLocation) {
                btnResolveLocation.disabled = true;
                btnResolveLocation.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';
            }

            try {
                const res = await fetch("/api/settings/commute/resolve-location", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ query })
                });
                const data = await res.json();
                if (res.ok && data.success && data.data) {
                    const r = data.data;
                    if (commuteLocationInput) commuteLocationInput.value = r.location_name;
                    if (commuteGridX) commuteGridX.value = r.grid_x;
                    if (commuteGridY) commuteGridY.value = r.grid_y;
                    if (commuteStationInput) commuteStationInput.value = r.air_station_name;
                    if (commuteCityCode && r.city_code) commuteCityCode.value = r.city_code;
                    console.log(`[GeoService] Resolved: ${r.location_name} (X:${r.grid_x}, Y:${r.grid_y})`);
                }
            } catch (err) {
                console.error("Failed to auto-resolve location:", err);
            } finally {
                if (btnResolveLocation) {
                    btnResolveLocation.disabled = false;
                    btnResolveLocation.innerHTML = '<i class="fa-solid fa-wand-magic-sparkles"></i> 자동 찾기';
                }
            }
        }
        btnResolveLocation?.addEventListener("click", handleAutoResolveLocation);

        const btnResolveBusStop = document.getElementById("btn-resolve-bus-stop");
        const commuteStopHint = document.getElementById("commute-stop-hint");

        async function handleAutoResolveBusStop() {
            const stopId = commuteStopId?.value.trim();
            if (!stopId) {
                alert("정류소 번호(ARS-ID)를 입력해 주세요 (예: 04158, 23284)");
                return;
            }

            if (btnResolveBusStop) {
                btnResolveBusStop.disabled = true;
                btnResolveBusStop.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> 조회 중';
            }

            try {
                const res = await fetch("/api/settings/commute/resolve-bus-stop", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        bus_stop_id: stopId,
                        city_code: commuteCityCode?.value || "11"
                    })
                });
                const data = await res.json();
                if (res.ok && data.success && data.data) {
                    const r = data.data;
                    if (commuteStopName && r.stop_name && !r.stop_name.startsWith("정류소(")) {
                        commuteStopName.value = r.stop_name;
                        if (commuteStopHint) {
                            const extra = r.direction ? ` (${r.direction})` : "";
                            commuteStopHint.innerHTML = `✅ <strong>${r.stop_name}</strong>${extra} 매핑 완료`;
                        }
                    }
                }
            } catch (err) {
                console.error("Failed to auto-resolve bus stop:", err);
            } finally {
                if (btnResolveBusStop) {
                    btnResolveBusStop.disabled = false;
                    btnResolveBusStop.innerHTML = '<i class="fa-solid fa-magnifying-glass"></i> 정류소 조회';
                }
            }
        }

        btnResolveBusStop?.addEventListener("click", handleAutoResolveBusStop);
        commuteStopId?.addEventListener("change", () => {
            if (commuteStopId.value.trim().length >= 4) handleAutoResolveBusStop();
        });
        commuteStopId?.addEventListener("blur", () => {
            if (commuteStopId.value.trim().length >= 4 && (!commuteStopName.value.trim() || commuteStopName.value.trim() === "역삼역")) {
                handleAutoResolveBusStop();
            }
        });

        commuteModal?.addEventListener("click", (e) => {
            if (e.target === commuteModal) closeCommuteModal();
        });

        saveCommuteBtn?.addEventListener("click", async () => {
            let stopNameVal = commuteStopName?.value.trim() || "";
            const stopIdVal = commuteStopId?.value.trim() || "";
            if (stopIdVal && (!stopNameVal || stopNameVal === "역삼역")) {
                stopNameVal = ""; // 백엔드에서 정류소 번호 기반으로 자동 역조회하도록 위임
            }

            const payload = {
                location_name: commuteLocationInput?.value.trim() || "우리 동네",
                air_station_name: commuteStationInput?.value.trim() || "",
                grid_x: parseInt(commuteGridX?.value, 10) || 61,
                grid_y: parseInt(commuteGridY?.value, 10) || 125,
                bus_stop_name: stopNameVal,
                bus_stop_id: stopIdVal,
                bus_route_name: commuteRouteName?.value.trim() || "",
                city_code: commuteCityCode?.value || "11",
                send_time: commuteSendTime?.value || "07:30",
                enabled: commuteEnabled?.checked ?? true,
                weekdays_only: commuteWeekdaysOnly?.checked ?? true,
                public_data_api_key: commuteApiKey?.value.trim() || "",
                use_mock_fallback: commuteMockFallback?.checked ?? true,
            };

            saveCommuteBtn.disabled = true;
            saveCommuteBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> 저장 중...';

            try {
                const res = await fetch("/api/settings/commute", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(payload)
                });
                const result = await res.json();
                if (res.ok) {
                    const busLabel = payload.bus_route_name ? `${payload.bus_route_name}번` : '전체 노선';
                    const stopLabel = payload.bus_stop_name || (payload.bus_stop_id ? `정류소(${payload.bus_stop_id})` : '정류소');
                    alert("✅ 출근길 맞춤형 브리핑 설정이 안전하게 저장되었습니다!\n\n" +
                          `📍 지역: ${payload.location_name}\n` +
                          `🚌 탑승: ${stopLabel} (${busLabel})\n` +
                          `⏰ 알림: ${payload.send_time} (${payload.weekdays_only ? '평일' : '매일'})`);
                    await loadCommuteSettings();
                    closeCommuteModal();
                } else {
                    alert(`⚠️ 저장 실패: ${result.detail || "설정 값을 확인해 주세요."}`);
                }
            } catch (e) {
                console.error(e);
                alert("⚠️ 서버 통신 중 오류가 발생했습니다.");
            } finally {
                saveCommuteBtn.disabled = false;
                saveCommuteBtn.innerHTML = '<i class="fa-solid fa-floppy-disk"></i> 설정 저장';
            }
        });

        btnCommutePreview?.addEventListener("click", async () => {
            if (!commutePreviewSection || !commutePreviewContent) return;

            btnCommutePreview.disabled = true;
            btnCommutePreview.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> 생성 중...';

            const customPayload = {
                location_name: commuteLocationInput?.value.trim() || "우리 동네",
                air_station_name: commuteStationInput?.value.trim() || "",
                grid_x: parseInt(commuteGridX?.value, 10) || 61,
                grid_y: parseInt(commuteGridY?.value, 10) || 125,
                bus_stop_name: commuteStopName?.value.trim() || "",
                bus_stop_id: commuteStopId?.value.trim() || "",
                bus_route_name: commuteRouteName?.value.trim() || "",
                city_code: commuteCityCode?.value || "11",
                send_time: commuteSendTime?.value || "07:30",
                enabled: commuteEnabled?.checked ?? true,
                weekdays_only: commuteWeekdaysOnly?.checked ?? true,
                public_data_api_key: commuteApiKey?.value.trim() || "",
                use_mock_fallback: commuteMockFallback?.checked ?? true,
            };

            try {
                const res = await fetch("/api/settings/commute/preview", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ config: customPayload })
                });
                if (res.ok) {
                    const data = await res.json();
                    commutePreviewContent.textContent = data.markdown || "미리보기 생성 실패";
                    commutePreviewSection.classList.remove("hidden");
                } else {
                    commutePreviewContent.textContent = "미리보기 요청 실패 (" + res.status + ")";
                    commutePreviewSection.classList.remove("hidden");
                }
            } catch (e) {
                commutePreviewContent.textContent = "통신 오류: " + e.message;
                commutePreviewSection.classList.remove("hidden");
            } finally {
                btnCommutePreview.disabled = false;
                btnCommutePreview.innerHTML = '<i class="fa-solid fa-magnifying-glass"></i> 실시간 미리보기';
            }
        });

        loadCommuteSettings();
    }

    window.WatsonCommute = {
        initCommuteModal,
        openCommuteModal,
        closeCommuteModal,
        loadCommuteSettings
    };
})();
