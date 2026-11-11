document.addEventListener("DOMContentLoaded", async () => {
    const list = document.getElementById("agentsPageList");
    const message = document.getElementById("agentsMessage");
    const load = async () => {
        try {
            const data = await window.AUVRION_GRID.apiRequest("/api/agents/");
            list.innerHTML = data.agents.map(agent => `
                <article class="agent-card">
                    <div class="agent-icon">✧</div>
                    <h3>${escapeHtml(agent.name)}</h3>
                    <p>${escapeHtml(agent.description)}</p>
                    <strong>$${Number(agent.price).toFixed(2)} <small>/ task</small></strong>
                    <span class="agent-availability">${agent.is_active ? "AVAILABLE" : "UNAVAILABLE"}</span>
                </article>`).join("");
            message.textContent = "";
        } catch (error) { message.textContent = error.message; message.classList.add("error"); }
    };
    function escapeHtml(v) {
        return String(v).replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
    }
    document.getElementById("agentsRefresh").addEventListener("click", load);
    await load();
});
