import json

from odoo import fields
from odoo.tests.common import TransactionCase, tagged

from ..models.logistics_idp import LogisticsPolicySource, _INTERNAL_SNAPSHOT_TOKEN
from ..services.restricted_party import canonical_party_evidence, normalize_party, sanitize_lists, screen_parties


@tagged('post_install', '-at_install')
class TestRestrictedPartyPure(TransactionCase):
    def test_normalize_and_fuzzy_alias_match(self):
        self.assertEqual(normalize_party('  ACME   Trading  CO. '), 'acme trading co.')
        lists = [{
            'list_name': 'SYN-DEMO', 'program': 'demo', 'source': 'synthetic', 'version': '2026.1',
            'entries': [{'name': 'Acme Trading Company', 'aliases': ['acme co ltd'], 'country': 'XX'}],
        }]
        hit = screen_parties(['ACME CO LTD'], lists)
        self.assertEqual(hit['verdict'], 'review')
        self.assertEqual(hit['hits'][0]['matched'], 'acme co ltd')
        self.assertEqual(hit['lists_consulted'], 1)
        clean = screen_parties(['Totally Different Supplier'], lists)
        self.assertEqual((clean['verdict'], clean['hits']), ('pass', []))

    def test_canonical_party_roles_and_identifiers_are_deterministic(self):
        self.assertEqual(canonical_party_evidence(
            {'parties': [{'role': 'buyer', 'name': ' Buyer ', 'identifiers': ['VAT-2', 'VAT-1']},
                         {'role': 'unknown', 'name': 'Ignored'}]},
            {'supplier': 'Supplier X'}), [
                {'role': 'buyer', 'name': 'buyer', 'identifiers': [{'type': 'other', 'value': 'vat-1'}, {'type': 'other', 'value': 'vat-2'}], 'assets': []},
                {'role': 'supplier', 'name': 'supplier x', 'identifiers': [], 'assets': []},
            ])

    def test_typed_identifiers_and_transport_assets_are_canonical(self):
        self.assertEqual(canonical_party_evidence({'parties': [{
            'role': 'shipper', 'identifiers': [
                {'type': 'IMO', 'value': ' 123 '}, {'type': 'unknown', 'value': 'drop'},
            ], 'assets': [{'type': 'vessel', 'value': ' MV Demo '}, {'type': 'car', 'value': 'drop'}],
        }]}), [{'role': 'shipper', 'name': '', 'identifiers': [{'type': 'imo', 'value': '123'}],
                     'assets': [{'type': 'vessel', 'value': 'mv demo'}]}])

    def test_sanitize_drops_malformed_entries(self):
        self.assertEqual(sanitize_lists(None), [])
        self.assertEqual(sanitize_lists([{'entries': [{'name': ''}]}]), [])
        self.assertEqual(sanitize_lists([{'list_name': 'L', 'entries': [
            {'name': 'Valid Name', 'aliases': ['v n']},
            {'name': ''}, 'not-a-dict',
        ]}]), [{'list_name': 'L', 'program': None, 'source': None, 'version': None,
                'entries': [{'name': 'valid name', 'aliases': ['v n'], 'country': None, 'id_numbers': []}]}])

    def test_no_lists_requires_incomplete_review(self):
        self.assertEqual(screen_parties(['Supplier X'], []),
                         {'verdict': 'review', 'hits': [], 'lists_consulted': 0,
                          'reason': 'restricted_party_screening_incomplete'})


