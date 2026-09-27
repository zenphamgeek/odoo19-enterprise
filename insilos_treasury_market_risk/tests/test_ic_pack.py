# Part of Insilos. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install', 'treasury_market_risk')
class TestTreasuryICPack(TransactionCase):
    def setUp(self):
        super().setUp()
        self.task = self.env['project.task'].create({'name': 'IC Pack Test'})

    def test_case_inputs_and_approval_link_are_persistent(self):
        currency = self.env.company.currency_id
        self.task.write({
            'treasury_decision_value': 1250000,
            'treasury_decision_currency_id': currency.id,
            'treasury_recommendation': 'Hedge exposure.',
            'treasury_alternatives': 'Do nothing.',
            'treasury_scorecard_json': {'risk': 4},
            'treasury_independent_challenge': 'Validate forecast.',
            'treasury_assumptions_unknowns': 'Forecast is uncertain.',
            'treasury_evidence_references': 'Evidence-001',
        })
        category = self.env['approval.category'].create({'name': 'Treasury IC Pack Test'})
        approval = self.env['approval.request'].create({
            'name': 'IC Pack Approval', 'category_id': category.id, 'treasury_task_id': self.task.id,
        })
        self.task.invalidate_recordset(['treasury_decision_value', 'treasury_scorecard_json', 'treasury_approval_request_ids'])
        self.assertEqual(self.task.treasury_decision_value, 1250000)
        self.assertEqual(self.task.treasury_scorecard_json, {'risk': 4})
        self.assertEqual(self.task.treasury_approval_request_ids, approval)
        self.assertEqual(approval.treasury_task_id, self.task)

    def test_report_action_has_eighteen_sections_and_unavailable_markers(self):
        report = self.env.ref('insilos_treasury_market_risk.action_report_treasury_ic_pack')
        self.assertEqual(report.model, 'project.task')
        view = self.env.ref('insilos_treasury_market_risk.report_treasury_ic_pack')
        for section in range(1, 19):
            self.assertIn(f'{section}.', view.arch_db)
        self.assertIn('Unavailable', view.arch_db)

    def test_generate_snapshots_pdf_json_and_audit_message(self):
        wizard = self.env['treasury.generate.ic.pack.wizard'].create({'task_id': self.task.id})
        wizard.action_generate()
        attachments = self.env['ir.attachment'].search([
            ('res_model', '=', 'project.task'), ('res_id', '=', self.task.id),
            ('name', 'like', 'IC Pack - %'),
        ])
        self.assertEqual(set(attachments.mapped('mimetype')), {'application/pdf', 'application/json'})
        self.assertTrue(self.task.message_ids.filtered(lambda message: 'Treasury IC Pack snapshot generated.' in message.body))

    def test_signature_handoff_requires_snapshot_and_manager(self):
        manager = self.env['res.users'].create({
            'name': 'IC Pack Manager', 'login': 'ic_pack_manager',
            'group_ids': [(4, self.env.ref('insilos_treasury_market_risk.group_treasury_manager').id), (4, self.env.ref('project.group_project_user').id)],
        })
        self.task.user_ids = [(4, manager.id)]
        with self.assertRaises(UserError):
            self.task.with_user(manager).action_send_treasury_ic_pack_for_signature()
        self.env['ir.attachment'].create({
            'name': 'IC Pack - Test.pdf', 'raw': b'%PDF', 'mimetype': 'application/pdf',
            'res_model': 'project.task', 'res_id': self.task.id,
        })
        reader = self.env['res.users'].create({'name': 'IC Pack Reader', 'login': 'ic_pack_reader'})
        with self.assertRaises(UserError):
            self.task.with_user(reader).action_send_treasury_ic_pack_for_signature()
        action = self.task.with_user(manager).action_send_treasury_ic_pack_for_signature()
        self.assertEqual(action['res_model'], 'sign.send.request')
        self.assertEqual(action['context']['default_reference_doc'], f'project.task,{self.task.id}')
