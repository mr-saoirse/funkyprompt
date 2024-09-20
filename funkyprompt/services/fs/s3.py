from pathlib import Path
import urllib
import yaml
import json
import os
from io import BytesIO
import typing
import pickle
from PIL import Image
import tarfile
from tqdm import tqdm
from glob import glob
import tempfile
import io
import pyarrow.dataset as ds
from functools import partial
from pydantic import BaseModel, model_validator
from datetime import datetime
import boto3
#maybes
import pandas as pd
import polars as pl
import pyarrow as pa


try:
    import s3fs
    import fastavro
    from cairosvg import svg2png
    from skimage.io import imread
except:
    pass


class FileLikeWritable:
    """
    wrapper around put object so it looks like a file to which you can write other stuff
    """

    def __init__(self, s3_client, bucket, key):
        self._client = s3_client
        self.bucket = bucket
        self.key = key

    def write(self, stream, **options):
        # stream = io.BytesIO()
        # stream.read(data)
        self._client.put_object(
            Bucket=self.bucket,
            Key=self.key,
            Body=stream,
        )

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        return self


class S3ObjectListing(BaseModel):
    Key: str
    LastModified: datetime
    Size: int
    bucket: str
    uri: typing.Optional[str] = None

    def __repr__(self):
        return self.uri

    @model_validator(mode="before")
    @classmethod
    def fixup(cls, data: typing.Any) -> typing.Any:
        data["uri"] = f"s3://{data['bucket']}/{data['Key']}"
        return data


def generate_presigned_url(url, expiry=3600, for_upload=False):
    """
    usually for get objects or specify put_object
    https://boto3.amazonaws.com/v1/documentation/api/latest/guide/s3-presigned-urls.html#generating-a-presigned-url-to-upload-a-file
    """
    s3 = S3Provider()
    bucket_name, object_key = s3._split_bucket_and_blob_from_path(url)

    if not s3.is_s3_uri(url):
        return url

    try:
        if for_upload:
            return s3._client.generate_presigned_url(
                "put_object",
                Params={
                    "Bucket": bucket_name,
                    "Key": object_key,
                },
                ExpiresIn=expiry,
                HttpMethod="PUT",
            )

        return s3._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket_name, "Key": object_key},
            ExpiresIn=expiry,
        )

    except Exception as ex:
        raise ex


