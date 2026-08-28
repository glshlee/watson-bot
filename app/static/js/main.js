document.addEventListener("DOMContentLoaded", () => {
    const sendBtn = document.getElementById("send-btn");
    const quickInput = document.getElementById("quick-input");
    const categorySelect = document.getElementById("category-select");
    const resultToast = document.getElementById("result-toast");
    const toastMsg = document.getElementById("toast-msg");

    sendBtn.addEventListener("click", async () => {
        const text = quickInput.value.trim();
        if (!text) {
            alert("내용을 입력해주세요!");
            return;
        }

        sendBtn.disabled = true;
        sendBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> 저장 중...';

        try {
            const response = await fetch("/api/log", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    session_id: "web_default_session",
                    message: text,
                    category: categorySelect.value
                })
            });

            const data = await response.json();
            if (response.ok) {
                toastMsg.innerText = `성공: ${data.filepath} 저장 및 Git 처리 완료`;
                resultToast.classList.remove("hidden");
                quickInput.value = "";
                setTimeout(() => resultToast.classList.add("hidden"), 5000);
            } else {
                alert(`오류: ${data.detail || '저장 실패'}`);
            }
        } catch (err) {
            console.error(err);
            alert("서버 통신 중 오류가 발생했습니다.");
        } finally {
            sendBtn.disabled = false;
            sendBtn.innerHTML = '<i class="fa-solid fa-arrow-up-from-bracket"></i> 로그 저장 및 깃 푸시';
        }
    });
});
