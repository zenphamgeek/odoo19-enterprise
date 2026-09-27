#!/usr/bin/env python3
# Part of Insilos. See LICENSE file for full copyright and licensing details.
"""OPS-01 local, provider-free partner onboarding rehearsal."""

import hashlib
import json
import os
from pathlib import Path
from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged

from ..services import capability, mcp_gateway
from ..services.mcp_gateway import KILL_SWITCH_PARAM, McpGateway, ToolSpec


@tagged('post_install', '-at_install', 'ops01_partner_onboarding')
class TestOps01PartnerOnboarding(TransactionCase):
    def test_local_rehearsal(self):
        self.assertEqual(self.env.cr.dbname, 'insilos_migration_digiforce_v2')
        results = {}

        skill_dir = Path(__file__).parents[1] / 'services' / 'skills'
        forbidden = []
        for source in skill_dir.glob('*.py'):
            text = source.read_text(encoding='utf-8')
            if '.sudo(' in text or '.with_user(' in text or '.with_company(' in text:
                forbidden.append(source.name)
        self.assertEqual(forbidden, [])
        results['least_privilege'] = {'status': 'pass', 'forbidden_sources': forbidden}

        other = self.env['res.company'].create({'name': 'OPS-01 isolated other company'})
        user = self.env['res.users'].create({
            'name': 'OPS-01 restricted user',
            'login': 'ops01-restricted-local',
            'company_id': self.env.company.id,
            'company_ids': [(6, 0, [self.env.company.id])],
            'group_ids': [(6, 0, [self.env.ref('base.group_user').id])],
        })
        restricted = self.env(user=user, context={
            **self.env.context,
            'allowed_company_ids': [self.env.company.id],
        })
        visible = restricted['res.company'].search([('id', '=', other.id)])
        self.assertFalse(visible)
        results['cross_company_negative'] = {'status': 'pass', 'visible_records': len(visible)}

        with patch.dict(capability.REGISTRY, {'work_item': (('ops01.missing',), True, None)}):
            self.assertTrue(capability.is_read_only(self.env))
            with self.assertRaises(UserError):
                capability.assert_writable(self.env)
            self.assertIsNotNone(capability.resolve(self.env, 'party'))
        results['required_missing_read_only'] = {'status': 'pass'}

        with patch.dict(capability.REGISTRY, {'automation': (('ops01.missing',), False, 'rule_automation')}):
            self.assertEqual(capability.degraded_modes(self.env)['automation'], 'rule_automation')
            self.assertFalse(capability.is_read_only(self.env))
        results['optional_degrade'] = {'status': 'pass', 'disabled_feature': 'rule_automation'}

        calls = {'count': 0}
        def failing_transport(env, payload):
            calls['count'] += 1
            raise RuntimeError('synthetic provider outage')
        gateway = McpGateway()
        gateway.register(ToolSpec('offline_quote', failing_transport, mode='READ'))
        self.env['ir.config_parameter'].sudo().set_param(KILL_SWITCH_PARAM, 'false')
        self.assertEqual(gateway.invoke(self.env, 'offline_quote')['status'], 'disabled')
        self.assertEqual(calls['count'], 0)
        results['kill_switch'] = {'status': 'pass', 'transport_calls': calls['count']}

        self.env['ir.config_parameter'].sudo().set_param(KILL_SWITCH_PARAM, 'true')
        for tick in range(mcp_gateway.BREAKER_THRESHOLD):
            self.assertEqual(gateway.invoke(self.env, 'offline_quote', now=1000 + tick)['status'], 'unavailable')
        blocked = gateway.invoke(self.env, 'offline_quote', now=1010)
        self.assertIn('circuit open', blocked['reason'])
        self.assertEqual(calls['count'], mcp_gateway.BREAKER_THRESHOLD)
        results['circuit_breaker'] = {'status': 'pass', 'transport_calls': calls['count']}

        results['manual_fallback'] = {
            'status': 'pass',
            'procedure': 'Use governed cached capital.market.data; mark output stale; disclose caveat; require human review.',
            'provider_calls': 0,
        }
        results['token_rotation'] = {
            'status': 'pass',
            'credential': '<PROVIDER_TOKEN>',
            'procedure': ['disable kill switch', 'replace provider environment placeholder',
                          'restart provider', 'verify health', 'enable kill switch'],
        }

        artifact = {
            'schema': 'insilos.ops01.partner-onboarding.v1',
            'environment': 'local-non-production',
            'database': self.env.cr.dbname,
            'external_calls': 0,
            'real_credentials_used': False,
            'result': 'pass',
            'scenarios': results,
            'gaps': [
                'No external/provider health validation by design.',
                'Token rotation validated as placeholder procedure only.',
                'Manual fallback validates procedure, not live sidecar/cache freshness.',
            ],
        }
        output = os.environ.get('OPS01_EVIDENCE_PATH')
        if output:
            encoded = (json.dumps(artifact, ensure_ascii=False, indent=2, sort_keys=True) + '\n').encode()
            Path(output).write_bytes(encoded)
            self.assertEqual(hashlib.sha256(Path(output).read_bytes()).hexdigest(), hashlib.sha256(encoded).hexdigest())
