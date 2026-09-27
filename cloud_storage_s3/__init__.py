# Part of Insilos. See LICENSE file for full copyright and licensing details.

from . import models


def uninstall_hook(env):
    ICP = env['ir.config_parameter']
    if ICP.get_param('cloud_storage_provider') == 's3':
        env['res.config.settings']._check_cloud_storage_uninstallable()
        ICP.set_param('cloud_storage_provider', False)
    ICP.search([('key', 'in', [
        'cloud_storage_s3_endpoint_url',
        'cloud_storage_s3_bucket_name',
        'cloud_storage_s3_access_key',
        'cloud_storage_s3_secret_key',
        'cloud_storage_s3_region',
    ])]).unlink()
