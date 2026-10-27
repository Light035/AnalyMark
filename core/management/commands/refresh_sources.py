import time

from django.core.management.base import BaseCommand, CommandError
from django.db import close_old_connections

from core.refreshing import recover_stuck, worker_pass


class Command(BaseCommand):
    help = "Run the refresh queue and due schedules. Kaspi access is currently blocked; no live prices are acquired."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true", help="One bounded pass, then exit.")
        parser.add_argument("--poll-seconds", type=int, default=15, help="Worker polling interval, 1–300 seconds.")
        parser.add_argument("--recover-stuck-minutes", type=int, help="Explicitly fail running operations older than this interval. Inspect/stop old workers first.")

    def handle(self, *args, **options):
        if not 1 <= options["poll_seconds"] <= 300:
            raise CommandError("Polling interval must be 1–300 seconds.")
        if options["recover_stuck_minutes"] is not None:
            if options["recover_stuck_minutes"] < 1:
                raise CommandError("Recovery interval must be positive.")
            self.stdout.write(f"Recovered {recover_stuck(options['recover_stuck_minutes'])} interrupted operations.")
        self.stdout.write("Refresh worker: no verified Kaspi competitor source is connected. Completed operations may be BLOCKED, not successful acquisitions.")
        try:
            while True:
                close_old_connections()
                queued, completed = worker_pass()
                if queued or completed or options["once"]:
                    self.stdout.write(f"Queued {queued}; finished {completed} operations. Check source/run status for outcomes.")
                if options["once"]:
                    break
                time.sleep(options["poll_seconds"])
        except KeyboardInterrupt:
            self.stdout.write("Worker stopped. If interrupted during acquisition, inspect/recover its running operation before retrying.")
