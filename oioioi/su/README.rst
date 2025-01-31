An option for admins to log in as other user
for testing purposes.

You can enable su for contest admins with ``CONTEST_ADMINS_CAN_SU`` option set to ``True`` in ``settings.py``. By default
this option is disabled. You can allow contest admins using su to make other request than `GET` by setting
``ALLOW_ONLY_GET_FOR_SU_CONTEST_ADMINS`` to ``True`` (default ``False``).
