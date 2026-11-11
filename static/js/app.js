document.addEventListener("DOMContentLoaded", async () => {
    const gridElement = document.getElementById("taskGrid");
    if (!gridElement || !window.AUVRION_GRID) return;

    const {apiRequest, createGrid, loadTasks, loadAgents} = window.AUVRION_GRID;
    const gridApi = createGrid(gridElement);

    async function refresh() {
        try {
            const [tasks, agents] = await Promise.all([
                loadTasks(gridApi),
                loadAgents()
            ]);
            document.getElementById("totalTasks").textContent = tasks.length;
            document.getElementById("runningTasks").textContent = tasks.filter(t => t.status === "Running").length;
            document.getElementById("completedTasks").textContent = tasks.filter(t => t.status === "Completed").length;
            document.getElementById("totalAgents").textContent = agents.filter(a => a.is_active).length;
            document.getElementById("recordCount").textContent = `${tasks.length} records`;

            const agentList = document.getElementById("agentList");
            agentList.innerHTML = agents.filter(a => a.is_active).map(a => `
                <article class="agent-card">
                    <div class="agent-icon">✧</div>
                    <h3>${escapeHtml(a.name)}</h3>
                    <p>${escapeHtml(a.description)}</p>
                    <strong>$${Number(a.price).toFixed(2)} <small>/ task</small></strong>
                </article>`).join("");

            const select = document.getElementById("taskAgent");
            const selected = select.value;
            select.innerHTML = `<option value="">Unassigned</option>` +
                agents.filter(a => a.is_active).map(a => `<option value="${a.id}">${escapeHtml(a.name)} — $${Number(a.price).toFixed(2)}</option>`).join("");
            select.value = selected;
        } catch (error) {
            showMessage("formMessage", error.message, true);
        }
    }

    function escapeHtml(value) {
        return String(value).replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
    }

    function showMessage(id, message, error=false) {
        const el = document.getElementById(id);
        if (el) {
            el.textContent = message;
            el.classList.toggle("error", error);
        }
    }

    document.getElementById("taskForm").addEventListener("submit", async event => {
        event.preventDefault();
        const button = event.currentTarget.querySelector("button[type=submit]");
        button.disabled = true;
        try {
            await apiRequest("/api/tasks/create/", {
                method:"POST",
                body:JSON.stringify({
                    title:document.getElementById("taskTitle").value,
                    agent_id:document.getElementById("taskAgent").value || null,
                    priority:document.getElementById("taskPriority").value
                })
            });
            event.currentTarget.reset();
            showMessage("formMessage", "Task created successfully.");
            await refresh();
        } catch (error) {
            showMessage("formMessage", error.message, true);
        } finally {
            button.disabled = false;
        }
    });

    document.getElementById("quickSearch").addEventListener("input", event => {
        gridApi.setGridOption("quickFilterText", event.target.value);
    });
    document.getElementById("refreshButton").addEventListener("click", refresh);
    await refresh();
});
