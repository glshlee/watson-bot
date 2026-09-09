document.addEventListener("DOMContentLoaded", () => {
    async function loadHubStatus() {
        try {
            const res = await fetch("/api/hub/status");
            if (res.ok) {
                const data = await res.json();
                const totalAgents = document.getElementById("total-agents-val");
                const watsonSessions = document.getElementById("watson-sessions-val");
                const devBranch = document.getElementById("dev-branch-val");

                if (totalAgents) totalAgents.innerText = `${data.total_agents}개`;
                
                const watson = data.agents.find(a => a.id === "watson");
                if (watson && watsonSessions) {
                    watsonSessions.innerText = `${watson.session_count}개`;
                }

                const dev = data.agents.find(a => a.id === "dev");
                if (dev && devBranch) {
                    devBranch.innerText = dev.branch || "main";
                }
            }
        } catch (e) {
            console.error("Failed to load hub status", e);
        }

        try {
            const gtdRes = await fetch("/api/settings/gtd-path");
            if (gtdRes.ok) {
                const gtdData = await gtdRes.json();
                const gtdStatus = document.getElementById("gtd-status-val");
                if (gtdStatus && gtdData.gtd_path) {
                    const parts = gtdData.gtd_path.split("/");
                    gtdStatus.innerText = parts[parts.length - 1] || "life_log";
                    gtdStatus.title = gtdData.gtd_path;
                }
            }
        } catch (e) {
            console.error("Failed to load GTD path", e);
        }
    }

    // Enable direct card clicking for fast navigation
    document.querySelectorAll(".agent-portal-card.watson-card").forEach(card => {
        card.addEventListener("click", (e) => {
            if (!e.target.closest("a, button")) {
                window.location.href = "/watson";
            }
        });
    });

    document.querySelectorAll(".agent-portal-card.dev-card").forEach(card => {
        card.addEventListener("click", (e) => {
            if (!e.target.closest("a, button")) {
                window.location.href = "/dev";
            }
        });
    });

    loadHubStatus();
});
