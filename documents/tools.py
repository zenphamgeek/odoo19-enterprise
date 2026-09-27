from odoo.http import request, root
from odoo.tools import file_open


def is_mimetype_textual(mimetype):
    maintype, subtype = mimetype.split('/')
    return (
        maintype == 'text'
        or (maintype == 'application' and subtype in {'documents-email', 'json', 'xml'})
    )


def attachment_read(attachment, size=4096):
    """Return up to `size` bytes of content.

    May read the whole content in memory first if the content is stored in the database
    :param attachment: attachment record to read
    :param int|None size: maximum number of bytes to read (full content if `None`)
    """
    attachment.ensure_one()
    if not attachment:
        return None
    if attachment.raw:
        with attachment.raw.open() as f:
            return f.read(size) if size is not None else f.read()
    if attachment.url and (static_path := root.get_static_file(
        attachment.url,
        host=request.httprequest.environ.get('HTTP_HOST', '')
    )):
        with file_open(static_path, 'rb') as f:
            return f.read(size)
    return None
