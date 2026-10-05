from django import test
from django.apps import apps
from django.db import connection
from django.db.migrations.executor import MigrationExecutor


class TestCaseMigrations(test.TestCase):
    """TestCase for Django Migrations

    migrate_from, migrate_to should be Django migration names of tested app
    setUpBeforeMigration(self, apps) method will be called before migrations
    are applied

    source: https://www.caktusgroup.com/blog/2016/02/02/writing-unit-tests-django-migrations/
    """

    @property
    def app(self):
        return apps.get_containing_app_config(type(self).__module__).name.split(".")[-1]

    migrate_from = None
    migrate_to = None
    # Apps after migrations
    apps = None

    def setUp(self):
        assert self.migrate_from and self.migrate_to, f"TestCase '{type(self).__name__}' must define migrate_from and migrate_to properties"
        self.migrate_from = [(self.app, self.migrate_from)]
        self.migrate_to = [(self.app, self.migrate_to)]

        # https://code.djangoproject.com/ticket/30023
        # We have to disable foreign key constraint checking in sqlite because
        # MigrationExecutor uses with transaction.atomic() under the hood.
        if connection.vendor == "sqlite":
            connection.cursor().execute("PRAGMA foreign_keys = OFF")

            org_disable_constraint_checking = connection.disable_constraint_checking
            org_enable_constraint_checking = connection.enable_constraint_checking

            connection.disable_constraint_checking = lambda: True
            connection.enable_constraint_checking = lambda: True

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

        # Reenable foreign key constraints checking.
        if connection.vendor == "sqlite":
            connection.cursor().execute("PRAGMA foreign_keys = ON")

            connection.disable_constraint_checking = org_disable_constraint_checking
            connection.enable_constraint_checking = org_enable_constraint_checking

    def setUpBeforeMigration(self, apps):
        pass