class S3Provider:
    def __init__(self):
        self._s3fs = s3fs.S3FileSystem(version_aware=True)

        try:
            self._client = boto3.client(
                "s3",
                aws_access_key_id=os.getenv("AWS_ACCESS_KEY"),
                aws_secret_access_key=os.getenv("AWS_SECRET_KEY"),
            )
        except:
            one.logger.warn(
                f"Failed to load the s3 connector which mean the environment is not setup properly for connecting to AWS"
            )

    @staticmethod
    def is_s3_uri(uri):
        return uri[:5] == "s3://"

    def exists(self, uri: str):
        """
        check if the file or folder exists
        """
        bucket, prefix = self._split_bucket_and_blob_from_path(uri)
        if "." in uri:
            # assume file
            try:
                self._client.head_object(Bucket=bucket, Key=prefix)
                return True
            except:
                pass
        # hack for dealing with dir buckets - listings
        # TODO: how do we know when its a directory bucket
        if bucket == "MY_DIR_BUCKET_TODO--use1-az6--x-s3" and prefix[-1] != "/":
            # todo how do we know its a directory bucket (cache)
            prefix = prefix + "/"
        results = self._client.list_objects_v2(
            Prefix=prefix,
            Bucket=bucket,
        )

        return results.get("Contents") is not None

    def open(self, uri: str, mode: str = "rb", version_id: str = None):
        """
        open the file object
        **Args**
          uri: the path to the file
          mode: file mode e.g. r|rb|w|wb
          versioned_id: the s3 file object version for older object versions
        """
        if mode[0] == "r":
            return BytesIO(self.get_streaming_body(uri, version_id=version_id).read())

        bucket, key = self._split_bucket_and_blob_from_path(uri)
        return FileLikeWritable(self._client, bucket, key)

    def get_streaming_body(
        self, uri, version_id=None, before=None, after=None, at=None, **kwargs
    ):
        c = self._client
        bucket, prefix = self._split_bucket_and_blob_from_path(uri)
        try:
            if version_id or before or after or at:
                response = self.read_version(
                    uri, version_id=version_id, before=before, after=after, at=at
                )
            else:
                response = c.get_object(Bucket=bucket, Key=prefix)["Body"]
            return response
        except Exception as ex:
            raise ex

    def read_image(self, uri, version_id=None):
        """
        read as pil image
        """

        if version_id is None:
            return Image.fromarray(self.read(uri))

        bucket_name, object_key = self.split_bucket_and_blob_from_path(uri)
        response = self._client.get_object(
            Bucket=bucket_name,
            Key=object_key,
            VersionId=version_id,
        )

        return Image.open(BytesIO(response["Body"].read()))

    def read(self, uri: str, version_id=None, **options):
        """
        Read data from s3 in from different formats
        """
        dataframe_lib = pd
        if "use_polars" in options:
            if options.pop("use_polars"):
                dataframe_lib = pl

        P = Path(uri)
        if P.suffix in [".pdf"]:
            """special parser that knows things about images and page scans"""
            raise NotImplemented("Still need to add the pdf parser")
            
        if P.suffix in [".yml", ".yaml"]:
            return yaml.safe_load(
                self.get_streaming_body(uri, version_id=version_id, **options)
            )
        if P.suffix in [".json"]:
            return json.load(
                self.get_streaming_body(uri, version_id=version_id, **options)
            )
        if P.suffix in [".svg"]:
            return (
                self.get_streaming_body(uri, version_id=version_id, **options)
                .read()
                .decode()
            )
        if P.suffix in [".xls", ".xlsx"]:
            return pd.read_excel(
                uri,
                sheet_name=None,
            )

        if P.suffix in [".csv"]:
            with self.open(uri, "rb") as f:
                return dataframe_lib.read_csv(f, **options)
        if P.suffix in [".txt", ".log"]:
            return self.get_streaming_body(uri, version_id=version_id, **options).read()
        if P.suffix in [".parquet"]:
            with self.open(uri, "rb") as f:
                return dataframe_lib.read_parquet(f, **options)
        if P.suffix in [".avro"]:
            encoding = options.get("encoding", "rb")
            with self.open(uri, encoding) as f:
                if "ignore_root" in options:
                    root = options.get("ignore_root")
                    return pd.DataFrame.from_records(
                        [r[root] for r in fastavro.reader(f)]
                    )
                return pd.DataFrame.from_records([r for r in fastavro.reader(f)])
        if P.suffix in [".feather"]:
            with self.open(uri, "rb") as f:
                return dataframe_lib.read_feather(f, **options)
        # TODO: all these need to be handled
        if P.suffix in [".png", ".jpg", ".jpeg", ".tiff", ".tif"]:
            with self.open(uri, "rb") as s3f:
                with tempfile.NamedTemporaryFile(
                    suffix=".png", prefix="f", mode="wb"
                ) as f:
                    f.write(s3f.read())
                    f.flush()
                    return imread(f.name)
        if P.suffix in [".svg"]:
            with self.open(uri, "r") as f:
                return Image.open(io.BytesIO(svg2png(f.read(), **options)))

 
        if P.suffix in [".pickle"]:
            with self.open(uri, "rb") as f:
                return pickle.load(f)

        raise Exception(f"TODO: handle case for file type {uri}")

    def write(self, uri: str, data: typing.Any, **options):
        """
        A wrapper to write different file types - the mode is inferred from the extension
        """

        P = Path(uri)
        bucket, prefix = self._split_bucket_and_blob_from_path(uri)

        def write_object(writer_fn):
            stream = io.BytesIO()
            writer_fn(stream, **options)
            self._client.put_object(
                Bucket=bucket,
                Key=prefix,
                Body=stream.getvalue(),
            )

        """
        dataframe writers
        """
        if P.suffix in [".parquet"]:
            # toying with dataframe and pandas agnosticism
            if isinstance(data, pd.DataFrame):
                return write_object(data.to_parquet, **options)
            if hasattr(data, "write_parquet"):
                return write_object(data.write_parquet, **options)
            raise Exception(
                f"Can not write this type of object {type(data)} to parquet yet"
            )
        if P.suffix in [".feather"]:
            if isinstance(data, pd.DataFrame):
                return write_object(data.to_feather, **options)
            if hasattr(data, "write_pic"):
                return write_object(data.write_pic, **options)
            raise Exception(
                f"Can not write this type of object {type(data)} to feather yet"
            )
        if P.suffix in [".csv"]:
            if isinstance(data, pd.DataFrame):
                fn = partial(data.to_csv, index=False)
                return write_object(fn, **options)
            if hasattr(data, "write_csv"):
                return write_object(data.write_csv, **options)
            raise Exception(
                f"Can not write this type of object {type(data)} to csv yet"
            )

        if P.suffix in [".pickle"]:
            with self.open(uri, "wb") as f:
                fn = partial(pickle.dump, data)
                return write_object(fn, **options)
        if P.suffix in [".jpg", ".jpeg", ".tiff", "tif", ".png"]:
            format = P.suffix[1:]  # this will not always work so we can test cases
            _data = BytesIO()
            if not isinstance(data, Image.Image):
                data = Image.fromarray(data)
            options = {"format": format, **options}
            if "dpi" in options:
                options["dpi"] = options.get("dpi")
                if isinstance(options["dpi"], int):
                    options["dpi"] = (options["dpi"], options["dpi"])

            # return write_object(data.save, **options)
            data.save(_data, **options)
            data = _data.getvalue()
            return self._client.put_object(Bucket=bucket, Key=prefix, Body=data)

        if P.suffix in [".pdf"]:
            return self._client.put_object(
                Bucket=bucket, Key=prefix, Body=data, ContentType="application/pdf"
            )

        if isinstance(data, dict):
            if P.suffix in [".yml", ".yaml"]:
                data = yaml.safe_dump(data)
            if P.suffix in [".json"]:
                data = json.dumps(data)

        return self._client.put_object(Bucket=bucket, Key=prefix, Body=data)

    def copy(self, uri_from: str, uri_to: str):
        """
        Copy files from s3->s3, local->s3, s3->local depending on the format
        """
        if S3Provider.is_s3_uri(uri_to) and not S3Provider.is_s3_uri(uri_from):
            bucket, path = self._split_bucket_and_blob_from_path(uri_to)
            self._client.upload_file(uri_from, bucket, path)
        elif not S3Provider.is_s3_uri(uri_to) and S3Provider.is_s3_uri(uri_from):
            bucket, path = self._split_bucket_and_blob_from_path(uri_from)
            meta_data = self._client.head_object(Bucket=bucket, Key=path)
            total_length = int(meta_data.get("ContentLength", 0))
            with tqdm(
                total=total_length,
                desc=f"source:{uri_from}",
                bar_format="{percentage:.1f}%|{bar:25} | {rate_fmt} | {desc}",
                unit="B",
                unit_scale=True,
                unit_divisor=1024,
            ) as pbar:
                with open(uri_to, "wb") as f:
                    self._client.download_fileobj(bucket, path, f, Callback=pbar.update)

        elif S3Provider.is_s3_uri(uri_to) and S3Provider.is_s3_uri(uri_from):
            with self.open(uri_from) as from_obj:
                with self.open(uri_to, "wb") as to_obj:
                    to_obj.write(from_obj.read())
        else:
            raise Exception(f"Either one of uri_from or uri_to should be an s3 path")

    def upload_folder_to_archive(self, folder, target_folder, archive_name=None):
        """
        packs a folder to an archive - this mode assumes something is local for now since that is the most likely thing
        but we could support the other thing to
        """

        archive_name = archive_name or folder.rstrip("/").split("/")[-1]
        tar_file_name = f"/tmp/{archive_name}.tar.gz"
        with tarfile.open(tar_file_name, "w:gz") as tar:
            for name in tqdm(glob(f"{folder}/**/*.*", recursive=True)):
                p = Path(name)
                class_item = p.relative_to(folder)
                tar.add(name, arcname=f"{archive_name}/{class_item}")

        self.upload(tar_file_name, f"{target_folder}/{Path(tar_file_name).name}")

    def rename(self, source: str, target: str):
        """
        file rename
        """
        return self._s3fs.rename(source, target)

    def cache_data(
        self,
        data: typing.Any,
        cache_location="s3://res-data-platform/cache",
        suffix=None,
        **kwargs,
    ):
        """you must pass a suffix or file name"""
        if isinstance(data, Image.Image):
            if "uri" in kwargs:
                return kwargs.get("uri")
            suffix = ".png"  # infer
            uri = f"{cache_location}/images/{one.utils.res_hash()}{suffix}"
            self.write(uri, data)
            return uri

        raise NotImplementedError(
            f"We typically cache images - to cache other types such as {type(data)} - implement it in the fs service"
        )

    def ls(self, uri, file_type="*", search=f"**/", **kwargs) -> typing.List[str]:
        r = self.glob(uri, file_type=file_type, search=search, **kwargs)
        return [i.uri for i in r]

    def glob(
        self, uri, file_type="*", search=f"**/", **kwargs
    ) -> typing.List[S3ObjectListing]:
        """
        deep listing
        """
        # file_type = f"*.{file_type}" if file_type else None
        # search = f"{uri}/{search}{file_type}"
        # results = [f"s3://{f}" for f in s3fs.S3FileSystem().glob(search)]
        # return results

        bucket, prefix = self._split_bucket_and_blob_from_path(uri)
        # hack for dealing with dir buckets
        if bucket == "one-ai--use1-az6--x-s3" and prefix[-1] != "/":
            # todo how do we know its a directory bucket (cache)
            prefix = prefix + "/"
        results = self._client.list_objects_v2(
            Prefix=prefix,
            Bucket=bucket,
        )
        contents = results.get("Contents")
        if not contents:
            return []

        return [S3ObjectListing(**d, bucket=bucket) for d in contents]

    def ls_dirs(self, uri, max_keys=100):
        """
        List the first directories under the root
        """
        bucket, key = self._split_bucket_and_blob_from_path(uri)
        key = f"{key.rstrip('/')}/"
        response = self._client.list_objects_v2(
            Bucket=bucket, Prefix=key, Delimiter="/", MaxKeys=max_keys
        )
        dirs = [
            p["Prefix"].rstrip("/").split("/")[-1] for p in response["CommonPrefixes"]
        ]
        dirs = [f"{uri}/{p}" for p in dirs]

        return dirs

    def ls_iter(self, uri: str, **options):
        pass

    def _delete(self, uri: str, limit: int = 100):
        pass

    def _check_uri(self, uri: str):
        """
        makes sure the uri is an s3 uri in the right format
        """
        url = urllib.parse.urlparse(uri)
        assert (
            url.scheme == "s3"
        ), f"The url must be of the form s3://BUCKET/path/to/file/ext but got {uri} with scheme {url.scheme}"

    def _split_bucket_and_blob_from_path(self, uri: str):
        """
        splits the s3://bucket/path into bucket and path
        """
        self._check_uri(uri)
        url = urllib.parse.urlparse(uri)
        return url.netloc, url.path.lstrip("/")

    def read_dataset(self, uri) -> pa.dataset.Dataset:
        """
        return an arrow dataset - todo check lazy loading etc

        useful also for S3 Express use cases

        one.fs.read_dataset('s3://one-ai--use1-az6--x-s3/test/missing_style_id_line_items.parquet')
        """
        with one.fs.open(uri, mode="rb") as f:
            return pl.read_parquet(f).to_arrow()

        # format = uri.split(".")[-1]
        # return ds.dataset(uri, filesystem=s3fs.S3FileSystem(), format=format)

    def delete(self, uri: str, limit=50) -> typing.List[str]:
        """
        deletes fle or directory
        """
        _s3 = boto3.resource("s3")
        # TODO: this this for single files
        deleted_files = self.ls(uri)
        if len(deleted_files) > limit:
            raise Exception(
                f"Trying to delete more than {limit} files is not permitted because it would be too easy to wipe the bucket"
            )
        for file in deleted_files:
            one.logger.debug(f"Deleting {file}")
            _s3.Object(*self._split_bucket_and_blob_from_path(file)).delete()
        # remove the now empty folder
        one.logger.debug(f"Deleting {uri}")
        _s3.Object(*self._split_bucket_and_blob_from_path(uri)).delete()

        return deleted_files

    def apply(self, uri: str, fn: typing.Callable):
        """apply an op to a file like object"""

        with self.open(uri, "rb") as s3f:
            # write to a temporary local file
            with tempfile.NamedTemporaryFile(
                suffix=f".{uri.split('.')[-1]}", prefix="file", mode="wb"
            ) as f:
                f.write(s3f.read())
                f.flush()
                # return the context manager
                return fn(f.name)
