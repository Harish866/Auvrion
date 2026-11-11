
import json
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from pathlib import Path
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import ensure_csrf_cookie

from .ai import build_ai_plan
from .models import Agent, Task, ExecutionPlan, PaymentTransaction, ExecutionRun
from .execution import run_csv_workflow
from .services import initialize_agents
from .paypal_service import (
    PayPalAPIError,
    create_paypal_order,
    capture_paypal_order,
)


@ensure_csrf_cookie
def dashboard(request):
    return render(request, "index.html", {"active_page": "dashboard"})


def planner(request):
    return render(request, "planner.html", {"active_page": "planner"})


def agents_page(request):
    return render(request, "agents.html", {"active_page": "agents"})


def tasks_page(request):
    return render(request, "tasks.html", {"active_page": "tasks"})


@ensure_csrf_cookie
def payments_page(request):
    return render(
        request,
        "payments.html",
        {
            "active_page": "payments",
            "paypal_return_order_id": request.GET.get("token", ""),
            "paypal_cancelled": request.GET.get("cancelled") == "1",
        },
    )


def paypal_return(request):
    return render(
        request,
        "payments.html",
        {
            "active_page": "payments",
            "paypal_return_order_id": request.GET.get("token", ""),
        },
    )


def paypal_cancel(request):
    return render(
        request,
        "payments.html",
        {
            "active_page": "payments",
            "paypal_cancelled": True,
        },
    )


def settings_page(request):
    return render(request, "settings.html", {"active_page": "settings"})


def _json_body(request):
    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        raise ValueError("Request body must contain valid JSON.")

    if not isinstance(data, dict):
        raise ValueError("The request body must be a JSON object.")

    return data


def _task_data(task):
    return {
        "id": str(task.task_id),
        "title": task.title,
        "agent": task.agent.name if task.agent else "Unassigned",
        "agent_id": task.agent_id,
        "priority": task.priority,
        "status": task.status,
        "progress": task.progress,
        "execution_output": task.execution_output,
        "budget": str(task.budget),
        "created_at": task.created_at.isoformat(),
        "execution_plan_status": task.execution_plan.status if task.execution_plan_id else None,
        "payment_required": bool(task.execution_plan_id and task.execution_plan.status != "Paid"),
    }


@require_GET
def api_agents(request):
    initialize_agents()
    agents = Agent.objects.all().order_by("id")

    return JsonResponse({
        "agents": [{
            "id": agent.id,
            "name": agent.name,
            "description": agent.description,
            "price": str(agent.price),
            "is_active": agent.is_active,
        } for agent in agents]
    })


@require_GET
def api_tasks(request):
    tasks = Task.objects.select_related("agent").all().order_by("-created_at")
    return JsonResponse({"tasks": [_task_data(task) for task in tasks]})


@require_POST
def api_tasks_create(request):
    try:
        data = _json_body(request)
        title = str(data.get("title", "")).strip()

        if not title:
            return JsonResponse({"error": "Task title is required."}, status=400)

        if len(title) > 255:
            return JsonResponse({"error": "Task title is too long."}, status=400)

        agent = None
        agent_id = data.get("agent_id")

        if agent_id:
            agent = Agent.objects.filter(id=agent_id, is_active=True).first()

            if not agent:
                return JsonResponse(
                    {"error": "Selected agent is unavailable."},
                    status=400,
                )

        priority = data.get("priority", "Medium")

        if priority not in {"Low", "Medium", "High"}:
            return JsonResponse({"error": "Invalid priority."}, status=400)

        budget = agent.price if agent else Decimal("0.00")

        task = Task.objects.create(
            title=title,
            agent=agent,
            priority=priority,
            budget=budget,
        )

        return JsonResponse({
            "message": "Task created.",
            "task": _task_data(task),
        }, status=201)

    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)


@require_POST
def api_update_task(request, task_id):
    try:
        data = _json_body(request)
        task = Task.objects.select_related("execution_plan").get(task_id=task_id)

        requested_status = data.get("status", task.status)
        requested_progress = data.get("progress", task.progress)

        if (
            task.execution_plan_id
            and task.execution_plan.status != "Paid"
            and (
                requested_status in {"Running", "Completed"}
                or (str(requested_progress).isdigit() and int(requested_progress) > 0)
            )
        ):
            return JsonResponse(
                {
                    "error": (
                        "Payment is required before this plan's tasks can start. "
                        "Complete the PayPal checkout first."
                    ),
                    "payment_required": True,
                    "plan_status": task.execution_plan.status,
                },
                status=402,
            )

        status = data.get("status", task.status)
        progress = data.get("progress", task.progress)

        if status not in dict(Task.STATUS_CHOICES):
            return JsonResponse({"error": "Invalid task status."}, status=400)

        try:
            progress = int(progress)
        except (TypeError, ValueError):
            return JsonResponse(
                {"error": "Progress must be a number."},
                status=400,
            )

        if not 0 <= progress <= 100:
            return JsonResponse(
                {"error": "Progress must be between 0 and 100."},
                status=400,
            )

        task.status = status
        task.progress = progress

        if status == "Completed":
            task.progress = 100
        elif status == "Queued" and progress == 0:
            task.progress = 0

        task.save()

        return JsonResponse({
            "message": "Task updated.",
            "task": _task_data(task),
        })

    except Task.DoesNotExist:
        return JsonResponse({"error": "Task not found."}, status=404)

    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)


