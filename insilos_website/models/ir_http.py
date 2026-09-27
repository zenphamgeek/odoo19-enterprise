# -*- coding: utf-8 -*-
import posixpath
from odoo import models
from odoo.http import request


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    @classmethod
    def _serve_fallback(cls):
        # Do not serve fallback page (e.g. homepage) if the request was a path traversal attempt
        if getattr(request, "_had_dot_segments", False):
            return False
        return super()._serve_fallback()

    @classmethod
    def _handle_error(cls, exception):
        # Prevent urljoin crash during error template rendering if request path contains dot-segments (. or ..)
        if request and hasattr(request, "httprequest"):
            raw_path = getattr(request.httprequest, "path", "")
            if ".." in raw_path or any(seg in (".", "..") for seg in raw_path.split("/")):
                request._had_dot_segments = True
                norm = posixpath.normpath(raw_path)
                if not norm.startswith("/"):
                    norm = "/" + norm

                # Update httprequest and wrapped request __dict__ to safe normalized path
                for obj in (
                    request.httprequest,
                    getattr(request.httprequest, "_HTTPRequest__wrapped", None),
                ):
                    if obj and hasattr(obj, "__dict__"):
                        obj.__dict__["path"] = norm
                        qs = (
                            obj.environ.get("QUERY_STRING", "")
                            if hasattr(obj, "environ")
                            else ""
                        )
                        obj.__dict__["full_path"] = f"{norm}?{qs}" if qs else norm

        return super()._handle_error(exception)
