import io
import logging
import string
import random

from minio import Minio
from minio.error import NoSuchKey, NoSuchBucket


def generate_secure_random(size, chars=string.ascii_uppercase + string.ascii_lowercase + string.digits):
    return ''.join(random.SystemRandom().choice(chars) for _ in range(size))


class MinIOClient(Minio):
    def __init__(self, endpoint, access_key, secret_key, secure, **kwargs):
        super().__init__(endpoint=endpoint,
                         access_key=access_key,
                         secret_key=secret_key,
                         secure=secure,
                         **kwargs)
        self.logger = logging.getLogger(self.__class__.__name__)

    def upload_object(self, bucket_name, object_name, data, data_type):
        _data = None
        _data_length = None

        if data_type == 'str':
            data_bytes = data.encode('utf-8')

            _data = io.BytesIO(data_bytes)
            _data_length = len(data_bytes)

        metadata = {
            'X-Amz-Meta-Data-Type': data_type,
            'X-Amz-Meta-Source': 'elastalert'
        }

        if _data:
            try:
                self.put_object(bucket_name=bucket_name,
                                object_name=object_name,
                                data=_data,
                                length=_data_length,
                                metadata=metadata)
            except Exception as e:
                self.logger.error(f"Error uploading data to MinIO: {e}")
            else:
                return True
        return False

    def upload_random_object(self, bucket_name, data, data_type):
        object_name = None

        valid = False
        while not valid:
            object_name = generate_secure_random(128)
            valid = not self.object_exists(bucket_name=bucket_name, object_name=object_name)

        if self.upload_object(bucket_name=bucket_name,
                              object_name=object_name,
                              data=data,
                              data_type=data_type):
            return object_name
        return None

    def download_object(self, bucket_name, object_name):
        try:
            raw_object = self.get_object(bucket_name=bucket_name, object_name=object_name)
            raw_metadata = self.stat_object(bucket_name=bucket_name, object_name=object_name)
        except Exception as e:
            self.logger.error(f"Error retrieving object from MinIO: {e}")
        else:
            object_metadata = raw_metadata.get('metadata')

            if object_metadata:
                object_data = None

                data_type = object_metadata['X-Amz-Meta-Data-Type']
                if data_type == 'str':
                    object_data = raw_object.data.decode('utf-8')

                return object_data, object_metadata
        return None

    def object_exists(self, bucket_name, object_name):
        try:
            self.stat_object(bucket_name=bucket_name, object_name=object_name)
        except (NoSuchKey, NoSuchBucket):
            return False
        else:
            return True
