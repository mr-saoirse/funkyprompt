from funkyprompt.io.stores import AbstractStore
from funkyprompt.model import AbstractModel
import typing
from tqdm import tqdm
from funkyprompt.io.clients.redis import RedisClient


def EntityDataStoreAny():
    """
    entity agnostic interface
    """
    return EntityDataStore(None, None)


class EntityDataStore(AbstractStore):
    def __init__(
        self,
        model: AbstractModel,
        alias: str = None,
        description: str = None,
    ):
        super().__init__(model=model, alias=alias, description=description)

        try:
            # in certain cases this is enabled
            self._db = RedisClient()
        except:
            pass  # silent

    @property
    def entity_name(self):
        return self._entity_name

    def insert_row(self, d, key, etype=None, **options):
        # extract they key
        if hasattr(d, "dict"):
            d = d.dict()
        key = d[key]
        d[".entity_type"] = etype
        # this is so we can have multiple mappings to the same key for disambiguation
        existing = self._db[key] or {}
        existing[etype] = d
        if len(existing) > 1:
            d[
                "hint"
            ] = f"There are multiple entities with the same name key {key} so you should infer the appropriate type"
        self._db.put(key, existing)
        return d

    def upsert_row(self, d, key, etype=None, **options):
        if hasattr(d, "dict"):
            d = d.dict()
        # extract they key
        key = d[key]
        d_old = self._db[key] or {}
        d_old.update(d)
        self.insert_row(d, d_old, etype=etype)
        return d

    def add(self, records: typing.List[typing.Union[AbstractModel, dict]], key):
        """
        Loads entities as dicts or types. A useful way to get typed entities is to read them from another store eg.

        store = ColumnarDataStore.open(name='style', namespace='meta')
        Model = store.entity
        estore = EntityDataStore(store.entity)
        estore.add(<records>)

        You can read entities generically with
        store = EntityDataStore(AbstractEntity)
        store[KEY]

        This will return a typed map or a map of maps for each entity
        a map of maps is sued simply to accommodate key collisions over types

        """
        assert (
            self._entity_name
        ), "You cannot use the add function without specifying the entity name and namespace in the constructor"

        if not isinstance(records, list):
            records = [records]

        records = [getattr(r, "dict", r) for r in records]
        records = [r for r in records if len(r)]

        if key is None:
            key = self._key_field

        for record in tqdm(records):
            self.insert_row(
                record, key=key, etype=f"{self._entity_namespace}.{self._entity_name}"
            )

    def __getitem__(self, key):
        added = None

        value = self._db[key]
        if value:
            etype = value.get(".entity_type")
            if added:
                if etype:
                    ac = EntityDataStore.ENTITY_CONTEXT.get(etype.lower())
                    if ac:
                        added = added + ac
                value[".context"] = added
            # principle of no dead ends
            # value["help"] = "use the stats tool to find out more"

        return value

    def run_search(self, keys: typing.List[str]):
        """
        use this function when you need to lookup entity attributes or find out more about some codes, skus, names or identifiers
        Do not use this tool to answer questions of a statistical nature.
        You should pass a comma separated list or a string list of known or suspected entities

        **Args**
            keys: a command separated list of keys or a collection of keys
        """

        help_text = f"""If you have a function specifically related to this entity use the ColumnarDataStore functions or if you do not find results with that you could try various vector store searches
            for arbitrary longer form questions about entities."""

        keys = keys.split(",") if not isinstance(keys, list) else keys
        # do some key cleansing
        # TODO figure out what the regex is to do this safely for identifiers - this is a crude way as we experience cases
        # Tests for new lines and quotes etc in the thing or stuff at the ends that is not simple chars
        keys = [k.rstrip("\n").lstrip().rstrip().strip('"').strip("'") for k in keys]
        # the store may internal try and add something to the map
        # for example if we pass in A B C D it may lookup A B C and add D in the result but map context from ABC
        # note we omit adding null responses!!
        d = {k: self[k] for k in keys if self[k]}
        d["help"] = help_text
        return d

    def __call__(self, *args: typing.Any, **kwargs: typing.Any) -> typing.Any:
        return self.run_search(*args, **kwargs)
