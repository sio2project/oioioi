# Taken from
# https://github.com/gdub/python-archive/blob/master/archive/__init__.py

# Copyright (c) Gary Wilson Jr. <gary@thegarywilson.com> and contributors.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import os
import tarfile
import tempfile
import zipfile

from oioioi.filetracker.utils import stream_file


class ArchiveException(RuntimeError):
    """Base exception class for all archive errors."""


class UnrecognizedArchiveFormat(ArchiveException):
    """Error raised when passed file is not a recognized archive format."""


class UnsafeArchive(ArchiveException):
    """
    Error raised when passed file contains paths that would be extracted
    outside of the target directory.
    """


def extract(path, to_path='', ext='', **kwargs):
    """
    Unpack the tar or zip file at the specified path to the directory
    specified by to_path.
    """
    Archive(path, ext=ext).extract(to_path, **kwargs)


class Archive(object):
    """
    The external API class that encapsulates an archive implementation.
    """

    def __init__(self, file, ext=''):
        """
        Arguments:
        * 'file' can be a string path to a file or a file-like object.
        * Optional 'ext' argument can be given to override the file-type
          guess that is normally performed using the file extension of the
          given 'file'.  Should start with a dot, e.g. '.tar.gz'.
        """
        self.filename, self.stored_temporarily = self._resolve_streamed_files(
            file, ext=ext
        )
        self._archive = self._archive_cls(self.filename, ext=ext)(self.filename)

    def __del__(self):
        if self.stored_temporarily:
            os.remove(self.filename)

    @staticmethod
    def _resolve_streamed_files(file, ext):
        if isinstance(file, str) or hasattr(file, 'seek') or hasattr(file, 'tell'):
            return file, False
        lookup_filename = file.name + ext
        base, tail_ext = os.path.splitext(lookup_filename.lower())
        f = tempfile.NamedTemporaryFile(suffix=tail_ext, delete=False)
        f.writelines(stream_file(file, file.name).streaming_content)
        f.close()
        return f.name, True

    @staticmethod
    def _archive_cls(file, ext=''):
        """
        Return the proper Archive implementation class, based on the file type.
        """
        cls = None
        filename = None
        if isinstance(file, str):
            filename = file
        else:
            try:
                filename = file.name
            except AttributeError:
                raise UnrecognizedArchiveFormat(
                    "File object not a recognized archive format."
                )
        lookup_filename = filename + ext
        base, tail_ext = os.path.splitext(lookup_filename.lower())
        cls = extension_map.get(tail_ext)
        if not cls:
            base, ext = os.path.splitext(base)
            cls = extension_map.get(ext)
        if not cls:
            raise UnrecognizedArchiveFormat(
                "Path not a recognized archive format: %s" % filename
            )
        return cls

    def extract(self, *args, **kwargs):
        self._archive.extract(*args, **kwargs)

    def filenames(self):
        return self._archive.filenames()

    def extracted_size(self):
        return self._archive.extracted_size()


class BaseArchive(object):
    """
    Base Archive class.  Implementations should inherit this class.
    """

    def __del__(self):
        if hasattr(self, "_archive"):
            self._archive.close()

    def filenames(self):
        """
        Return a list of the filenames contained in the archive.
        """
        raise NotImplementedError()

    def extracted_size(self):
        """
        Return total file size of extracted files in bytes.
        """
        raise NotImplementedError()

    def _extract(self, to_path):
        """
        Performs the actual extraction.  Separate from 'extract' method so that
        we don't recurse when subclasses don't declare their own 'extract'
        method.
        """
        self._archive.extractall(to_path)

    def extract(self, to_path='', method='safe'):
        if method == 'safe':
            self.check_files(to_path)
        elif method == 'insecure':
            pass
        else:
            raise ValueError("Invalid method option")
        self._extract(to_path)

    def check_files(self, to_path=None):
        """
        Check that all of the files contained in the archive are within the
        target directory.
        """
        if to_path:
            target_path = os.path.normpath(os.path.realpath(to_path))
        else:
            target_path = os.getcwd()
        for filename in self.filenames():
            extract_path = os.path.join(target_path, filename)
            extract_path = os.path.normpath(os.path.realpath(extract_path))
            if not extract_path.startswith(target_path):
                raise UnsafeArchive(
                    "Archive member destination is outside the target"
                    " directory.  member: %s" % filename
                )


class TarArchive(BaseArchive):
    def __init__(self, file):
        # tarfile's open uses different parameters for file path vs. file obj.
        if isinstance(file, str):
            self._archive = tarfile.open(name=file)
        else:
            self._archive = tarfile.open(fileobj=file)

    def filenames(self):
        return [
            tarinfo.name for tarinfo in self._archive.getmembers() if tarinfo.isfile()
        ]

    def extracted_size(self):
        total = 0
        for member in self._archive:
            total += member.size
        return total

    def check_files(self, to_path=None):
        BaseArchive.check_files(self, to_path)

        for finfo in self._archive:
            if finfo.issym():
                raise UnsafeArchive("Archive contains symlink: " + finfo.name)
            if finfo.islnk():
                raise UnsafeArchive("Archive contains hardlink: " + finfo.name)


class ZipArchive(BaseArchive):
    def __init__(self, file):
        # ZipFile's 'file' parameter can be path (string) or file-like obj.
        self._archive = zipfile.ZipFile(file)

    def extracted_size(self):
        total = 0
        for member in self._archive.infolist():
            total += member.file_size
        return total

    def filenames(self):
        return [
            zipinfo.filename
            for zipinfo in self._archive.infolist()
            if not zipinfo.is_dir()
        ]


extension_map = {
    '.tar': TarArchive,
    '.tar.bz2': TarArchive,
    '.tar.gz': TarArchive,
    '.tgz': TarArchive,
    '.tz2': TarArchive,
    '.zip': ZipArchive,
}
