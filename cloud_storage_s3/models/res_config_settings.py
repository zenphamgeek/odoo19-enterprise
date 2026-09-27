# Part of Insilos. See LICENSE file for full copyright and licensing details.
from odoo import api, models, fields, _
from odoo.exceptions import ValidationError, UserError

from ..utils.cloud_storage_s3_utils import get_s3_client


class ResConfigSettings(models.TransientModel):
    """
    Instructions:
    cloud_storage_s3_endpoint_url, cloud_storage_s3_bucket_name: if changed
        and old bucket is still in use, the new credentials must keep access
        to the old bucket too.
    Works with any S3-compatible provider (MinIO, AWS S3, ...) via boto3.
    """
    _inherit = 'res.config.settings'

    cloud_storage_provider = fields.Selection(selection_add=[('s3', 'S3 Cloud Storage')])

    cloud_storage_s3_endpoint_url = fields.Char(
        string='S3 Endpoint URL',
        config_parameter='cloud_storage_s3_endpoint_url',
        help='e.g. https://s3.iz.io.vn')
    cloud_storage_s3_bucket_name = fields.Char(
        string='S3 Bucket Name',
        config_parameter='cloud_storage_s3_bucket_name')
    cloud_storage_s3_access_key = fields.Char(
        string='S3 Access Key',
        config_parameter='cloud_storage_s3_access_key')
    cloud_storage_s3_secret_key = fields.Char(
        string='S3 Secret Key',
        config_parameter='cloud_storage_s3_secret_key')
    cloud_storage_s3_region = fields.Char(
        string='S3 Region',
        config_parameter='cloud_storage_s3_region',
        help='Leave empty for MinIO / providers without region concept.')

    def _get_cloud_storage_configuration(self):
        ICP = self.env['ir.config_parameter'].sudo()
        if ICP.get_param('cloud_storage_provider') != 's3':
            return super()._get_cloud_storage_configuration()
        configuration = {
            'endpoint_url': ICP.get_param('cloud_storage_s3_endpoint_url'),
            'bucket_name': ICP.get_param('cloud_storage_s3_bucket_name'),
            'access_key': ICP.get_param('cloud_storage_s3_access_key'),
            'secret_key': ICP.get_param('cloud_storage_s3_secret_key'),
        }
        if not all(configuration.values()):
            return {}
        configuration['region'] = ICP.get_param('cloud_storage_s3_region') or None
        return configuration

    @api.model
    def _get_cloud_storage_s3_client(self):
        config = self._get_cloud_storage_configuration()
        if not config:
            raise UserError(_('Please configure the S3 Cloud Storage before enabling it'))
        return get_s3_client(**config)

    def _setup_cloud_storage_provider(self):
        ICP = self.env['ir.config_parameter'].sudo()
        if ICP.get_param('cloud_storage_provider') != 's3':
            return super()._setup_cloud_storage_provider()
        config = self._get_cloud_storage_configuration()
        client = get_s3_client(**config)
        bucket = config['bucket_name']
        key = f'0/insilos-setup-check.txt'
        try:
            client.put_object(Bucket=bucket, Key=key, Body=b'insilos setup check')
            client.get_object(Bucket=bucket, Key=key)
            client.delete_object(Bucket=bucket, Key=key)
        except Exception as e:
            raise ValidationError(_('The S3 credentials do not have read/write access to the bucket.\n%s', str(e)))

    def _check_cloud_storage_uninstallable(self):
        if self.env['ir.config_parameter'].get_param('cloud_storage_provider') != 's3':
            return super()._check_cloud_storage_uninstallable()
        cr = self.env.cr
        cr.execute(
            """
                SELECT 1
                FROM ir_attachment
                WHERE type = 'cloud_storage'
                AND url LIKE %s
                LIMIT 1
            """,
            (f"{self.cloud_storage_s3_endpoint_url}/{self.cloud_storage_s3_bucket_name}/%",),
        )
        if cr.fetchone():
            raise UserError(_('Some S3 attachments are in use, please migrate their cloud storages before disable this module'))
