"""
file system tools - S3 or local
"""

import typing
from pydantic import Field, BaseModel
import polars as pl
import s3fs
import pyarrow.dataset as ds
from functools import partial
from pathlib import Path


class FileData(BaseModel):
    name: str
    content: str
    namespace: str = Field(default="default")


class FileCollection(BaseModel):
    files: typing.List[FileData]

    def __iter__(self):
        for f in self.files:
            yield f


def get_filesystem(uri):
    fs = None if uri[:5] != "s3://" else s3fs.S3FileSystem()
    return fs  # if none we could return something like an interface


def _get_writer(df, uri=None):
    """
    the writer is determined from the uri and defaults to parquet
    """
    # TODO generalize / assume parquet for now for our usecase
    return partial(df.write_parquet)


def read_dataset(uri) -> ds.Dataset:
    fs = None if uri[:5] != "s3://" else s3fs.S3FileSystem()
    # we choose to infer the format
    format = uri.split(".")[-1]
    return ds.dataset(uri, filesystem=fs, format=format)


def exists(uri):
    fs = None if uri[:5] != "s3://" else s3fs.S3FileSystem()
    if fs:
        return fs.exists(uri)

    return Path(uri).exists()


def ls(root, file_type="*", search=f"**/", **kwargs):
    """
    deep listing
    """
    file_type = f"*.{file_type}" if file_type else None
    search = f"{root}/{search}{file_type}"
    results = [f"s3://{f}" for f in s3fs.S3FileSystem().glob(search)]
    return results


def glob(pattern, **kwargs):
    return s3fs.S3FileSystem().glob(pattern, **kwargs)


def read(uri, lazy=False) -> pl.DataFrame:
    """
    read data to polar data
    """
    dataset = read_dataset(uri)
    if lazy:
        return pl.scan_pyarrow_dataset(dataset)

    return pl.from_arrow(dataset.to_table())


def get_query_context(uri, name):
    """
    get the polar query context from polars
    """
    ctx = pl.SQLContext()
    ctx.register(name, read(uri, lazy=True))
    return ctx


def read_if_exists(uri, **kwargs):
    # TODO: add some s3 clients stuff
    try:
        # fs = get_filesystem()
        # if fs and not fs.exists(uri):
        #     return None
        return read(uri=uri, **kwargs)
    except:
        return None


def write(uri, data: typing.Union[pl.DataFrame, typing.List[dict]]):
    """
    write data from polar data to format=parquet
    """
    if not isinstance(data, pl.DataFrame):
        # assume the data are dicts or pydantic objects
        data = pl.DataFrame([d.dict() if hasattr(d, "dict") else d for d in data])

    fs = None if uri[:5] != "s3://" else s3fs.S3FileSystem()

    fn = _get_writer(data, uri)
    if fs:
        with fs.open(uri, "wb") as f:
            fn(f)
    else:
        # create director
        Path(uri).parent.mkdir(exist_ok=True, parents=True)
        fn(uri)

    return read_dataset(uri)


def merge(
    uri: str, data: typing.Union[pl.DataFrame, typing.List[dict]], key: str
) -> ds.Dataset:
    """
    merge data from polar data using key

    """
    existing = read_if_exists(uri)

    if isinstance(data, list):
        # assume the data are dicts or pydantic objects
        data = pl.DataFrame([d.dict() if hasattr(d, "dict") else d for d in data])
    if not isinstance(data, pl.DataFrame):
        raise Exception(
            "Only list of dicts and polar dataframes are supported - what did you pass in?"
        )
    if existing is not None:
        data = pl.concat([existing, data])

    write(uri, data.unique(subset=[key], keep="last"))

    return read_dataset(uri)


def typed_record_reader(uri, entity_type, lazy=False):
    """
    im not sure how to lazily do this but we will look into it or chunk perhaps
    """
    df = read(uri, lazy=lazy)
    for record in df.rows(named=True):
        yield (entity_type(**record))


def save_file_collection(files: FileCollection):
    """
    given a list of files, save 1 or more files from the collection to disk

    **Params**
        files: The file collection to save

    **Returns**
        We return information on the persons favourite thing

    **Raises**
        Exception

    """
    print("IN FUNC")
    # some resilience - seems to alternative quite a bit on this. need to study
    if isinstance(files, list):
        files = {"files": files}
    for file in FileCollection(**files):
        print(file.name)
        with open(f"/Users/sirsh/Downloads/{file.name}", "w") as f:
            f.write(file.content)

    return "DONE"


def save_type(code_str, namespace="default", add_crud_ops=True):
    """
    Save a type which is a pydantic class under the modules_home/namespace/
    the Crud is a RAG op set for getting columnar and vector data
    we can use conventions to generate ops that load the given stores to retrieve typed objects for use in agent systems
    those methods can be extended e.g. to load data from other subscriptions
    """

    # exceptions for parsing errors
    my_type = eval(code_str)

    path = my_type.get_path()

    with open(path, "w") as f:
        f.write(code_str)


def load_type(entity_name, namespace="default"):
    """
    the entity name can be fully qualified in which case we ignore the namespace, otherwise we qualify with passed namespace
    module_home/namespace/entity
    """
    pass


def _save_sample_file_to_home(code, file, folder=None):
    """
    When testing file generation its useful to save output files to the home directory for caching or inspecting

    **Args**
        code: the actual code e.g. python code
        file: the name of the file e.g. file.python
        folder: a sub folder to organize data into
    """

    out_dir = f"{Path.home()}/.funkyprompt"
    if folder:
        out_dir = f"{out_dir}/{folder}"
    out_file = f"{out_dir}/{file}"
    Path(out_dir).mkdir(exist_ok=True, parents=True)
    with open(out_file, "w") as f:
        f.write(code)
