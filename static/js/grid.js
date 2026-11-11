
(() => {
    const csrf = document.querySelector("#csrf-form input[name=csrfmiddlewaretoken]")?.value;

    async function apiRequest(url, options = {}) {
        const response = await fetch(url, {
            ...options,
            headers: {
                "Content-Type": "application/json",
                ...(csrf ? {"X-CSRFToken": csrf} : {}),
                ...(options.headers || {})
            }
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "Request failed.");
        }

        return data;
    }

    const statusRenderer = params =>
        `<span class="status-pill ${String(params.value || "Queued").toLowerCase()}">${params.value || "Queued"}</span>`;

    const progressRenderer = params =>
        `<div class="progress-cell"><div class="progress-track"><span style="width:${Number(params.value) || 0}%"></span></div><small>${Number(params.value) || 0}%</small></div>`;

    const actionRenderer = params => {
        const status = params.data.status;

        if (params.data.payment_required) {
            return `<span class="muted-note">Payment required</span>`;
        }

        if (status === "Completed" || status === "Cancelled") {
            return `<span class="muted-note">No action</span>`;
        }

        return `<button class="grid-action" data-task="${params.data.id}" data-action="${status === "Queued" ? "start" : "advance"}">${status === "Queued" ? "Start" : "Advance"}</button>`;
    };

    function makeColumns() {
        return [
            {headerName:"Task", field:"title", flex:2, minWidth:220},
            {headerName:"Assigned agent", field:"agent", flex:1, minWidth:170},
            {headerName:"Priority", field:"priority", width:115},
            {headerName:"Status", field:"status", width:130, cellRenderer:statusRenderer},
            {headerName:"Progress", field:"progress", width:160, cellRenderer:progressRenderer},
            {headerName:"Budget", field:"budget", width:110, valueFormatter:p=>`$${Number(p.value || 0).toFixed(2)}`},
            {headerName:"Action", field:"id", width:110, sortable:false, filter:false, cellRenderer:actionRenderer}
        ];
    }

    function createGrid(element) {
        if (!element || !window.agGrid) {
            console.error("AG Grid failed to load.");
            return null;
        }

        const options = {
            columnDefs: makeColumns(),
            rowData: [],
            defaultColDef: {
                sortable: true,
                filter: true,
                resizable: true
            },
            animateRows: true,
            pagination: true,
            paginationPageSize: 8
        };

        const api = agGrid.createGrid(element, options);

        element.addEventListener("click", async event => {
            const button = event.target.closest("[data-task][data-action]");

            if (!button) return;

            const rowElement = button.closest(".ag-row");
            const rowIndex = Number(rowElement?.getAttribute("row-index"));
            const current = api.getDisplayedRowAtIndex(rowIndex)?.data;

            if (!current) return;

            const start = button.dataset.action === "start";
            const nextProgress = start
                ? Math.max(10, current.progress)
                : Math.min(100, current.progress + 25);

            const nextStatus = nextProgress >= 100 ? "Completed" : "Running";

            button.disabled = true;

            try {
                await apiRequest(`/api/tasks/${current.id}/update/`, {
                    method: "POST",
                    body: JSON.stringify({
                        status: nextStatus,
                        progress: nextProgress
                    })
                });

                await loadTasks(api);
            } catch (error) {
                alert(error.message);
                button.disabled = false;
            }
        });

        return api;
    }

    async function loadTasks(api) {
        if (!api) return [];

        const data = await apiRequest("/api/tasks/");
        api.setGridOption("rowData", data.tasks);

        return data.tasks;
    }

    async function loadAgents() {
        const data = await apiRequest("/api/agents/");
        return data.agents;
    }

    window.AUVRION_GRID = {
        apiRequest,
        createGrid,
        loadTasks,
        loadAgents
    };
})();
