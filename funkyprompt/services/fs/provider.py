"""
A simpler s3 and file system interface. read, write, ls, copy and basic file system operations are supported
for example we dont have upload or download since the copy format is used instead e..g copy rom file:/// to s3:///
we dont have zip or unzip since the format of copying to an archive is supported

"""

from funkyprompt.services.fs.s3 import S3Provider
import polars as pl
import pyarrow.dataset as ds
from PIL import Image
from pathlib import Path
import io
import typing
import requests


def is_s3(uri):
    return uri[:5] == "s3://"


def is_archive(uri):
    return ".zip" in uri.lower() or ".tar" in uri.lower() or ".gz" in uri.lower()


class FS:
    """
    entry point to file systems to abstract away from local or S3 - all methods may not yet be implemented as we normally use S3
    """

    def https_to_file(self, web_request_uri, target_uri, token=None):
        """
        if we have a remote resource we can write it to a file in our file system e.g.
        - download airtable or slack files to s3
        """
        response = (
            requests.get(web_request_uri)
            if not token
            else requests.get(
                web_request_uri, headers={"Authorization": "Bearer %s" % token}
            )
        )

        with self.open(target_uri, "wb") as f:
            f.write(response.content)

    def open(self, uri: str, mode: str):
        """
        open files for read or write on the filesystem
        """
        if is_s3(uri):
            return S3Provider().open(uri, mode=mode)
        else:
            return open(uri, mode)

    def exists(self, uri):
        """
        check if file or folder exists on the file system
        """
        if is_s3(uri):
            return S3Provider().exists(uri)

        return Path(uri).exists()

    def read(self, uri: str, **options):
        """
        read any data type - extensions are used to determine the reader
        """

        if is_s3(uri):
            return S3Provider().read(uri, **options)

        from cairosvg import svg2png

        P = Path(uri)
        with open(uri, mode=options.get("mode", "r")) as f:
            if P.suffix in [".svg"]:
                return Image.open(io.BytesIO(svg2png(f.read(), **options)))

        # check extensions - svg example

    def write(self, uri, data, **options):
        """
        write any data type - extensions are used to determine the writer
        """
        if is_s3(uri):
            return S3Provider().write(uri, data, **options)

    def copy(self, uri_from: str, uri_to: str):
        """
        overloaded copy between file systems and locations
        """
        if is_s3(uri_from) and is_s3(uri_to):
            return S3Provider().copy(uri_from, uri_to)
        if not is_s3(uri_from) and not is_s3(uri_to):
            raise Exception(f"Not handled mode {uri_from} -> {uri_to}")
        if is_s3(uri_from) and not is_s3(uri_to):
            # s3 handles download
            return S3Provider().copy(uri_from, uri_to)
        if not is_s3(uri_from) and is_s3(uri_to):
            # s3 handles upload
            return S3Provider().copy(uri_from, uri_to)

        raise Exception(f"Not handled mode {uri_from} -> {uri_to}")

    def cache_data(self, data: typing.Any, **kwargs):
        """
        cache data is assumed to be on s3
        """
        return S3Provider().cache_data(data, **kwargs)

    def ls(self, uri: str, **options):
        """
        list files from a prefix `uri`. To look at immediate children use `ls_dirs`
        """
        if is_s3(uri):
            return S3Provider().ls(uri, **options)

    def ls_dirs(self, uri: str, **options):
        """
        list the directories that are child to the prefix `uri`
        """
        if is_s3(uri):
            return S3Provider().ls_dirs(uri, **options)

    def ls_iter(self, uri: str, **options):
        """
        for paginated use cases (TODO:)
        """
        if is_s3(uri):
            for item in S3Provider().ls_iter(uri, **options):
                yield item

    def delete(self, uri: str, limit=100):
        """
        delete objects in a folder/dir - a safety `limit` is used
        this can be used to delete files or directory contents
        """
        if is_s3(uri):
            return S3Provider().delete(uri, limit=limit)

    def read_dataset(self, uri) -> ds.Dataset:
        """
        read data such as parquet files as a pyarrow dataset
        """
        if is_s3(uri):
            return S3Provider().read_dataset(uri)

    def read_image(self, uri) -> Image:
        """
        read image as a PIL image
        """
        if is_s3(uri):
            return S3Provider().read_image(uri)

        return Image.open(uri)

    def apply(self, uri: str, fn: typing.Callable):
        """apply an op to a file like object"""
        if is_s3(uri):
            return S3Provider().apply(uri, fn)

    def local_file(self, uri):
        if is_s3(uri):
            filename = Path(uri).name
            filename = f"/tmp/{filename}"
            S3Provider().copy(uri, filename)
            return filename
        return uri
