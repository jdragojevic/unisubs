from django.core.management.base import BaseCommand
from raven.contrib.django.models import get_client

client = get_client()


class ErrorHandlingCommand(BaseCommand):
    def handle_error(self, exc_info):
        client.captureException()

    def print_to_console(self, msg, min_verbosity=1):
        if self.verbosity >= min_verbosity:
            print msg
