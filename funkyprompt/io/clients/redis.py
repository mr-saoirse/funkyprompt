import redis
import os
from pickle import loads, dumps


class RedisClient:
    def __init__(self, schema="default", table="default"):
        """
        Constructor sets up the session for a particular account and endpoint
        """
        self._schema = schema
        self._table = table
        self._db = redis.StrictRedis(
            host=os.getenv("FUNKY_REDIS_HOST", "localhost"), port=6379
        )

    def get_lock(self, key, timeout=1000):
        k = self._make_key
        return self._db.lock(key, timeout=timeout)

    def _make_key(self, key):
        return f"{self._schema}:{self._table}:{key}"

    def __getitem__(self, key):
        k = self._make_key(key)
        o = self._db.get(k)
        return loads(o) if o is not None else None

    def __setitem__(self, key, value):
        k = self._make_key(key)

        self._db.set(k, dumps(value))

    def put(self, key, value, acquire_lock=True, retrieve=False):
        if not acquire_lock:
            self[key] = value
        else:
            with self._db.lock(key, timeout=10):
                self[key] = value
        return self[key] if retrieve else True

    def update_named_map(self, name, key, value):
        """
        A shared dictionary is a useful simple object to share state in a single map
        """
        with self._db.lock(key, timeout=10):
            data = self[name] or {}
            data[key] = value
            self[name] = data

            return data

    def append_to_list(self, key, item):
        """
        acquire a lock and update a list
        """
        if not isinstance(item, list):
            item = [item]

        with self._db.lock(key, timeout=10):
            l = []
            l = self[key] or []

            l += item
            self[key] = l
            return l

    def add_to_set(self, key, item):
        """
        acquire a lock and update a set
        """
        if not isinstance(item, list):
            item = [item]

        with self._db.lock(key, timeout=10):
            l = []
            l = self[key] or []
            l += item
            self[key] = list(set(l))
            return l

    def remove_from_set_if_exists(self, key, items):
        if not isinstance(items, list):
            items = [items]

        with self._db.lock(key, timeout=10):
            l = []
            l = self[key] or []
            l = [item for item in l if item not in items]
            self[key] = list(set(l))
            return l

    def delete(self, key):
        """
        Remove a key-value pair from the Redis database using the provided key.
        """
        k = self._make_key(key)
        if self._db.exists(k):  # Check if the key exists before trying to delete
            self._db.delete(k)
