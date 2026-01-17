"""
Django app configuration for charts application.

Handles startup initialization including the auto-update scheduler.
"""

from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)


class ChartsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'charts'

    def ready(self):
        """
        Called when Django starts.

        Initializes the background scheduler if auto-updates are enabled.
        This runs once per process (not on every request).
        """
        # Import here to avoid AppRegistryNotReady exception
        from django.conf import settings

        # Only start scheduler in main process (not during migrations, tests, etc.)
        # Check for 'runserver' or 'gunicorn' in command line
        import sys
        if 'runserver' in sys.argv or 'gunicorn' in sys.argv[0]:
            # Start the scheduler
            from .scheduler import start_scheduler

            try:
                start_scheduler()
            except Exception as e:
                logger.error(f"Failed to start auto-update scheduler: {e}", exc_info=True)
        else:
            logger.debug(f"Skipping scheduler startup (command: {sys.argv})")
