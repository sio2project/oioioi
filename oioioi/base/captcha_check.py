import os
import subprocess
import warnings

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

FNULL = subprocess.DEVNULL


class CaptchaAudioWarning(Warning):
    pass


def _check_executable(setting_name, path, expected_code=0):
    if not os.path.isfile(path):
        raise ImproperlyConfigured(f"{setting_name}: {path} is not a valid path.")
    else:
        code = subprocess.call([path, "--version"], stdout=FNULL, stderr=FNULL, stdin=FNULL)
        if code != expected_code:
            raise ImproperlyConfigured(f"{setting_name}: failed to execute {path}, exit code {code}")


def captcha_check():
    flite_path = getattr(settings, "CAPTCHA_FLITE_PATH", None)
    sox_path = getattr(settings, "CAPTCHA_SOX_PATH", None)

    if flite_path is None:
        warnings.warn(
            "Audio playback of captcha is turned off, because no flite executable was found in PATH, and CAPTCHA_FLITE_PATH was not set to any path",
            CaptchaAudioWarning,
            stacklevel=2,
        )
        # We have no need for further checking if flite is not installed.
        return
    else:
        _check_executable("CAPTCHA_FLITE_PATH", flite_path, expected_code=1)

    if sox_path is None:
        warnings.warn(
            "Audio playback of captcha is not secure, because sox executable was not found in PATH, and CAPTCHA_SOX_PATH was not set to any path",
            CaptchaAudioWarning,
            stacklevel=2,
        )
    else:
        _check_executable("CAPTCHA_SOX_PATH", sox_path)
