from django.apps import apps
from django import test
from django.db.migrations.executor import MigrationExecutor
from django.db import connection


class TestCaseMigrations(test.TestCase):
    """TestCase for Django Migrations

    migrate_from, migrate_to should be Django migration names of tested app
    setUpBeforeMigration(self, apps) method will be called before migrations
    are applied

    source: https://www.caktusgroup.com/blog/2016/02/02/writing-unit-tests-django-migrations/
    """
    @property
    def app(self):
        return apps.get_containing_app_config(type(self).__module__).name.split('.')[-1]

    migrate_from = None
    migrate_to = None
    # Apps after migrations
    apps = None

    def setUp(self):
        assert self.migrate_from and self.migrate_to, \
            "TestCase '{}' must define migrate_from and migrate_to properties".format(type(self).__name__)
        self.migrate_from = [(self.app, self.migrate_from)]
        self.migrate_to = [(self.app, self.migrate_to)]
        executor = MigrationExecutor(connection)
        # Detect disabled migrations tests by checking if there are any
        # migration nodes loaded
        if executor.loader.graph.nodes == {}:
            self.skipTest("not possible with migrations disabled")
        old_apps = executor.loader.project_state(self.migrate_from).apps

        # Reverse to the original migration
        executor.migrate(self.migrate_from)

        self.setUpBeforeMigration(old_apps)

        # Run the migration to test
        executor = MigrationExecutor(connection)
        executor.loader.build_graph()  # reload
        executor.migrate(self.migrate_to)

        self.apps = executor.loader.project_state(self.migrate_to).apps

    def setUpBeforeMigration(self, apps):
        pass