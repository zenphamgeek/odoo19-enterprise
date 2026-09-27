# Part of Insilos. See LICENSE file for full copyright and licensing details.
"""Authenticated, read-only market-data contracts (DATA-004/DATA-007)."""

from odoo import http
from odoo.http import request, route

from ..services.provider import get_provider


class MarketDataController(http.Controller):

    @route('/market/bars', type='jsonrpc', auth='user', methods=['POST'], csrf=False, readonly=True)
    def bars(self, symbol, date_from, date_to, **kwargs):
        return get_provider(request.env).bars(request.env, symbol.upper(), date_from, date_to)

    @route('/market/quote', type='jsonrpc', auth='user', methods=['POST'], csrf=False, readonly=True)
    def quote(self, symbol, **kwargs):
        return get_provider(request.env).quote(request.env, symbol.upper())

    @route('/market/stream', type='jsonrpc', auth='user', methods=['POST'], csrf=False, readonly=True)
    def stream(self, symbol, **kwargs):
        return get_provider(request.env).stream(request.env, symbol.upper())
