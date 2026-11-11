from django.urls import path
from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("planner/", views.planner, name="planner"),
    path("agents/", views.agents_page, name="agents"),
    path("tasks/", views.tasks_page, name="tasks"),
    path("payments/", views.payments_page, name="payments"),
    path("payments/return/", views.paypal_return, name="paypal_return"),
    path("payments/cancel/", views.paypal_cancel, name="paypal_cancel"),
    path("settings/", views.settings_page, name="settings"),

    path("api/agents/", views.api_agents, name="api_agents"),
    path("api/tasks/", views.api_tasks, name="api_tasks"),
    path("api/tasks/create/", views.api_tasks_create, name="api_tasks_create"),
    path("api/tasks/<uuid:task_id>/update/", views.api_update_task, name="api_update_task"),
    path("api/ai/plan/", views.api_ai_plan, name="api_ai_plan"),
    path("api/ai/approve/", views.api_approve_plan, name="api_approve_plan"),
    path("api/payments/", views.api_payments, name="api_payments"),
    path("api/executions/", views.api_executions, name="api_executions"),
    path("api/executions/run/", views.api_execute_plan, name="api_execute_plan"),
    path("api/executions/<uuid:run_id>/", views.api_execution_detail, name="api_execution_detail"),
    path("api/payments/create-order/", views.api_create_paypal_order, name="api_create_paypal_order"),
    path("api/payments/capture/", views.api_capture_paypal_order, name="api_capture_paypal_order"),
]
