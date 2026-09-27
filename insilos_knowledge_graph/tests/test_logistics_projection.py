from odoo import fields
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.exceptions import ValidationError

from ..services.graph_query import GraphQuery
from ..services.graph_service import GraphService
from ..services.logistics_projection import LogisticsProjection


@tagged('post_install', '-at_install')
class TestLogisticsProjection(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.projection = LogisticsProjection(cls.env)
        if not cls.projection.available:
            cls.skipTest(cls, 'Logistics IDP is not installed; projector disabled.')
        cls.case = cls.env['logistics.idp.case'].create({
            'name': 'KG-03', 'source_system': 'fixture', 'source_key': 'KG-03',
            'source_version': '1', 'provenance': 'fixture:kg-03', 'po_reference': 'PO-KG-1',
            'effective_date': '2026-01-01',
        })
        cls.document = cls.env['logistics.idp.document'].create({
            'case_id': cls.case.id, 'document_type': 'invoice', 'content_hash': 'a' * 64,
            'mimetype': 'application/json', 'status': 'valid',
        })
        cls.evidence = cls.env['logistics.idp.evidence'].create({
            'case_id': cls.case.id, 'category': 'invoice', 'source_reference': 'fixture:evidence',
            'status': 'valid', 'payload': {'invoice_number': 'INV-1'},
        })
        cls.extraction = cls.env['logistics.idp.extraction.run'].create({
            'case_id': cls.case.id, 'document_id': cls.document.id, 'provider': 'fixture',
            'model_version': 'fixture', 'schema_version': '1', 'prompt_version': '1',
            'started_at': fields.Datetime.now(), 'completed_at': fields.Datetime.now(),
            'status': 'valid', 'confidence': .99, 'payload': {'invoice_number': 'INV-1'},
        })

    def test_structured_projection_keeps_lineage_and_ai_candidate(self):
        first = self.projection.project_case(self.case)
        second = self.projection.project_case(self.case)
        self.assertEqual(first, second)
        edges = self.env['kg.edge'].search([('company_id', '=', self.case.company_id.id)])
        document_edge = edges.filtered(lambda edge: edge.relation == 'CONTAINS')
        evidence_edge = edges.filtered(lambda edge: edge.relation == 'SUPPORTED_BY')
        extraction_edge = edges.filtered(lambda edge: edge.source_type == 'LOGISTICS_EXTRACTION')
        self.assertEqual(document_edge.source_hash, self.document.content_hash)
        self.assertEqual(evidence_edge.source_hash, self.evidence.payload_hash)
        self.assertTrue(evidence_edge.verified)
        self.assertEqual((extraction_edge.state, extraction_edge.verified), ('CANDIDATE', False))
        self.assertEqual(extraction_edge.source_hash, self.extraction.payload_hash)

    def _create_po_line(self, line_key='1', material_code='MAT-1'):
        snapshot = self.env['logistics.idp.po.snapshot'].create({
            'company_id': self.case.company_id.id, 'po_reference': 'PO-KG-1',
            'snapshot_date': '2026-01-01', 'source_system': 'fixture',
            'source_key': 'PO-KG-1', 'source_version': '1', 'provenance': 'fixture:po',
            'payload': {'lines': [{'line_key': line_key, 'material_code': material_code}]},
        })
        return self.env['logistics.idp.po.snapshot.line'].create({
            'snapshot_id': snapshot.id, 'line_key': line_key, 'material_code': material_code,
            'ordered_quantity': 1, 'remaining_quantity': 1, 'uom': 'EA',
            'payload': {'line_key': line_key, 'material_code': material_code},
        })

    def _create_line_check(self, line_key='1', material_code='MAT-1', code='KG-CHECK'):
        return self.env['logistics.idp.check.result'].create({
            'case_id': self.case.id, 'code': code, 'required': True, 'verdict': 'pass',
            'rationale': 'Structured identity fixture.',
            'payload': {'line_key': line_key, 'material_code': material_code},
        })

    def test_po_line_structured_identity_match(self):
        line = self._create_po_line()
        check = self._create_line_check()
        self.projection.project_case(self.case)
        edge = self.env['kg.edge'].search([('source_type', '=', 'LOGISTICS_PO_LINE_CHECK')])
        self.assertEqual((edge.relation, edge.to_node_id.source_id), ('SUBJECT_TO', str(check.id)))
        self.assertEqual(edge.evidence_reference, 'sha256:' + edge.source_hash)
        self.assertTrue(edge.verified)

    def test_po_line_missing_identity_does_not_match(self):
        self._create_po_line(material_code=False)
        self._create_line_check(material_code=False)
        self.projection.project_case(self.case)
        self.assertFalse(self.env['kg.edge'].search([('source_type', '=', 'LOGISTICS_PO_LINE_CHECK')]))

    def test_po_line_ambiguous_identity_does_not_match(self):
        self._create_po_line()
        self._create_line_check(code='KG-CHECK-1')
        self._create_line_check(code='KG-CHECK-2')
        self.projection.project_case(self.case)
        self.assertFalse(self.env['kg.edge'].search([('source_type', '=', 'LOGISTICS_PO_LINE_CHECK')]))

    def test_po_line_check_link_is_company_isolated(self):
        self._create_po_line()
        self._create_line_check()
        self.projection.project_case(self.case)
        self.assertTrue(all(edge.company_id == self.case.company_id for edge in self.env['kg.edge'].search([])))

    def test_projects_case_checks_and_exceptions(self):
        check = self.env['logistics.idp.check.result'].create({
            'case_id': self.case.id, 'code': 'KG-CHECK', 'required': True,
            'verdict': 'review', 'rationale': 'Synthetic KG check.',
            'payload': {'kind': 'kg_projection'},
        })
        exception = self.env['logistics.idp.exception'].create({
            'case_id': self.case.id, 'exception_type': 'hs_code_mismatch',
            'severity': 'high',
        })
        self.projection.project_case(self.case)
        edges = self.env['kg.edge'].search([('company_id', '=', self.case.company_id.id)])
        check_edge = edges.filtered(lambda edge: edge.source_reference == '%s:%s' % (check._name, check.id))
        exception_edge = edges.filtered(lambda edge: edge.source_reference == '%s:%s' % (exception._name, exception.id))
        self.assertEqual((check_edge.relation, check_edge.state, check_edge.verified), ('SUBJECT_TO', 'VERIFIED', True))
        self.assertEqual((exception_edge.relation, exception_edge.state, exception_edge.verified), ('SUBJECT_TO', 'CANDIDATE', False))

    def test_312_lineage_projection_is_deterministic_provenance_bounded_and_company_isolated(self):
        first = self.projection.project_case(self.case)
        edges = self.env['kg.edge'].search([('company_id', '=', self.case.company_id.id)])
        snapshot = {(edge.edge_hash, edge.from_node_id.urn, edge.to_node_id.urn) for edge in edges}
        second = self.projection.project_case(self.case)
        edges_again = self.env['kg.edge'].search([('company_id', '=', self.case.company_id.id)])
        self.assertEqual(first.urn, second.urn)
        self.assertEqual(snapshot, {(edge.edge_hash, edge.from_node_id.urn, edge.to_node_id.urn) for edge in edges_again})
        self.assertEqual(len(edges_again.mapped('edge_hash')), len(edges_again))
        for edge in edges_again:
            if edge.verified:
                self.assertTrue(edge.source_reference and edge.source_hash and edge.evidence_reference)
            else:
                self.assertIn(edge.state, ('CANDIDATE', 'REJECTED', 'CONFLICT'))

        neighbors = GraphService(self.env).neighbors(first.urn, depth=1, limit=50)
        self.assertTrue(neighbors)
        self.assertTrue(all(item['state'] == 'VERIFIED' and item['evidence_reference'] for item in neighbors))
        with self.assertRaises(ValidationError):
            GraphService(self.env).neighbors(first.urn, depth=0)
        with self.assertRaises(ValidationError):
            GraphService(self.env).neighbors(first.urn, include_unverified=True)
        with self.assertRaises(ValidationError):
            GraphQuery(self.env).paths(first.urn, first.urn, max_depth=0)
        self.assertEqual(GraphQuery(self.env).paths(first.urn, first.urn), [])
        self.assertTrue(all(edge.company_id == self.case.company_id for edge in edges_again))
