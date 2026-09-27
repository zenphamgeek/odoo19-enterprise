import json

from odoo import Command
from odoo.addons.pos_react.tests.test_tour import TestPosReactBrowser
from odoo.exceptions import ValidationError
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class TestPosHrReactBrowser(TestPosReactBrowser):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.employee = cls.env["hr.employee"].sudo().create({
            "name": "POS React minimal employee",
            "user_id": cls.pos_user.id,
            "company_id": cls.main_pos_config.company_id.id,
            "pin": "1234",
            "barcode": "POSREACTMIN",
        })
        cls.cashier = cls.env["hr.employee"].sudo().create({
            "name": "POS React cashier employee",
            "company_id": cls.main_pos_config.company_id.id,
            "pin": "5678",
            "barcode": "POSREACTCASHIER",
        })
        cls.pos_user.group_ids = [Command.link(cls.env.ref("account.group_account_invoice").id)]
        cls.main_pos_config.write({
            "module_pos_hr": True,
            "minimal_employee_ids": [Command.set(cls.employee.ids)],
            "basic_employee_ids": [Command.set(cls.cashier.ids)],
        })

    def test_minimal_employee_browser(self):
        self.browser_js(
            f"/pos/react/{self.main_pos_config.id}",
            """
            (async () => {
                const data = JSON.parse(document.getElementById('pos-react-data').textContent);
                if (data.role !== 'minimal') throw new Error(`unexpected role: ${data.role}`);
                if (data.employee?.id !== %d || data.employee?.name !== 'POS React minimal employee') throw new Error('employee bootstrap missing');
                if ('pin' in data.employee || 'barcode' in data.employee || '_pin' in data.employee || '_barcode' in data.employee) throw new Error('employee secret leaked');
                const product = document.querySelector('.product');
                for (let attempt = 0; attempt < 100 && product.disabled; attempt++) await new Promise(resolve => setTimeout(resolve, 20));
                product.click();
                await new Promise(resolve => setTimeout(resolve, 100));
                if (document.querySelector('[aria-label^="Remove one"]')) throw new Error('minimal employee can decrement');
                console.log('POS React minimal employee permissions succeeded');
            })();
            """ % self.employee.id,
            "Boolean(document.querySelector('#pos-react-root .product'))",
            login="pos_user",
            success_signal="POS React minimal employee permissions succeeded",
        )

    def test_employee_pin_switch_browser(self):
        self.browser_js(
            f"/pos/react/{self.main_pos_config.id}",
            """
            (async () => {
                const data = JSON.parse(document.getElementById('pos-react-data').textContent);
                const setValue = (element, value) => {
                    Object.getOwnPropertyDescriptor(element.constructor.prototype, 'value').set.call(element, value);
                    element.dispatchEvent(new Event('change', { bubbles: true }));
                    element.dispatchEvent(new Event('input', { bubbles: true }));
                };
                const product = document.querySelector('.product');
                for (let attempt = 0; attempt < 100 && product.disabled; attempt++) await new Promise(resolve => setTimeout(resolve, 20));
                product.click();
                for (let attempt = 0; attempt < 100 && !document.querySelector('aside .line'); attempt++) await new Promise(resolve => setTimeout(resolve, 20));
                if (!document.querySelector('aside .line')) throw new Error('cart line missing before employee switch');
                if (document.querySelector('[aria-label^="Remove one"]')) throw new Error('minimal employee can decrement before switch');
                document.querySelector('[data-action-id="pos_hr_react.select_employee"]').click();
                for (let attempt = 0; attempt < 100 && !document.querySelector('[role="dialog"]'); attempt++) await new Promise(resolve => setTimeout(resolve, 20));
                const dialog = document.querySelector('[role="dialog"]');
                if (!dialog) throw new Error('employee dialog missing');
                const selects = dialog.querySelectorAll('select');
                setValue(selects[1], '%d');
                const input = dialog.querySelector('input');
                setValue(input, 'bad');
                dialog.querySelector('form').requestSubmit();
                for (let attempt = 0; attempt < 100 && !dialog.querySelector('[role="alert"]'); attempt++) await new Promise(resolve => setTimeout(resolve, 20));
                if (!dialog.querySelector('[role="alert"]')) throw new Error('wrong PIN accepted');
                setValue(input, '5678');
                dialog.querySelector('form').requestSubmit();
                for (let attempt = 0; attempt < 100 && document.querySelector('[role="dialog"]'); attempt++) await new Promise(resolve => setTimeout(resolve, 20));
                if (document.querySelector('[role="dialog"]')) throw new Error('valid PIN rejected');
                if (document.querySelector('[data-active-employee-id]')?.dataset.activeEmployeeId !== '%d') throw new Error('cashier identity not activated');
                document.querySelector('[data-action-id="pos_hr_react.select_employee"]').click();
                for (let attempt = 0; attempt < 100 && !document.querySelector('[role="dialog"]'); attempt++) await new Promise(resolve => setTimeout(resolve, 20));
                const barcodeDialog = document.querySelector('[role="dialog"]');
                const barcodeSelects = barcodeDialog.querySelectorAll('select');
                setValue(barcodeSelects[0], 'barcode');
                await new Promise(resolve => setTimeout(resolve, 20));
                const barcodeInput = barcodeDialog.querySelector('input');
                setValue(barcodeInput, 'POSREACTMIN');
                barcodeDialog.querySelector('form').requestSubmit();
                for (let attempt = 0; attempt < 100 && document.querySelector('[role="dialog"]'); attempt++) await new Promise(resolve => setTimeout(resolve, 20));
                if (document.querySelector('[data-active-employee-id]')?.dataset.activeEmployeeId !== '%d') throw new Error('barcode identity not activated');
                let payCash;
                for (let attempt = 0; attempt < 100 && !payCash; attempt++) {
                    payCash = [...document.querySelectorAll('button')].find(button => button.textContent === 'Pay cash' && !button.disabled);
                    if (!payCash) await new Promise(resolve => setTimeout(resolve, 20));
                }
                if (!payCash) throw new Error(`cash checkout unavailable: ${document.querySelector('[aria-label="Recovery error"]')?.textContent || 'no recovery error'}`);
                payCash.click();
                let order;
                for (let attempt = 0; attempt < 100 && !order; attempt++) {
                    const orders = await posReact.rpc('pos.order', 'search_read', [[['session_id', '=', data.sessionId], ['state', '=', 'paid']], ['employee_id', 'payment_ids'], 0, 1, 'id desc']);
                    order = orders[0];
                    if (!order) await new Promise(resolve => setTimeout(resolve, 20));
                }
                if (order?.employee_id?.[0] !== %d) throw new Error('order employee ownership missing');
                const payments = await posReact.rpc('pos.payment', 'search_read', [[['id', 'in', order.payment_ids]], ['employee_id']]);
                if (!payments.length || payments.some(payment => payment.employee_id?.[0] !== %d)) throw new Error('payment employee ownership missing');
                console.log('POS React employee ownership succeeded');
            })();
            """ % (
                self.cashier.id,
                self.cashier.id,
                self.employee.id,
                self.employee.id,
                self.employee.id,
            ),
            'Boolean(document.querySelector(\'[data-action-id="pos_hr_react.select_employee"]\'))',
            login="pos_user",
            success_signal="POS React employee ownership succeeded",
        )
        order = self.env["pos.order"].search([
            ("session_id.config_id", "=", self.main_pos_config.id),
            ("state", "=", "paid"),
        ], order="id desc", limit=1)
        self.assertEqual(order.employee_id, self.employee)
        self.assertTrue(order.payment_ids)
        self.assertEqual(order.payment_ids.employee_id, self.employee)
        with self.assertRaises(ValidationError):
            order._pos_react_validate_employee({}, order.session_id, order)
        with self.assertRaises(ValidationError):
            order._pos_react_validate_employee(
                {"employee_id": self.cashier.id},
                order.session_id,
                order,
            )

    def test_cash_move_employee_ownership_browser(self):
        self.browser_js(
            f"/pos/react/{self.main_pos_config.id}",
            """
            (async () => {
                const data = JSON.parse(document.getElementById('pos-react-data').textContent);
                const waitFor = async (predicate, message) => {
                    for (let attempt = 0; attempt < 100; attempt++) {
                        const value = await predicate();
                        if (value) return value;
                        await new Promise(resolve => setTimeout(resolve, 20));
                    }
                    throw new Error(message);
                };
                const setValue = (element, value) => {
                    Object.getOwnPropertyDescriptor(element.constructor.prototype, 'value').set.call(element, value);
                    element.dispatchEvent(new Event('change', { bubbles: true }));
                    element.dispatchEvent(new Event('input', { bubbles: true }));
                };
                const cashMove = async (type, amount, reason) => {
                    document.querySelector('[data-action-id="pos_hr_react.cash_move"]').click();
                    const dialog = await waitFor(() => document.querySelector('[role="dialog"]'), 'cash move dialog missing');
                    setValue(dialog.querySelector('select'), type);
                    const inputs = dialog.querySelectorAll('input');
                    setValue(inputs[0], amount);
                    setValue(inputs[1], reason);
                    dialog.querySelector('form').requestSubmit();
                    await waitFor(() => !document.querySelector('[role="dialog"]'), 'cash move was not recorded');
                };
                const findMove = (reason) => waitFor(async () => {
                    const moves = await posReact.rpc('account.bank.statement.line', 'search_read', [[
                        ['pos_session_id', '=', data.sessionId], ['payment_ref', 'ilike', reason],
                    ], ['amount', 'employee_id'], 0, 1, 'id desc']);
                    return moves[0];
                }, `cash move missing: ${reason}`);

                await cashMove('in', '12.5', 'React ownership cash in');
                const cashIn = await findMove('React ownership cash in');
                if (cashIn.amount !== 12.5) throw new Error(`cash-in sign mismatch: ${cashIn.amount}`);
                if (cashIn.employee_id?.[0] !== %d) throw new Error('cash-in active cashier ownership missing');

                document.querySelector('[data-action-id="pos_hr_react.select_employee"]').click();
                const employeeDialog = await waitFor(() => document.querySelector('[role="dialog"]'), 'employee dialog missing');
                setValue(employeeDialog.querySelectorAll('select')[1], '%d');
                setValue(employeeDialog.querySelector('input'), '5678');
                employeeDialog.querySelector('form').requestSubmit();
                await waitFor(() => !document.querySelector('[role="dialog"]'), 'cashier switch failed');
                if (document.querySelector('[data-active-employee-id]')?.dataset.activeEmployeeId !== '%d') throw new Error('switched cashier not active');

                await cashMove('out', '4.25', 'React ownership cash out');
                const cashOut = await findMove('React ownership cash out');
                if (cashOut.amount !== -4.25) throw new Error(`cash-out sign mismatch: ${cashOut.amount}`);
                if (cashOut.employee_id?.[0] !== %d) throw new Error('cash-out switched cashier ownership missing');
                console.log('POS React cash move ownership succeeded');
            })();
            """ % (self.employee.id, self.cashier.id, self.cashier.id, self.cashier.id),
            'Boolean(document.querySelector(\'[data-action-id="pos_hr_react.cash_move"]\'))',
            login="pos_user",
            success_signal="POS React cash move ownership succeeded",
        )
        moves = self.env["account.bank.statement.line"].search([
            ("pos_session_id.config_id", "=", self.main_pos_config.id),
            ("payment_ref", "ilike", "React ownership cash"),
        ], order="id")
        self.assertEqual(moves.mapped("amount"), [12.5, -4.25])
        self.assertEqual(moves[0].employee_id, self.employee)
        self.assertEqual(moves[1].employee_id, self.cashier)
        session = moves[0].pos_session_id.with_user(self.pos_user)
        for move_type, amount, reason in [
            ("invalid", 1, "reason"),
            ("in", 0, "reason"),
            ("out", -1, "reason"),
            ("in", float("nan"), "reason"),
            ("out", float("inf"), "reason"),
            ("in", True, "reason"),
            ("in", 1, " "),
            ("out", 1, "x" * 501),
        ]:
            with self.assertRaises(ValidationError):
                session.pos_react_try_cash_in_out(session.id, move_type, amount, reason)
        self.assertEqual(len(moves), 2)

    def test_employee_refresh_and_lock_browser(self):
        self.browser_js(
            f"/pos/react/{self.main_pos_config.id}",
            """
            (async () => {
                const waitFor = async (predicate, message) => {
                    for (let attempt = 0; attempt < 100; attempt++) {
                        const value = predicate();
                        if (value) return value;
                        await new Promise(resolve => setTimeout(resolve, 20));
                    }
                    throw new Error(message);
                };
                const setValue = (element, value) => {
                    Object.getOwnPropertyDescriptor(element.constructor.prototype, 'value').set.call(element, value);
                    element.dispatchEvent(new Event('change', { bubbles: true }));
                    element.dispatchEvent(new Event('input', { bubbles: true }));
                };
                const submitPin = async (pin) => {
                    const dialog = await waitFor(() => document.querySelector('[role="dialog"]'), 'employee dialog missing');
                    setValue(dialog.querySelector('input'), pin);
                    dialog.querySelector('form').requestSubmit();
                };

                document.querySelector('[data-action-id="pos_hr_react.select_employee"]').click();
                const selectDialog = await waitFor(() => document.querySelector('[role="dialog"]'), 'employee dialog missing');
                setValue(selectDialog.querySelectorAll('select')[1], '%d');
                await submitPin('5678');
                await waitFor(() => !document.querySelector('[role="dialog"]'), 'cashier PIN rejected');
                const refreshFrame = document.createElement('iframe');
                refreshFrame.src = location.href;
                document.body.appendChild(refreshFrame);
                const refreshed = refreshFrame.contentWindow;
                await waitFor(() => refreshed.document?.querySelector('[data-active-employee-id]')?.dataset.activeEmployeeId === '%d', 'authenticated refresh did not restore cashier');

                refreshed.document.querySelector('[data-action-id="pos_hr_react.lock"]').click();
                await waitFor(() => refreshed.document.querySelector('[role="dialog"]'), 'lock dialog missing');
                const staleDocument = refreshed.document;
                refreshed.location.reload();
                const lockedDialog = await waitFor(() => refreshed.document !== staleDocument && refreshed.document?.querySelector('[role="dialog"]'), 'refresh unlocked POS');
                setValue(lockedDialog.querySelectorAll('select')[1], '%d');
                const refreshedSubmitPin = async (pin) => {
                    const dialog = refreshed.document.querySelector('[role="dialog"]');
                    setValue(dialog.querySelector('input'), pin);
                    await new Promise(resolve => setTimeout(resolve, 0));
                    dialog.querySelector('form').requestSubmit();
                };
                await refreshedSubmitPin('bad');
                await waitFor(() => refreshed.document.querySelector('[role="dialog"] [role="alert"]'), 'wrong PIN unlocked POS');
                await refreshedSubmitPin('5678');
                await waitFor(() => !refreshed.document.querySelector('[role="dialog"]'), 'right PIN did not unlock POS');
                if (refreshed.document.querySelector('[data-active-employee-id]')?.dataset.activeEmployeeId !== '%d') throw new Error('unlock changed cashier');
                refreshFrame.remove();
                console.log('POS React employee refresh and lock succeeded');
            })();
            """ % (self.cashier.id, self.cashier.id, self.cashier.id, self.cashier.id),
            'Boolean(document.querySelector(\'[data-action-id="pos_hr_react.select_employee"]\'))',
            login="pos_user",
            success_signal="POS React employee refresh and lock succeeded",
        )
