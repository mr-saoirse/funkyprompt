import datetime
from datetime import timezone


def now():
    return datetime.datetime.now(tz=None)


def utc_now():
    return datetime.datetime.now(tz=timezone.utc)
