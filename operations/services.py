from .models import Agent


def initialize_agents():
    """Create the starter agents without resetting existing active/inactive flags."""
    defaults = [
        {
            "name": "Data Analyst",
            "description": "Data processing, exploration and analysis",
            "price": 5.00,
        },
        {
            "name": "Visualization Specialist",
            "description": "Charts, dashboards and visual analytics",
            "price": 3.00,
        },
        {
            "name": "Report Writer",
            "description": "Structured reports and documentation",
            "price": 4.00,
        },
    ]

    for item in defaults:
        Agent.objects.get_or_create(
            name=item["name"],
            defaults={
                "description": item["description"],
                "price": item["price"],
                "is_active": True,
            },
        )
