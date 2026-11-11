import json
import os
import re
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from django.conf import settings
from django.core.files.storage import default_storage
from groq import Groq


MAX_ROWS = 10000
MAX_COLUMNS = 40


def _json_safe(value):
    if hasattr(value, "item"):
        value = value.item()
    if isinstance(value, (str, int, float, bool)) or value is None:
        if isinstance(value, float) and (pd.isna(value) or not pd.notna(value)):
            return None
        return value
    return str(value)


def run_csv_workflow(execution_run, tasks):
    """Execute the three AUVRION agent roles against one validated CSV."""
    dataset_path = execution_run.dataset.path
    frame = pd.read_csv(dataset_path)
    if frame.empty:
        raise ValueError("The CSV contains no data rows.")
    if len(frame) > MAX_ROWS:
        raise ValueError(f"The CSV exceeds the {MAX_ROWS:,}-row execution limit.")
    if len(frame.columns) > MAX_COLUMNS:
        raise ValueError(f"The CSV exceeds the {MAX_COLUMNS}-column execution limit.")

    frame.columns = [str(column).strip() for column in frame.columns]
    if any(not column for column in frame.columns):
        raise ValueError("Every CSV column must have a name.")

    numeric = frame.select_dtypes(include="number")
    categorical = frame.select_dtypes(exclude="number")
    analysis = {
        "row_count": int(len(frame)),
        "column_count": int(len(frame.columns)),
        "columns": list(frame.columns),
        "missing_values": {str(k): int(v) for k, v in frame.isna().sum().items()},
        "numeric_summary": {},
        "category_summary": {},
    }

    if not numeric.empty:
        desc = numeric.describe().replace({float("inf"): None, float("-inf"): None})
        analysis["numeric_summary"] = {
            str(col): {str(stat): _json_safe(val) for stat, val in desc[col].items()}
            for col in desc.columns
        }
    for column in categorical.columns[:8]:
        counts = frame[column].astype(str).value_counts().head(8)
        analysis["category_summary"][str(column)] = {
            str(k): int(v) for k, v in counts.items()
        }

    # Visualization Specialist: generate charts from actual CSV columns.
    artifacts = []
    run_dir = f"auvrion_runs/{execution_run.run_id}"
    if not numeric.empty:
        for column in list(numeric.columns[:3]):
            fig, ax = plt.subplots(figsize=(8, 4.5))
            values = numeric[column].dropna()
            ax.plot(range(1, len(values) + 1), values.values, marker=".", linewidth=1.5)
            ax.set_title(f"{column} — values by row")
            ax.set_xlabel("Row")
            ax.set_ylabel(str(column))
            ax.grid(True, alpha=0.25)
            fig.tight_layout()
            local_path = Path(settings.MEDIA_ROOT) / "tmp" / f"{re.sub(r'[^a-zA-Z0-9_-]', '_', str(column))}.png"
            local_path.parent.mkdir(parents=True, exist_ok=True)
            fig.savefig(local_path, dpi=140)
            plt.close(fig)
            with local_path.open("rb") as image_file:
                saved = default_storage.save(f"{run_dir}/{local_path.name}", image_file)
            artifacts.append({"name": f"{column} chart", "url": default_storage.url(saved), "kind": "chart"})
            local_path.unlink(missing_ok=True)
    elif not categorical.empty:
        column = categorical.columns[0]
        counts = frame[column].astype(str).value_counts().head(10)
        fig, ax = plt.subplots(figsize=(8, 4.5))
        counts.sort_values().plot(kind="barh", ax=ax)
        ax.set_title(f"Top values — {column}")
        ax.set_xlabel("Rows")
        ax.set_ylabel(str(column))
        fig.tight_layout()
        local_path = Path(settings.MEDIA_ROOT) / "tmp" / "category_summary.png"
        local_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(local_path, dpi=140)
        plt.close(fig)
        with local_path.open("rb") as image_file:
            saved = default_storage.save(f"{run_dir}/category_summary.png", image_file)
        artifacts.append({"name": f"{column} category chart", "url": default_storage.url(saved), "kind": "chart"})
        local_path.unlink(missing_ok=True)

    # Report Writer: use computed facts as context; never ask the model to invent metrics.
    api_key = os.getenv("GROQ_API_KEY", "")
    if not api_key:
        raise ValueError("GROQ_API_KEY is missing; the data analysis ran but the report could not be generated.")
    client = Groq(api_key=api_key)
    response = client.chat.completions.create(
        model=os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"),
        temperature=0.2,
        messages=[
            {"role": "system", "content": "Write a concise executive data report using only the supplied computed dataset facts. Clearly label limitations. Do not invent values, causal claims, or recommendations unsupported by the data."},
            {"role": "user", "content": "Create an executive summary, key findings, caveats and practical recommendations from these computed CSV statistics:\n" + json.dumps(analysis, ensure_ascii=False)[:18000]},
        ],
    )
    report = response.choices[0].message.content.strip()
    if not report:
        raise ValueError("The Report Writer returned an empty report.")

    # Mark tasks complete only after every role has returned its deliverable.
    for task in tasks:
        agent_name = (task.agent.name if task.agent else "").lower()
        if "analyst" in agent_name:
            task.execution_output = "Dataset analysis completed: " + str(analysis["row_count"]) + " rows analysed."
        elif "visual" in agent_name:
            task.execution_output = f"Generated {len(artifacts)} chart(s) from numeric dataset columns."
        elif "report" in agent_name or "writer" in agent_name:
            task.execution_output = "Executive report generated."
        else:
            task.execution_output = "Included in the CSV execution workflow; see run results."
        task.status = "Completed"
        task.progress = 100
        task.save(update_fields=["execution_output", "status", "progress", "updated_at"])

    return analysis, report, artifacts
