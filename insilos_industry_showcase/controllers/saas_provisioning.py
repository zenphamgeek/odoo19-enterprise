# -*- coding: utf-8 -*-
# Part of Insilos. See LICENSE file for full copyright and licensing details.

import logging
from odoo import http
from odoo.http import request
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class InsilosSaaSController(http.Controller):

    @http.route('/workspace/create', type='json', auth='public', methods=['POST'], csrf=False)
    def workspace_create(self, subdomain=None, tenant_id=None, idempotency_key=None, **kwargs):
        """
        Atomically provisions a SaaS workspace using DISM-TRL advisory locks.
        Guarantees non-blocking collision handling under concurrent traffic bursts.
        """
        if not subdomain:
            return {'status': 'error', 'error': 'subdomain_invalid'}

        try:
            workspace = request.env['saas.workspace'].sudo().provision_atomic(
                subdomain=subdomain,
                tenant_id=tenant_id,
                idempotency_key=idempotency_key,
                **kwargs
            )
            return {
                'status': 'success',
                'workspace_id': workspace.id,
                'subdomain': workspace.subdomain,
                'state': workspace.state,
            }
        except UserError as e:
            return {'status': 'error', 'error': str(e)}
        except Exception as e:
            _logger.exception("Error during SaaS workspace atomic creation for '%s': %s", subdomain, e)
            return {'status': 'error', 'error': 'system_busy'}
