import json
import os
from decimal import Decimal

from django.conf import settings
from dotenv import load_dotenv
from groq import Groq

from .models import Agent

load_dotenv(settings.BASE_DIR / ".env")


def build_ai_plan(goal):
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY is missing from the .env file.")

    agents = list(Agent.objects.filter(is_active=True).order_by("name"))
    if not agents:
        raise ValueError("No active agents are available.")

    agent_catalogue = [
        {"name": agent.name, "price": float(agent.price),
         "description": agent.description}
        for agent in agents
    ]
    allowed_names = {agent.name for agent in agents}

    client = Groq(api_key=api_key)
    completion = client.chat.completions.create(
        model=os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"),
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a task-planning assistant for an AI agent marketplace. "
                    "Return valid JSON only with keys summary and tasks. "
                    "tasks must contain 1 to 5 objects. Each object must contain "
                    "title, agent, priority, and reason. Choose agent names only "
                    "from the supplied catalogue. Priority must be Low, Medium, "
                    "or High. Do not claim that tasks have already been executed."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"User goal: {goal}\n"
                    f"Available agents and prices: "
                    f"{json.dumps(agent_catalogue)}\n"
                    "Create a practical task breakdown."
                ),
            },
        ],
        temperature=0.2,
        response_format={"type": "json_object"},
    )

    raw = completion.choices[0].message.content
    try:
        parsed = json.loads(raw)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError("The AI returned an invalid plan. Please try again.") from exc

    proposed_tasks = parsed.get("tasks")
    if not isinstance(proposed_tasks, list) or not 1 <= len(proposed_tasks) <= 5:
        raise ValueError("The AI did not return between 1 and 5 tasks.")

    agent_by_name = {agent.name: agent for agent in agents}
    clean_tasks = []
    total = Decimal("0.00")

    for item in proposed_tasks:
        if not isinstance(item, dict):
            continue
        name = str(item.get("agent", "")).strip()
        if name not in allowed_names:
            raise ValueError(f"The AI selected an unavailable agent: {name}")
        agent = agent_by_name[name]
        priority = str(item.get("priority", "Medium")).title()
        if priority not in {"Low", "Medium", "High"}:
            priority = "Medium"

        price = agent.price
        total += price
        clean_tasks.append({
            "title": str(item.get("title", "Untitled task")).strip()[:255],
            "agent_id": agent.id,
            "agent": agent.name,
            "priority": priority,
            "reason": str(item.get("reason", "")).strip()[:500],
            "price": str(price),
        })

    if not clean_tasks:
        raise ValueError("The AI plan did not contain any valid tasks.")

    return {
        "summary": str(parsed.get("summary", "Proposed task plan"))[:500],
        "tasks": clean_tasks,
        "total_cost": str(total),
        "currency": "USD",
        "task_count": len(clean_tasks),
    }
