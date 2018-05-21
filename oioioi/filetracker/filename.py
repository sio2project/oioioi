from filetracker.utils import split_name


class FiletrackerFilename(unicode):
    """A class inheriting from ``unicode`` used for versioned paths
       in Filetracker.

       When accessed as a string/unicode, this class acts as if the path
       was not versioned. This is suitable for any normal code, which would
       like to extract let's say the basename or extension of the file.

       Only the code which is Filetracker-aware can extract the versioned name,
       by accessing the :attr:`versioned_name` attribute.
    """
    def __new__(cls, versioned_name):
        # http://stackoverflow.com/questions/14783698/how-to-or-why-not-call-unicode-init-from-subclass
        if isinstance(versioned_name, FiletrackerFilename):
            versioned_name = versioned_name.versioned_name
        versioned_name = unicode(versioned_name)
        name, _version = split_name(versioned_name)
        self = unicode.__new__(cls, name)
        self.versioned_name = versioned_name
        return self