@require_POST
def api_ai_plan(request):
    try:
        data = _json_body(request)
        goal = str(data.get("goal", "")).strip()

        if not goal:
            return JsonResponse({"error": "Please enter a goal."}, status=400)

        if len(goal) > 1000:
            return JsonResponse(
                {"error": "Goal must be 1000 characters or fewer."},
                status=400,
            )

        initialize_agents()
        plan = build_ai_plan(goal)

        return JsonResponse({
            "message": "Plan generated.",
            "plan": plan,
        })

    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)

    except Exception:
        return JsonResponse({
            "error": (
                "The AI planner could not generate a plan. "
                "Check the server terminal and Groq configuration."
            )
        }, status=502)


@require_POST
def api_approve_plan(request):
    try:
        data = _json_body(request)
        tasks = data.get("tasks")

        if not isinstance(tasks, list) or not tasks:
            return JsonResponse(
                {"error": "There are no tasks to approve."},
                status=400,
            )

        if len(tasks) > 5:
            return JsonResponse(
                {"error": "A plan can contain at most 5 tasks."},
                status=400,
            )

        validated_tasks = []
        total_amount = Decimal("0.00")

        for item in tasks:
            if not isinstance(item, dict):
                return JsonResponse(
                    {"error": "Invalid task data in the plan."},
                    status=400,
                )

            agent = Agent.objects.filter(
                id=item.get("agent_id"),
                is_active=True,
            ).first()

            if not agent:
                return JsonResponse(
                    {"error": "An agent in this plan is no longer available."},
                    status=400,
                )

            title = str(item.get("title", "")).strip()
            priority = item.get("priority", "Medium")

            if not title or priority not in {"Low", "Medium", "High"}:
                return JsonResponse(
                    {"error": "The plan contains invalid task details."},
                    status=400,
                )

            validated_tasks.append({
                "title": title[:255],
                "agent": agent,
                "priority": priority,
            })

            total_amount += agent.price

        with transaction.atomic():
            execution_plan = ExecutionPlan.objects.create(
                total_amount=total_amount,
                currency="USD",
                status="Pending",
            )

            created = []

            for item in validated_tasks:
                task = Task.objects.create(
                    title=item["title"],
                    agent=item["agent"],
                    execution_plan=execution_plan,
                    priority=item["priority"],
                    budget=item["agent"].price,
                )
                created.append(_task_data(task))

        return JsonResponse({
            "message": "Plan approved. Tasks have been added to Task Operations.",
            "plan": {
                "id": str(execution_plan.plan_id),
                "total_amount": str(execution_plan.total_amount),
                "currency": execution_plan.currency,
                "status": execution_plan.status,
            },
            "tasks": created,
        }, status=201)

    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)


@require_GET
def api_payments(request):
    """Return payment history and summary figures for the Payments page."""
    plans = (
        ExecutionPlan.objects
        .prefetch_related("payment")
        .order_by("-created_at")
    )

    rows = []
    completed_total = Decimal("0.00")
    completed_count = 0
    pending_count = 0
    failed_count = 0

    for plan in plans:
        payment = getattr(plan, "payment", None)

        if payment:
            status = payment.status
            order_id = payment.paypal_order_id or ""
            capture_id = payment.paypal_capture_id or ""
            amount = payment.amount
            currency = payment.currency
            created_at = payment.created_at
        else:
            status = "Pending" if plan.status == "Pending" else plan.status
            order_id = ""
            capture_id = ""
            amount = plan.total_amount
            currency = plan.currency
            created_at = plan.created_at

        if plan.status == "Paid" and payment and payment.status == "Completed":
            completed_total += amount
            completed_count += 1
            status = "Completed"
        elif status in {"Created", "Approved", "Pending"}:
            pending_count += 1
            status = "Pending"
        elif status == "Failed":
            failed_count += 1

        rows.append({
            "plan_id": str(plan.plan_id),
            "amount": str(amount),
            "currency": currency,
            "status": status,
            "order_id": order_id,
            "capture_id": capture_id,
            "created_at": created_at.isoformat(),
        })

    return JsonResponse({
        "summary": {
            "total_revenue": str(completed_total),
            "completed_count": completed_count,
            "pending_count": pending_count,
            "failed_count": failed_count,
        },
        "transactions": rows,
    })


