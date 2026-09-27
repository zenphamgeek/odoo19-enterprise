# Part of Insilos. See LICENSE file for full copyright and licensing details.
import logging
import os
import re
from urllib.parse import unquote, quote

from odoo import api, models
from odoo.exceptions import ValidationError

from ..utils.cloud_storage_s3_utils import get_s3_client

_logger = logging.getLogger(__name__)


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'
    # path-style URL: {endpoint_url}/{bucket_name}/{key}
    _cloud_storage_s3_url_pattern = re.compile(r'^(?P<endpoint_url>https?://[^/]+)/(?P<bucket_name>[^/]+)/(?P<blob_name>[^?]+)$')

    def _get_cloud_storage_s3_info(self):
        match = self._cloud_storage_s3_url_pattern.fullmatch(self.url or '')
        if not match:
            raise ValidationError(self.env._('%s is not a valid S3 URL.', self.url))
        return {
            'endpoint_url': match['endpoint_url'],
            'bucket_name': match['bucket_name'],
            'blob_name': unquote(match['blob_name']),
        }

    def _generate_cloud_storage_s3_url(self, blob_name):
        ICP = self.env['ir.config_parameter'].sudo()
        endpoint_url = ICP.get_param('cloud_storage_s3_endpoint_url')
        bucket_name = ICP.get_param('cloud_storage_s3_bucket_name')
        return f"{endpoint_url}/{bucket_name}/{quote(blob_name)}"

    def _get_cloud_storage_s3_client(self):
        return self.env['res.config.settings']._get_cloud_storage_s3_client()

    # OVERRIDES
    def _generate_cloud_storage_url(self):
        if self.env['ir.config_parameter'].sudo().get_param('cloud_storage_provider') != 's3':
            return super()._generate_cloud_storage_url()
        blob_name = self._generate_cloud_storage_blob_name()
        return self._generate_cloud_storage_s3_url(blob_name)

    def _generate_cloud_storage_download_info(self):
        if self.env['ir.config_parameter'].sudo().get_param('cloud_storage_provider') != 's3':
            return super()._generate_cloud_storage_download_info()
        info = self._get_cloud_storage_s3_info()
        client = self._get_cloud_storage_s3_client()
        params = {'Bucket': info['bucket_name'], 'Key': info['blob_name']}
        if self.mimetype:
            params['ResponseContentType'] = self.mimetype
        url = client.generate_presigned_url(
            'get_object', Params=params,
            ExpiresIn=self._cloud_storage_download_url_time_to_expiry,
        )
        return {
            'url': url,
            'time_to_expiry': self._cloud_storage_download_url_time_to_expiry,
        }

    def _generate_cloud_storage_upload_info(self):
        if self.env['ir.config_parameter'].sudo().get_param('cloud_storage_provider') != 's3':
            return super()._generate_cloud_storage_upload_info()
        info = self._get_cloud_storage_s3_info()
        client = self._get_cloud_storage_s3_client()
        params = {'Bucket': info['bucket_name'], 'Key': info['blob_name']}
        headers = {}
        if self.mimetype:
            params['ContentType'] = self.mimetype
            headers['Content-Type'] = self.mimetype
        url = client.generate_presigned_url(
            'put_object', Params=params,
            ExpiresIn=self._cloud_storage_upload_url_time_to_expiry,
        )
        return {
            'url': url,
            'method': 'PUT',
            'headers': headers,
            'response_status': 200,
        }

    # ── Filestore mirror (fix cross-pod filestore sharing) ──────────
    # ponytail: cluster K8s không có storage RWX (Longhorn đã gỡ), mỗi pod
    # ghi filestore local riêng (ir_attachment.store_fname trỏ file chỉ tồn
    # tại ở 1 pod cụ thể). Round-robin sang pod khác chưa từng ghi file đó
    # -> FileNotFoundError -> HTTP 500 (đặc biệt với asset bundle CSS/JS,
    # không đi qua cơ chế cloud_storage upload thông thường vì do server tự
    # compile, không qua composer/upload widget).
    # Giải pháp: mirror MỌI file filestore (kể cả asset bundle) lên S3 khi
    # ghi, và tự heal (tải lại từ S3) khi đọc mà file local bị thiếu.
    # Ceiling: thêm 1 network call mỗi lần ghi/miss-read; không xoá bản mirror
    # trên S3 khi file bị GC local (chấp nhận rác nhỏ, dọn định kỳ nếu cần).
    # Upgrade path: NFS/S3-backed filestore thật (fuse mount) nếu traffic lớn.
    def _cloud_storage_s3_mirror_enabled(self):
        return self.env['ir.config_parameter'].sudo().get_param('cloud_storage_provider') == 's3'

    @api.model
    def _file_write(self, *args, **kwargs):
        res = super()._file_write(*args, **kwargs)
        if self._cloud_storage_s3_mirror_enabled():
            fname = args[0] if args and isinstance(args[0], str) else kwargs.get('fname')
            bin_value = args[1] if len(args) > 1 else kwargs.get('bin_value')
            if fname and bin_value:
                self._cloud_storage_s3_mirror_upload(fname, bin_value)
        return res

    def _file_read(self, *args, **kwargs):
        if not args and not kwargs:
            # Odoo 20 signature: _file_read(self) -> BinaryValue
            data = super()._file_read()
            if not data and self.store_fname and self._cloud_storage_s3_mirror_enabled():
                data = self._cloud_storage_s3_mirror_download(self.store_fname)
            return data
        # Fallback for legacy signature: _file_read(self, fname, size=None)
        fname = args[0] if args else kwargs.get('fname')
        size = args[1] if len(args) > 1 else kwargs.get('size')
        data = super()._file_read(fname, size=size)
        if not data and fname and self._cloud_storage_s3_mirror_enabled():
            data = self._cloud_storage_s3_mirror_download(fname)
        return data

    def _cloud_storage_s3_mirror_client_bucket(self):
        config = self.env['res.config.settings']._get_cloud_storage_configuration()
        if not config:
            return None, None
        return get_s3_client(**config), config['bucket_name']

    def _cloud_storage_s3_mirror_upload(self, fname, bin_value):
        try:
            client, bucket = self._cloud_storage_s3_mirror_client_bucket()
            if not client:
                return
            client.put_object(Bucket=bucket, Key=f'filestore-mirror/{fname}', Body=bin_value)
        except Exception:
            _logger.warning("cloud_storage_s3: failed to mirror-upload %s", fname, exc_info=True)

    def _cloud_storage_s3_mirror_download(self, fname):
        try:
            client, bucket = self._cloud_storage_s3_mirror_client_bucket()
            if not client:
                return b''
            obj = client.get_object(Bucket=bucket, Key=f'filestore-mirror/{fname}')
            data = obj['Body'].read()
            # tự heal: ghi lại vào local filestore cho pod hiện tại để lần sau đọc nhanh
            full_path = self._full_path(fname)
            try:
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                with open(full_path, 'wb') as fp:
                    fp.write(data)
            except OSError:
                _logger.info("cloud_storage_s3: could not heal local copy of %s", fname, exc_info=True)
            return data
        except Exception:
            _logger.warning("cloud_storage_s3: failed to mirror-download %s", fname, exc_info=True)
            return b''
