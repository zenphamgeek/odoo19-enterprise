from odoo.tests.common import TransactionCase


class TestInsilosDemoRequest(TransactionCase):
    def test_create_and_progress_request(self):
        request = self.env["insilos.demo.request"].create(
            {
                "name": "Test User",
                "email": "test@example.com",
                "company": "Example Manufacturing",
                "industry": "pharma",
                "use_case": "governed_ai",
                "consent": True,
            }
        )
        self.assertEqual(request.state, "new")
        request.action_mark_contacted()
        self.assertEqual(request.state, "contacted")
        request.action_mark_qualified()
        self.assertEqual(request.state, "qualified")
        request.action_close()
        self.assertEqual(request.state, "closed")