@require_GET
def api_executions(request):
    plans = ExecutionPlan.objects.filter(status="Paid").order_by("-created_at")
    plan_rows = [{"id": str(plan.plan_id), "amount": str(plan.total_amount), "currency": plan.currency,
                  "created_at": plan.created_at.isoformat()} for plan in plans]
    runs = ExecutionRun.objects.select_related("plan").order_by("-created_at")[:10]
    run_rows = [{"id": str(run.run_id), "plan_id": str(run.plan.plan_id),
                 "filename": run.original_filename, "status": run.status,
                 "created_at": run.created_at.isoformat(), "error": run.error_message}
                for run in runs]
    return JsonResponse({"paid_plans": plan_rows, "runs": run_rows})


@require_POST
def api_execute_plan(request):
    plan_id = str(request.POST.get("plan_id", "")).strip()
    uploaded = request.FILES.get("dataset")
    if not plan_id or not uploaded:
        return JsonResponse({"error": "Choose a paid plan and upload a CSV file."}, status=400)
    if not uploaded.name.lower().endswith(".csv"):
        return JsonResponse({"error": "Only .csv files are accepted."}, status=400)
    if uploaded.size > 5 * 1024 * 1024:
        return JsonResponse({"error": "CSV files must be 5 MB or smaller."}, status=413)

    plan = ExecutionPlan.objects.filter(plan_id=plan_id, status="Paid").first()
    if not plan:
        return JsonResponse({"error": "A completed payment is required before execution."}, status=402)
    tasks = list(Task.objects.select_related("agent").filter(execution_plan=plan).order_by("created_at"))
    if not tasks:
        return JsonResponse({"error": "This plan has no tasks to execute."}, status=400)
    if not any(task.agent and "analyst" in task.agent.name.lower() for task in tasks):
        return JsonResponse({"error": "This plan has no Data Analyst task. Generate a plan that includes the Data Analyst agent."}, status=400)

    run = ExecutionRun.objects.create(plan=plan, dataset=uploaded, original_filename=Path(uploaded.name).name)
    try:
        for task in tasks:
            task.status = "Running"
            task.progress = 10
            task.save(update_fields=["status", "progress", "updated_at"])
        analysis, report, artifacts = run_csv_workflow(run, tasks)
        run.analysis = analysis
        run.report = report
        run.artifacts = artifacts
        run.status = "Completed"
        run.completed_at = timezone.now()
        run.save(update_fields=["analysis", "report", "artifacts", "status", "completed_at"])
        return JsonResponse({"message": "Agent workflow completed.", "run": {
            "id": str(run.run_id), "filename": run.original_filename, "status": run.status,
            "analysis": run.analysis, "report": run.report, "artifacts": run.artifacts,
        }})
    except Exception as exc:
        run.status = "Failed"
        run.error_message = str(exc)[:1000]
        run.save(update_fields=["status", "error_message"])
        for task in tasks:
            task.refresh_from_db()
            if task.status == "Running":
                task.status = "Failed"
                task.execution_output = run.error_message
                task.save(update_fields=["status", "execution_output", "updated_at"])
        return JsonResponse({"error": f"Execution failed: {run.error_message}", "run_id": str(run.run_id)}, status=502)


@require_GET
def api_execution_detail(request, run_id):
    run = ExecutionRun.objects.filter(run_id=run_id).first()
    if not run:
        return JsonResponse({"error": "Execution run not found."}, status=404)
    return JsonResponse({"run": {"id": str(run.run_id), "filename": run.original_filename,
        "status": run.status, "analysis": run.analysis, "report": run.report,
        "artifacts": run.artifacts, "error": run.error_message,
        "created_at": run.created_at.isoformat()}})


