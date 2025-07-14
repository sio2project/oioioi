from oioioi.contests.controllers import ContestController


class LogoContestControllerMixin:
    """Sets default empty contest logo and icons settings."""

    def default_contestlogo_url(self):
        """Returns a URL of an image which will be used as the contest logo.

        If a contest admin specifies a contest logo URL in the contest
        settings view, it will be used instead of the one returned by this
        function.

        The default implementation returns None.
        """
        return None

    def default_contestlogo_link(self):
        """Returns a contest logo link.

        If a contest admin specifies a contest logo link in the contest
        settings view, it will be used instead of the one returned by this
        function.

        The default implementation returns an empty string.
        """
        return ""

    def default_contesticons_urls(self):
        """Returns a list of URLs of images which will be used to decorate
        the user side menu.

        If a contest admin adds some icon urls in the contest settings view,
        they will be used instead of the urls returned by this function.

        The default implementation returns an empty list.
        """
        return []


ContestController.mix_in(LogoContestControllerMixin)
