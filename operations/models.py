
import uuid
from decimal import Decimal

from django.db import models


class Agent(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField()
    price = models.DecimalField(max_digits=8, decimal_places=2)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class ExecutionPlan(models.Model):
    STATUS_CHOICES = [
        ("Pending", "Pending Payment"),
        ("Paid", "Paid"),
        ("Cancelled", "Cancelled"),
    ]

    plan_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False
    )
    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00")
    )
    currency = models.CharField(max_length=3, default="USD")
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="Pending"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Plan {self.plan_id} - {self.status}"


class Task(models.Model):
    STATUS_CHOICES = [
        ("Queued", "Queued"),
        ("Running", "Running"),
        ("Completed", "Completed"),
        ("Failed", "Failed"),
        ("Cancelled", "Cancelled"),
    ]

    PRIORITY_CHOICES = [
        ("Low", "Low"),
        ("Medium", "Medium"),
        ("High", "High"),
    ]

    task_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False
    )
    title = models.CharField(max_length=255)

    agent = models.ForeignKey(
        Agent,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tasks"
    )

    execution_plan = models.ForeignKey(
        ExecutionPlan,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tasks"
    )

    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default="Medium"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="Queued"
    )
    progress = models.PositiveIntegerField(default=0)
    execution_output = models.TextField(blank=True)
    budget = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal("0.00")
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class PaymentTransaction(models.Model):
    STATUS_CHOICES = [
        ("Created", "Created"),
        ("Approved", "Approved"),
        ("Completed", "Completed"),
        ("Failed", "Failed"),
    ]

    plan = models.OneToOneField(
        ExecutionPlan,
        on_delete=models.PROTECT,
        related_name="payment"
    )
    paypal_order_id = models.CharField(
        max_length=64,
        unique=True,
        null=True,
        blank=True
    )
    paypal_approval_url = models.URLField(
        max_length=2048,
        blank=True
    )
    paypal_capture_id = models.CharField(
        max_length=64,
        unique=True,
        null=True,
        blank=True
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )
    currency = models.CharField(max_length=3, default="USD")
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="Created"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Payment {self.paypal_order_id or self.pk} - {self.status}"


class ExecutionRun(models.Model):
    STATUS_CHOICES = [
        ("Processing", "Processing"),
        ("Completed", "Completed"),
        ("Failed", "Failed"),
    ]

    run_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    plan = models.ForeignKey(ExecutionPlan, on_delete=models.CASCADE, related_name="runs")
    dataset = models.FileField(upload_to="auvrion_datasets/%Y/%m/")
    original_filename = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Processing")
    analysis = models.JSONField(default=dict, blank=True)
    report = models.TextField(blank=True)
    artifacts = models.JSONField(default=list, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Execution {self.run_id} - {self.status}"
