from django.core.management.base import BaseCommand

from grow.synthetic.career_pack import create_synthetic_career_pack


class Command(BaseCommand):
    help = "Load the idempotent synthetic/reference-only Milestone 3 career pack."

    def handle(self, *args: object, **options: object) -> None:
        careers = create_synthetic_career_pack()
        self.stdout.write(self.style.SUCCESS(f"Loaded {len(careers)} synthetic career profiles."))