@require_POST
def api_create_paypal_order(request):
    try:
        data = _json_body(request)
        plan_id = str(data.get("plan_id", "")).strip()

        if not plan_id:
            return JsonResponse({"error": "Plan ID is required."}, status=400)

        plan = ExecutionPlan.objects.filter(plan_id=plan_id).first()

        if not plan:
            return JsonResponse({"error": "Execution plan not found."}, status=404)

        if plan.status == "Paid":
            return JsonResponse({"error": "This plan has already been paid."}, status=409)

        if plan.status == "Cancelled":
            return JsonResponse({"error": "This plan has been cancelled."}, status=409)

        payment, _ = PaymentTransaction.objects.get_or_create(
            plan=plan,
            defaults={
                "amount": plan.total_amount,
                "currency": plan.currency,
            },
        )

        if payment.status == "Completed":
            return JsonResponse({"error": "This payment is already completed."}, status=409)

        # Reuse an existing order instead of creating another one.
        if payment.paypal_order_id and payment.paypal_approval_url:
            return JsonResponse({
                "message": "Existing PayPal order reused.",
                "order_id": payment.paypal_order_id,
                "approval_url": payment.paypal_approval_url,
                "amount": str(payment.amount),
                "currency": payment.currency,
            })

        if payment.paypal_order_id:
            return JsonResponse({
                "error": (
                    "A PayPal order already exists for this plan, "
                    "but its approval URL is unavailable. "
                    "Please contact the project administrator."
                )
            }, status=409)

        return_url = request.build_absolute_uri(reverse("paypal_return"))
        cancel_url = request.build_absolute_uri(reverse("paypal_cancel"))

        result = create_paypal_order(
            amount=payment.amount,
            currency=payment.currency,
            return_url=return_url,
            cancel_url=cancel_url,
        )

        payment.paypal_order_id = result["order_id"]
        payment.paypal_approval_url = result["approval_url"]
        payment.status = "Created"
        payment.save(update_fields=[
            "paypal_order_id",
            "paypal_approval_url",
            "status",
            "updated_at",
        ])

        return JsonResponse({
            "message": "PayPal order created.",
            "order_id": payment.paypal_order_id,
            "approval_url": payment.paypal_approval_url,
            "amount": str(payment.amount),
            "currency": payment.currency,
        }, status=201)

    except (ValueError, InvalidOperation) as exc:
        return JsonResponse({"error": str(exc)}, status=400)

    except PayPalAPIError as exc:
        return JsonResponse({
            "error": f"PayPal could not create the order: {str(exc)}"
        }, status=502)


@require_POST
def api_capture_paypal_order(request):
    try:
        data = _json_body(request)
        order_id = str(data.get("order_id", "")).strip()

        if not order_id:
            return JsonResponse({"error": "PayPal order ID is required."}, status=400)

        payment = (
            PaymentTransaction.objects
            .select_related("plan")
            .filter(paypal_order_id=order_id)
            .first()
        )

        if not payment:
            return JsonResponse({"error": "Payment order not found."}, status=404)

        if payment.status == "Completed" and payment.plan.status == "Paid":
            return JsonResponse({
                "message": "Payment was already completed.",
                "status": "Completed",
                "plan_status": payment.plan.status,
            })

        result = capture_paypal_order(order_id)

        purchase_units = result.get("purchase_units", [])
        if not isinstance(purchase_units, list) or not purchase_units:
            return JsonResponse(
                {"error": "PayPal returned no purchase details. Payment was not marked as paid."},
                status=502,
            )

        captures = (
            purchase_units[0]
            .get("payments", {})
            .get("captures", [])
        )

        completed_capture = next(
            (
                capture for capture in captures
                if capture.get("status") == "COMPLETED"
            ),
            None,
        )

        if result.get("status") != "COMPLETED" or not completed_capture:
            return JsonResponse({
                "error": "PayPal has not confirmed a completed capture.",
                "paypal_status": result.get("status", "Unknown"),
            }, status=409)

        capture_amount = completed_capture.get("amount", {})

        try:
            received_amount = Decimal(str(capture_amount.get("value"))).quantize(
                Decimal("0.01")
            )
        except (InvalidOperation, TypeError):
            return JsonResponse(
                {"error": "PayPal returned an invalid capture amount."},
                status=502,
            )

        received_currency = str(capture_amount.get("currency_code", "")).upper()

        if (
            received_amount != payment.amount
            or received_currency != payment.currency.upper()
        ):
            return JsonResponse(
                {
                    "error": (
                        "The captured amount or currency does not match "
                        "the approved plan. The plan has not been marked as paid."
                    )
                },
                status=409,
            )

        capture_id = completed_capture.get("id")

        if not capture_id:
            return JsonResponse(
                {"error": "PayPal did not return a capture ID."},
                status=502,
            )

        with transaction.atomic():
            locked_payment = (
                PaymentTransaction.objects
                .select_for_update()
                .select_related("plan")
                .get(pk=payment.pk)
            )

            if locked_payment.status != "Completed":
                locked_payment.paypal_capture_id = capture_id
                locked_payment.status = "Completed"
                locked_payment.save(update_fields=[
                    "paypal_capture_id",
                    "status",
                    "updated_at",
                ])

                locked_payment.plan.status = "Paid"
                locked_payment.plan.save(update_fields=["status"])

        return JsonResponse({
            "message": "PayPal payment captured and verified successfully.",
            "status": "Completed",
            "capture_id": capture_id,
            "amount": str(payment.amount),
            "currency": payment.currency,
            "plan_status": "Paid",
        })

    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)

    except PayPalAPIError as exc:
        return JsonResponse({
            "error": f"PayPal capture failed: {str(exc)}"
        }, status=502)
