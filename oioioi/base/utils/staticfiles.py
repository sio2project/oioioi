from django.contrib.staticfiles.storage import ManifestStaticFilesStorage


class ManifestLaxStaticFilesStorage(ManifestStaticFilesStorage):
    manifest_strict = False
