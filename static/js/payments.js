(() => {
    const payButton = document.getElementById("payWithPaypalButton");
    const amountElement = document.getElementById("paymentAmount");
    const messageElement = document.getElementById("paymentMessage");
    const noticeTitle = document.getElementById("paymentNoticeTitle");
    const noticeText = document.getElementById("paymentNoticeText");
    const returnData = document.getElementById("paypalReturnData");
    const refreshButton = document.getElementById("refreshPaymentsButton");
    const loadMessage = document.getElementById("paymentsLoadMessage");

    if (!payButton || !window.AUVRION_GRID) {
        console.error("AUVRION payment dependencies are unavailable.");
        return;
    }

    const apiRequest = window.AUVRION_GRID.apiRequest;
    const STORAGE_KEY = "auvrion_approved_plan";
    let approvedPlan = null;
    let processing = false;
    let paymentsGridApi = null;

    function showMessage(message, isError = false) {
        messageElement.textContent = message;
        messageElement.style.color = isError ? "#ff7777" : "";
    }

    function setNotice(title, message) {
        noticeTitle.textContent = title;
        noticeText.textContent = message;
    }

    function formatAmount(amount, currency = "USD") {
        const value = Number(amount);
        if (!Number.isFinite(value)) return `${currency} ${amount}`;
        try {
            return new Intl.NumberFormat("en-US", {style: "currency", currency}).format(value);
        } catch {
            return `${currency} ${value.toFixed(2)}`;
        }
    }

    function loadApprovedPlan() {
        try {
            const stored = sessionStorage.getItem(STORAGE_KEY);
            if (!stored) return null;
            const plan = JSON.parse(stored);
            return plan && plan.id && plan.total_amount && plan.currency ? plan : null;
        } catch (error) {
            console.error("Could not read approved plan:", error);
            return null;
        }
    }

    function displayPlan(plan) {
        approvedPlan = plan;
        amountElement.textContent = formatAmount(plan.total_amount, plan.currency);
        payButton.disabled = false;
        payButton.textContent = "Continue with PayPal";
        setNotice("Plan ready for checkout", "Your approved plan is ready. Continue to PayPal Sandbox to authorize the payment.");
    }

    function statusRenderer(params) {
        const value = String(params.value || "Pending");
        const span = document.createElement("span");
        span.className = `status-pill ${value.toLowerCase()}`;
        span.textContent = value;
        return span;
    }

    function setupPaymentsGrid() {
        const element = document.getElementById("paymentsGrid");
        if (!element || !window.agGrid) {
            loadMessage.textContent = "AG Grid did not load. Check your internet connection and refresh.";
            return;
        }
        paymentsGridApi = agGrid.createGrid(element, {
            columnDefs: [
                {headerName: "Date", field: "created_at", minWidth: 175, flex: 1,
                    valueFormatter: p => p.value ? new Date(p.value).toLocaleString() : "—"},
                {headerName: "Plan ID", field: "plan_id", minWidth: 150, flex: 1},
                {headerName: "Amount", field: "amount", minWidth: 120,
                    valueFormatter: p => formatAmount(p.value, p.data.currency)},
                {headerName: "Status", field: "status", minWidth: 125, cellRenderer: statusRenderer},
                {headerName: "PayPal Order ID", field: "order_id", minWidth: 190, flex: 1},
                {headerName: "Capture ID", field: "capture_id", minWidth: 190, flex: 1}
            ],
            rowData: [],
            defaultColDef: {sortable: true, filter: true, resizable: true},
            animateRows: true,
            pagination: true,
            paginationPageSize: 8,
            getRowId: params => params.data.plan_id
        });
    }

    async function loadPaymentHistory() {
        if (!paymentsGridApi) return;
        loadMessage.textContent = "Loading transaction history...";
        try {
            const data = await apiRequest("/api/payments/");
            const summary = data.summary || {};
            document.getElementById("totalRevenue").textContent = formatAmount(summary.total_revenue || "0", "USD");
            document.getElementById("completedCount").textContent = summary.completed_count ?? 0;
            document.getElementById("pendingCount").textContent = summary.pending_count ?? 0;
            document.getElementById("failedCount").textContent = summary.failed_count ?? 0;
            paymentsGridApi.setGridOption("rowData", data.transactions || []);
            document.getElementById("transactionCount").textContent = `${(data.transactions || []).length} records`;
            loadMessage.textContent = "";
        } catch (error) {
            loadMessage.textContent = error.message;
            loadMessage.style.color = "#ff7777";
        }
    }

    async function createOrder() {
        if (!approvedPlan || processing) return;
        processing = true;
        payButton.disabled = true;
        payButton.textContent = "Connecting to PayPal...";
        showMessage("Creating your PayPal Sandbox order...");
        try {
            const result = await apiRequest("/api/payments/create-order/", {
                method: "POST",
                body: JSON.stringify({plan_id: approvedPlan.id})
            });
            if (!result.approval_url) throw new Error("PayPal did not provide an approval URL.");
            showMessage("PayPal order created. Redirecting...");
            window.location.assign(result.approval_url);
        } catch (error) {
            showMessage(error.message, true);
            payButton.disabled = false;
            payButton.textContent = "Retry PayPal checkout";
            processing = false;
        }
    }

    async function captureReturnedOrder(orderId) {
        if (!orderId || processing) return;
        processing = true;
        payButton.disabled = true;
        payButton.textContent = "Verifying payment...";
        setNotice("Payment approval received", "AUVRION is asking PayPal to capture and verify the payment.");
        showMessage("Verifying the PayPal transaction...");
        try {
            const result = await apiRequest("/api/payments/capture/", {
                method: "POST",
                body: JSON.stringify({order_id: orderId})
            });
            sessionStorage.removeItem(STORAGE_KEY);
            amountElement.textContent = formatAmount(result.amount, result.currency);
            setNotice("Payment completed", "PayPal confirmed the capture. Your execution plan is now marked as paid.");
            showMessage(result.message);
            payButton.textContent = "Payment completed";
            payButton.disabled = true;
            await loadPaymentHistory();
        } catch (error) {
            setNotice("Payment verification incomplete", "PayPal has not yet confirmed a completed capture. Do not assume the plan is paid.");
            showMessage(error.message, true);
            payButton.textContent = "Retry verification";
            payButton.disabled = false;
        } finally {
            processing = false;
        }
    }

    payButton.addEventListener("click", createOrder);
    refreshButton?.addEventListener("click", loadPaymentHistory);
    const returnedOrderId = returnData?.dataset.orderId || "";
    const wasCancelled = returnData?.dataset.cancelled === "true";
    setupPaymentsGrid();

    if (returnedOrderId) {
        captureReturnedOrder(returnedOrderId);
    } else {
        if (wasCancelled) {
            setNotice("Checkout cancelled", "No completed payment was recorded. You can return to checkout when ready.");
            showMessage("PayPal checkout was cancelled.");
        }
        const plan = loadApprovedPlan();
        if (plan) displayPlan(plan);
        else if (!wasCancelled) {
            setNotice("No approved plan found", "Generate and approve a plan in AI Planner before starting checkout.");
            showMessage("There is no approved plan waiting for payment.");
        }
    }
    loadPaymentHistory();
})();
