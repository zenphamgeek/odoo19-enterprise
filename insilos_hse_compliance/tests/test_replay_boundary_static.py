# -*- coding: utf-8 -*-
# Part of Insilos. See LICENSE file for full copyright and licensing details.

import ast
from pathlib import Path
import unittest


class TestHSEReplayBoundaryStatic(unittest.TestCase):

    def test_direct_event_create_requires_immediate_unique_constraint(self):
        source = Path(__file__).resolve().parents[1] / 'models' / 'is_hse_compliance_event.py'
        tree = ast.parse(source.read_text())
        model = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'HSEComplianceEvent')
        create = next(node for node in model.body if isinstance(node, ast.FunctionDef) and node.name == 'create')
        create_source = ast.get_source_segment(source.read_text(), create)
        self.assertIn("c.contype = 'u' AND c.convalidated AND NOT c.condeferrable", create_source)
        self.assertIn("i.indisunique AND i.indisvalid AND i.indisready", create_source)
        self.assertIn("raise UserError(_('HSE event replay protection is unavailable.'))", create_source)
        self.assertIn("vals['state'] = 'new'", create_source)
        self.assertIn("vals['received_date'] = fields.Datetime.now()", create_source)
        self.assertIn("self.env.context.get('_hse_event_create') is not _EVENT_CREATE_TOKEN", create_source)
        self.assertIn("raise AccessError(_('Compliance evidence can only be received through a verified webhook.'))", create_source)
        self.assertIn("'name', 'reviewed_by_id', 'reviewed_date'", create_source)
        create_from_webhook = next(
            node for node in model.body
            if isinstance(node, ast.FunctionDef) and node.name == '_create_from_signed_webhook'
        )
        webhook_source = ast.get_source_segment(source.read_text(), create_from_webhook)
        self.assertIn("if capability is not _EVENT_CREATE_TOKEN:", webhook_source)
        self.assertIn("with_context(_hse_event_create=_EVENT_CREATE_TOKEN).create(vals_list)", webhook_source)

    def test_workflow_write_enforces_maker_checker_metadata(self):
        source = Path(__file__).resolve().parents[1] / 'models' / 'is_hse_compliance_event.py'
        tree = ast.parse(source.read_text())
        model = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'HSEComplianceEvent')
        write = next(node for node in model.body if isinstance(node, ast.FunctionDef) and node.name == 'write')
        write_source = ast.get_source_segment(source.read_text(), write)
        self.assertIn("vals.get('reviewed_by_id') != self.env.user.id", write_source)
        self.assertIn("A review must record the current HSE manager from a new event.", write_source)
        self.assertIn("ev.reviewed_by_id == self.env.user", write_source)
        self.assertIn("A reviewed event must be applied by a different HSE manager.", write_source)

    def test_legal_event_accepts_only_active_payload_and_target(self):
        source = Path(__file__).resolve().parents[1] / 'models' / 'is_hse_compliance_event.py'
        tree = ast.parse(source.read_text())
        model = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'HSEComplianceEvent')
        validate = next(node for node in model.body if isinstance(node, ast.FunctionDef) and node.name == '_validated_legal_document_payload')
        apply = next(node for node in model.body if isinstance(node, ast.FunctionDef) and node.name == 'action_apply_to_legal_register')
        self.assertIn("if doc['state'] != 'active':", ast.get_source_segment(source.read_text(), validate))
        apply_source = ast.get_source_segment(source.read_text(), apply)
        self.assertIn("activate_document = not doc or doc.state != 'active'", apply_source)
        self.assertIn("if doc and doc.state == 'active':", apply_source)

    def test_task_permit_check_is_internal_and_fail_closed(self):
        source = (Path(__file__).resolve().parents[1] / 'models' / 'project_task.py').read_text()
        self.assertIn("'chemical_substance_id', '=', chem.id", source)
        self.assertNotIn("('state', 'in', ['valid', 'expiring_soon'])", source)
        self.assertIn('không thể kết luận nghĩa vụ hoặc hiệu lực', source)
        self.assertIn('chưa xác nhận nghĩa vụ pháp lý hoặc hiệu lực bên ngoài', source)
        self.assertNotIn('đã đáp ứng giấy phép HSE', source)


if __name__ == '__main__':
    unittest.main()
