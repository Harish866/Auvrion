
document.addEventListener("DOMContentLoaded", () => {
    const { apiRequest } = window.AUVRION_GRID || {};

    const goalInput = document.getElementById("goalInput");
    const generateButton = document.getElementById("generatePlanButton");
    const planSection = document.getElementById("planSection");

    let currentPlan = null;
    let approvedPlan = null;

    function message(id, text, error = false) {
        const el = document.getElementById(id);
        if (!el) return;

        el.textContent = text;
        el.classList.toggle("error", error);
    }

    function escapeHtml(value) {
        return String(value).replace(/[&<>"']/g, c => ({
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            '"': "&quot;",
            "'": "&#39;"
        }[c]));
    }

    function renderPlan(plan) {
        document.getElementById("planSummary").textContent = plan.summary;

        document.getElementById("planTotal").textContent =
            `${plan.currency} ${Number(plan.total_cost).toFixed(2)}`;

        document.getElementById("planTasks").innerHTML =
            plan.tasks.map((task, index) => `
                <article class="plan-task">
                    <div class="plan-number">${index + 1}</div>

                    <div class="plan-task-main">
                        <h3>${escapeHtml(task.title)}</h3>
                        <p>${escapeHtml(task.reason)}</p>

                        <div class="plan-meta">
                            <span>${escapeHtml(task.agent)}</span>
                            <span>${escapeHtml(task.priority)} priority</span>
                        </div>
                    </div>

                    <strong>$${Number(task.price).toFixed(2)}</strong>
                </article>
            `).join("");

        planSection.classList.remove("hidden");
    }

    generateButton.addEventListener("click", async () => {
        const goal = goalInput.value.trim();

        if (!goal) {
            message("plannerMessage", "Enter a goal before generating a plan.", true);
            return;
        }

        generateButton.disabled = true;
        generateButton.textContent = "Generating...";
        message("plannerMessage", "Groq is preparing your proposed plan...");

        planSection.classList.add("hidden");
        currentPlan = null;
        approvedPlan = null;

        try {
            const result = await apiRequest("/api/ai/plan/", {
                method: "POST",
                body: JSON.stringify({ goal })
            });

            currentPlan = result.plan;
            renderPlan(currentPlan);

            message("plannerMessage", "Plan generated. Review it before approval.");

        } catch (error) {
            message("plannerMessage", error.message, true);

        } finally {
            generateButton.disabled = false;
            generateButton.textContent = "Generate plan ✧";
        }
    });

    document.getElementById("rejectPlanButton").addEventListener("click", () => {
        currentPlan = null;
        approvedPlan = null;

        planSection.classList.add("hidden");

        message("plannerMessage", "Plan discarded.");
        message("approvalMessage", "");
    });

    document.getElementById("approvePlanButton").addEventListener("click", async event => {
        if (!currentPlan) return;

        const button = event.currentTarget;

        button.disabled = true;
        button.textContent = "Approving...";

        try {
            const result = await apiRequest("/api/ai/approve/", {
                method: "POST",
                body: JSON.stringify({
                    tasks: currentPlan.tasks
                })
            });

            if (!result.plan || !result.plan.id) {
                throw new Error("Approval succeeded, but the server did not return a plan ID.");
            }

            approvedPlan = result.plan;

            sessionStorage.setItem(
                "auvrion_approved_plan",
                JSON.stringify(approvedPlan)
            );

            message(
                "approvalMessage",
                `Plan approved. Total: ${approvedPlan.currency} ${Number(approvedPlan.total_amount).toFixed(2)}`
            );

            currentPlan = null;
            button.textContent = "Approved";

            setTimeout(() => {
                window.location.href = "/payments/";
            }, 900);

        } catch (error) {
            message("approvalMessage", error.message, true);

            button.disabled = false;
            button.textContent = "Approve plan";
        }
    });
});