@tagged('post_install', '-at_install')
class TestRestrictedPartyRuntime(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context={**cls.env.context, 'logistics_idp_test_authority_registry': {
            'authoritative_tier_1': {'https://example.invalid/restricted-party': {
                'approved': True, 'source_tier': 'authoritative_tier_1'}}}})
        cls.case = cls.env['logistics.idp.case'].create({
            'name': 'RPS-01', 'source_system': 'fixture', 'source_key': 'RPS-01',
            'source_version': '1', 'provenance': 'fixture:rps',
            'effective_date': '2026-06-01', 'supplier_reference': 'Acme Trading Company',
        })
        cls.clean_case = cls.env['logistics.idp.case'].create({
            'name': 'RPS-CLEAN-CASE', 'source_system': 'fixture', 'source_key': 'RPS-CLEAN-CASE',
            'source_version': '1', 'provenance': 'fixture:rps',
            'effective_date': '2026-06-01', 'supplier_reference': 'Clean Supplier',
        })
        baseline = cls.env.ref('insilos_logistics_idp.policy_trade_compliance_vn_reference_2026_2')
        payload = json.loads(baseline.payload)
        payload['overlays']['restricted_parties'] = [{
            'list_name': 'SYN-DEMO-PARTIES', 'program': 'demo', 'source': 'synthetic_fixture',
            'version': '2026.1',
            'entries': [{'name': 'Acme Trading Company', 'aliases': ['ACME CO'], 'country': 'XX'}],
        }]
        cls.policy = cls.env['logistics.idp.policy.source']._controlled_create({
            'code': 'RPS-DEMO', 'version': '2026.1', 'company_id': cls.env.company.id,
            'jurisdiction': 'XX', 'regime': 'ALL', 'source_tier': 'authoritative_tier_1',
            'citation': 'https://example.invalid/restricted-party', 'provenance': json.dumps({'verification': 'verified'}), 'effective_from': '2026-01-01', 'last_successful_sync_at': fields.Datetime.now(), 'state': 'active',
            'payload': payload,
        }, 'test_fixture')

    def test_screening_hit_routes_review_and_is_idempotent(self):
        po = invoice = {'supplier': 'Acme Trading Company', 'lines': []}
        first = self.case._restricted_party_screening(po, invoice, 'binding-rps')
        self.assertEqual((first['verdict'], first['performed'], first['lists_consulted']),
                         ('review', True, 1))
        self.assertTrue(first['hits'])
        check = self.env['logistics.idp.check.result'].browse(first['check_id'])
        self.assertEqual((check.code, check.verdict, check.policy_source_id.id),
                         ('RESTRICTED_PARTY_SCREENING', 'review', self.policy.id))
        exception = self.env['logistics.idp.exception'].search([
            ('case_id', '=', self.case.id), ('exception_type', '=', 'restricted_party_hit')])
        self.assertEqual(len(exception), 1)
        second = self.case._restricted_party_screening(po, invoice, 'binding-rps')
        self.assertEqual(second['check_id'], check.id)
        self.assertEqual(self.env['logistics.idp.check.result'].search_count([
            ('case_id', '=', self.case.id), ('code', '=', 'RESTRICTED_PARTY_SCREENING')]), 1)

    def test_policy_change_creates_new_immutable_check(self):
        po = invoice = {'supplier': 'Acme Trading Company', 'lines': []}
        first = self.case._restricted_party_screening(po, invoice, 'binding-rps-policy-change')
        prior = self.env['logistics.idp.check.result'].browse(first['check_id'])
        prior_snapshot = (prior.id, prior.audit_input_hash, prior.policy_source_id.id, prior.verdict, prior.actual)

        changed_payload = json.loads(self.policy.payload)
        changed_payload['overlays']['restricted_parties'][0]['version'] = '2026.2'
        changed = self.env['logistics.idp.policy.source']._controlled_create({
            'code': 'RPS-DEMO-V2', 'version': '2026.2', 'company_id': self.env.company.id,
            'jurisdiction': 'XX', 'regime': 'ALL', 'source_tier': 'authoritative_tier_1',
            'citation': 'https://example.invalid/restricted-party', 'provenance': json.dumps({'verification': 'verified'}), 'effective_from': '2026-01-01', 'last_successful_sync_at': fields.Datetime.now(), 'state': 'active',
            'payload': changed_payload,
        }, 'test_fixture')

        second = self.case._restricted_party_screening(po, invoice, 'binding-rps-policy-change')
        current = self.env['logistics.idp.check.result'].browse(second['check_id'])
        self.assertNotEqual(current.id, prior.id)
        self.assertNotEqual(current.audit_input_hash, prior.audit_input_hash)
        self.assertEqual(current.policy_source_id.id, changed.id)
        self.assertEqual((prior.id, prior.audit_input_hash, prior.policy_source_id.id, prior.verdict, prior.actual), prior_snapshot)
        self.assertEqual(self.env['logistics.idp.check.result'].search_count([
            ('case_id', '=', self.case.id), ('code', '=', 'RESTRICTED_PARTY_SCREENING')]), 2)

    def test_untrusted_source_forces_review_with_immutable_evidence(self):
        payload = json.loads(self.policy.payload)
        self.env['logistics.idp.policy.source']._controlled_create({
            'code': 'RPS-UNTRUSTED', 'version': '1', 'company_id': self.env.company.id,
            'jurisdiction': 'XX', 'regime': 'ALL', 'source_tier': 'demo', 'citation': 'fixture',
            'effective_from': '2026-01-01', 'state': 'active', 'payload': payload,
        }, 'test_fixture')
        result = self.clean_case._restricted_party_screening(
            {'supplier': 'Clean Supplier'}, {'supplier': 'Clean Supplier'}, 'binding-untrusted')
        self.assertEqual((result['verdict'], result['performed']), ('review', False))
        check = self.env['logistics.idp.check.result'].browse(result['check_id'])
        self.assertEqual(check.verdict, 'review')
        self.assertIn('not_legally_authoritative', json.loads(check.payload)['reason_codes'][0])

    def test_clean_party_passes(self):
        result = self.clean_case._restricted_party_screening(
            {'supplier': 'Clean Supplier'}, {'supplier': 'Clean Supplier'}, 'binding-clean')
        self.assertEqual((result['verdict'], result['hits']), ('pass', []))
        check = self.env['logistics.idp.check.result'].browse(result['check_id'])
        self.assertEqual((check.code, check.verdict), ('RESTRICTED_PARTY_SCREENING', 'pass'))

    def test_screening_rejects_unactivated_source_provenance(self):
        super(LogisticsPolicySource, self.policy.with_context(
            _logistics_snapshot_token=_INTERNAL_SNAPSHOT_TOKEN,
        )).write({'audit_service': 'forged_rpc'})
        result = self.clean_case._restricted_party_screening(
            {'supplier': 'Clean Supplier'}, {'supplier': 'Clean Supplier'}, 'binding-unactivated-source')
        self.assertEqual((result['verdict'], result['performed']), ('review', False))
        reasons = json.loads(self.env['logistics.idp.check.result'].browse(result['check_id']).payload)['reason_codes']
        self.assertIn('missing_activated_provenance:%s' % self.policy.id, reasons)

    def test_company_isolation_ignores_foreign_lists(self):
        other_company = self.env['res.company'].create({'name': 'RPS Alien'})
        alien_payload = json.loads(self.policy.payload)
        alien_payload['overlays']['restricted_parties'] = [{
            'list_name': 'ALIEN-LIST', 'program': 'demo', 'source': 'synthetic_fixture',
            'version': '2026.1', 'entries': [{'name': 'Clean Supplier', 'aliases': []}],
        }]
        self.env['logistics.idp.policy.source']._controlled_create({
            'code': 'RPS-ALIEN', 'version': '2026.1', 'company_id': other_company.id,
            'jurisdiction': 'XX', 'regime': 'ALL', 'source_tier': 'authoritative_tier_1',
            'citation': 'https://example.invalid/restricted-party', 'provenance': json.dumps({'verification': 'verified'}), 'effective_from': '2026-01-01', 'last_successful_sync_at': fields.Datetime.now(), 'state': 'active',
            'payload': alien_payload,
        }, 'test_fixture')
        result = self.clean_case._restricted_party_screening(
            {'supplier': 'Clean Supplier'}, {'supplier': 'Clean Supplier'}, 'binding-alien')
        self.assertEqual((result['verdict'], result['hits']), ('pass', []))

    def test_reconcile_wire_downgrades_pass_to_review_on_hit(self):
        po = {'supplier': 'Clean Supplier', 'regime': 'E13', 'lines': [{
            'material_code': 'MAT-RPS', 'regime': 'E13', 'quantity': 2, 'unit_price': 10}]}
        invoice = {'document_type': 'main_vat_invoice', 'supplier': 'Clean Supplier',
                   'invoice_number': 'INV-RPS', 'regime': 'E13', 'lines': [{
                       'material_code': 'MAT-RPS', 'regime': 'E13', 'quantity': 2, 'unit_price': 10}]}
        clean_case = self.env['logistics.idp.case'].create({
            'name': 'RPS-CLEAN', 'source_system': 'fixture', 'source_key': 'RPS-CLEAN',
            'source_version': '1', 'provenance': 'fixture:rps',
            'effective_date': '2026-06-01', 'supplier_reference': 'Clean Supplier',
        })
        self.env['logistics.idp.supplier.profile'].import_upsert({
            'company_id': self.env.company.id, 'supplier_reference': 'Clean Supplier',
            'profile_code': 'RPS-PROFILE', 'version': 'v1',
            'source_system': 'fixture', 'source_key': 'RPS-PROFILE', 'source_version': 'v1',
            'provenance': 'fixture:rps', 'effective_from': '2026-01-01',
            'payload': {'draft_invoice': {'mode': 'skipped', 'final_number_allowed': False}},
        })
        clean_evidence = clean_case.reconcile_documents(po, invoice)
        clean_payload = json.loads(clean_evidence.payload)
        self.assertEqual(clean_payload['verdict'], 'pass')
        self.assertEqual(clean_payload['restricted_party']['verdict'], 'pass')
        self.env['logistics.idp.supplier.profile'].import_upsert({
            'company_id': self.env.company.id, 'supplier_reference': 'Acme Trading Company',
            'profile_code': 'RPS-PROFILE-2', 'version': 'v1',
            'source_system': 'fixture', 'source_key': 'RPS-PROFILE-2', 'source_version': 'v1',
            'provenance': 'fixture:rps', 'effective_from': '2026-01-01',
            'payload': {'draft_invoice': {'mode': 'skipped', 'final_number_allowed': False}},
        })
        hit_evidence = self.case.reconcile_documents(
            {**po, 'supplier': 'Acme Trading Company'},
            {**invoice, 'supplier': 'Acme Trading Company'})
        hit_payload = json.loads(hit_evidence.payload)
        self.assertEqual(hit_payload['verdict'], 'review')
        self.assertEqual(hit_payload['restricted_party']['verdict'], 'review')
        self.assertTrue(hit_payload['restricted_party']['hits'])

        prior_snapshot = clean_evidence.payload
        changed_payload = json.loads(self.policy.payload)
        changed_payload['overlays']['restricted_parties'][0]['entries'] = [{'name': 'Clean Supplier'}]
        self.env['logistics.idp.policy.source']._controlled_create({
            'code': 'RPS-CACHE-V2', 'version': '2', 'company_id': self.env.company.id,
            'jurisdiction': 'XX', 'regime': 'ALL', 'source_tier': 'authoritative_tier_1',
            'citation': 'https://example.invalid/restricted-party', 'provenance': json.dumps({'verification': 'verified'}), 'effective_from': '2026-01-01', 'last_successful_sync_at': fields.Datetime.now(), 'state': 'active',
            'payload': changed_payload,
        }, 'test_fixture')
        changed = clean_case.reconcile_documents(po, invoice)
        self.assertNotEqual(changed.id, clean_evidence.id, 'Policy change reused stale clearance')
        self.assertEqual(json.loads(changed.payload)['verdict'], 'review')
        self.assertTrue(json.loads(changed.payload)['restricted_party']['hits'])
        self.assertEqual(clean_evidence.payload, prior_snapshot)
        self.assertEqual(clean_case.reconcile_documents(po, invoice), changed)
