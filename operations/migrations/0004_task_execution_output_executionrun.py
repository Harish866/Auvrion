import uuid
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("operations", "0003_paymenttransaction_paypal_approval_url")]

    operations = [
        migrations.AddField(
            model_name="task",
            name="execution_output",
            field=models.TextField(blank=True),
        ),
        migrations.CreateModel(
            name="ExecutionRun",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("run_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("dataset", models.FileField(upload_to="auvrion_datasets/%Y/%m/")),
                ("original_filename", models.CharField(max_length=255)),
                ("status", models.CharField(choices=[("Processing", "Processing"), ("Completed", "Completed"), ("Failed", "Failed")], default="Processing", max_length=20)),
                ("analysis", models.JSONField(blank=True, default=dict)),
                ("report", models.TextField(blank=True)),
                ("artifacts", models.JSONField(blank=True, default=list)),
                ("error_message", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("plan", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="runs", to="operations.executionplan")),
            ],
        ),
    ]
