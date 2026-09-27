# Part of Insilos. See LICENSE file for full copyright and licensing details.

{
    "name": "Cloud Storage S3",
    "summary": """Store chatter attachments in an S3-compatible object store (MinIO, AWS S3, ...)""",
    "category": "Technical Settings",
    "version": "1.0",
    "depends": ["cloud_storage"],
    "data": [
        "views/settings.xml",
    ],
    "uninstall_hook": "uninstall_hook",
    'author': 'Insilos S.A.',
    'license': 'LGPL-3',
}
