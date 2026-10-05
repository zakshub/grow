from django.core.management.base import BaseCommand

from grow.synthetic.scenarios import create_synthetic_scenarios


class Command(BaseCommand):
    help = "Create deterministic synthetic-only Milestone 1 scenarios"

    def handle(self, *args: object, **options: object) -> None:
        scenarios = create_synthetic_scenarios()
        self.stdout.write(self.style.SUCCESS(f"Synthetic scenarios available: {len(scenarios)}"))
