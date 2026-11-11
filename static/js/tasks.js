document.addEventListener("DOMContentLoaded", async () => {
    const gridElement = document.getElementById("tasksGrid");
    const api = window.AUVRION_GRID.createGrid(gridElement);
    const form = document.getElementById("executionForm");
    const planSelect = document.getElementById("executionPlan");
    const fileInput = document.getElementById("executionCsv");
    const executeButton = document.getElementById("executeButton");
    const message = document.getElementById("executionMessage");
    const csrf = document.querySelector("#csrf-form input[name=csrfmiddlewaretoken]")?.value;

    const refreshTasks = async () => {
        try {
            const tasks = await window.AUVRION_GRID.loadTasks(api);
            document.getElementById("tasksCount").textContent = `${tasks.length} records`;
        } catch (error) { message.textContent = error.message; }
    };

    document.getElementById("tasksSearch").addEventListener("input", event => {
        api.setGridOption("quickFilterText", event.target.value);
    });
    document.getElementById("tasksRefresh").addEventListener("click", refreshTasks);

    async function loadExecutionOptions() {
        const response = await fetch("/api/executions/");
        const data = await response.json();
        planSelect.replaceChildren();
        const placeholder = document.createElement("option");
        placeholder.value = "";
        placeholder.textContent = data.paid_plans.length ? "Select a paid plan" : "No paid plans available";
        planSelect.append(placeholder);
        data.paid_plans.forEach(plan => {
            const option = document.createElement("option");
            option.value = plan.id;
            option.textContent = `${plan.id.slice(0, 8)}… — ${plan.currency} ${plan.amount}`;
            planSelect.append(option);
        });
    }

    function showResults(run) {
        const section = document.getElementById("executionResults");
        section.hidden = false;
        document.getElementById("resultFilename").textContent = run.filename || "Dataset execution";
        document.getElementById("resultStatus").textContent = run.status;
        const summary = document.getElementById("analysisSummary");
        summary.replaceChildren();
        const values = [
            ["Rows analysed", run.analysis?.row_count ?? "—"],
            ["Columns", run.analysis?.column_count ?? "—"],
            ["Missing values", Object.values(run.analysis?.missing_values || {}).reduce((a, b) => a + b, 0)]
        ];
        values.forEach(([label, value]) => {
            const card = document.createElement("div"); card.className = "execution-metric";
            const title = document.createElement("span"); title.textContent = label;
            const number = document.createElement("strong"); number.textContent = value;
            card.append(title, number); summary.append(card);
        });
        const charts = document.getElementById("chartResults"); charts.replaceChildren();
        (run.artifacts || []).forEach(item => {
            const link = document.createElement("a"); link.href = item.url; link.target = "_blank"; link.rel = "noopener";
            const img = document.createElement("img"); img.src = item.url; img.alt = item.name;
            const caption = document.createElement("span"); caption.textContent = item.name;
            link.append(img, caption); charts.append(link);
        });
        document.getElementById("executionReport").textContent = run.report || "No report was generated.";
        section.scrollIntoView({ behavior: "smooth", block: "start" });
    }

    form.addEventListener("submit", async event => {
        event.preventDefault();
        if (!planSelect.value || !fileInput.files.length) {
            message.textContent = "Select a paid plan and a CSV file."; return;
        }
        const file = fileInput.files[0];
        if (file.size > 5 * 1024 * 1024) { message.textContent = "CSV files must be 5 MB or smaller."; return; }
        const body = new FormData(); body.append("plan_id", planSelect.value); body.append("dataset", file);
        executeButton.disabled = true; executeButton.textContent = "Agents working…";
        message.textContent = "Validating dataset and running the agent workflow. Keep this page open.";
        try {
            const response = await fetch("/api/executions/run/", { method: "POST", headers: csrf ? {"X-CSRFToken": csrf} : {}, body });
            const data = await response.json();
            if (!response.ok) throw new Error(data.error || "Execution failed.");
            message.textContent = data.message;
            showResults(data.run);
            await refreshTasks();
            await loadExecutionOptions();
        } catch (error) { message.textContent = error.message; }
        finally { executeButton.disabled = false; executeButton.textContent = "Run agents"; }
    });

    await Promise.all([refreshTasks(), loadExecutionOptions()]);
});
