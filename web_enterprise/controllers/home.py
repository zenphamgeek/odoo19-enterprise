# Part of Insilos. See LICENSE file for full copyright and licensing details.

from insilos.addons.web.controllers import home as web_home
from insilos.http import request, route


class Home(web_home.Home):

    @route()
    def web_client(self, s_action=None, **kw):
        response = super().web_client(s_action, **kw)
        if response.status_code == 200:
            response.set_cookie('color_scheme', request.env['ir.http'].color_scheme())
        return response
