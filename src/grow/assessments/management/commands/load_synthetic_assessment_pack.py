from django.core.management.base import BaseCommand

from grow.synthetic.assessment_pack import create_synthetic_assessment_pack


class Command(BaseCommand):
    help = "Create the deterministic synthetic Milestone 2 assessment pack"

    def handle(self, *args: object, **options: object) -> None:
        sessions = create_synthetic_assessment_pack()
        self.stdout.write(
            self.style.SUCCESS(f"Synthetic assessment sessions ready: {len(sessions)}")
        )
