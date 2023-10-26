"""
deployment attributes
"""


def attributes(
    memory=None,
    sem_var=None,
    cron=None,
    on_error=None,
    interval_minutes=None,
    interval_hours=None,
    namespace=None,
):
    def _adorned(func):
        func.meta = {
            "memory": memory,
            "sem_var": sem_var,
            "memory": memory,
            "cron": cron,
            "interval_minutes": interval_minutes,
            "interval_hours": interval_hours,
            "namespace": namespace,
        }
        return func

    return _adorned
