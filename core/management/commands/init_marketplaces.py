from django.core.management.base import BaseCommand
from django.db import transaction

from core.marketplaces import initialize_marketplaces


class Command(BaseCommand):
    help = "Maintain the five approved MVP labels; archive other labels without deleting any records."

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(f"Created {initialize_marketplaces()} approved marketplace labels. Exactly five are supported. "
                          "Other labels are archived; records/history retained. No live integration enabled.")
