import json

from odoo import Command
from odoo.addons.pos_react.tests.test_tour import TestPosReactBrowser
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class TestPosDiscountReactBrowser(TestPosReactBrowser):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.discount_tax_a = cls.env["account.tax"].create({
            "name": "POS React discount A 10%",
            "type_tax_use": "sale",
            "amount_type": "percent",
            "amount": 10,
        })
        cls.discount_tax_b = cls.env["account.tax"].create({
            "name": "POS React discount B 20%",
            "type_tax_use": "sale",
            "amount_type": "percent",
            "amount": 20,
        })
        cls.discount_product_a = cls.env["product.product"].create({
            "name": "POS React discount taxable A",
            "list_price": 100,
            "available_in_pos": True,
            "taxes_id": [Command.set((cls.discount_tax_a | cls.discount_tax_b).ids)],
        })
        cls.discount_product_b = cls.env["product.product"].create({
            "name": "POS React discount taxable B",
            "list_price": 50,
            "available_in_pos": True,
            "taxes_id": [Command.set(cls.discount_tax_b.ids)],
        })
        cls.discount_product = cls.env["product.product"].create({
            "name": "POS React global discount",
            "available_in_pos": True,
        })
        cls.tip_product = cls.env["product.product"].create({
            "name": "POS React tip",
            "list_price": 20,
            "available_in_pos": True,
            "taxes_id": [Command.clear()],
        })
        cls.main_pos_config.write({
            "module_pos_discount": True,
            "iface_discount": False,
            "discount_pc": 10,
            "discount_product_id": cls.discount_product.id,
            "tip_product_id": cls.tip_product.id,
        })

    def test_global_discount_tax_grouped_browser(self):
        self.env["res.lang"]._activate_and_install_lang("vi_VN")
        self.pos_user.lang = "vi_VN"
        fiscal_position = self.env["account.fiscal.position"].create({"name": "POS React discount fiscal position"})
        destination_tax_a = self.env["account.tax"].create({
            "name": "POS React discount destination A 5%",
            "type_tax_use": "sale",
            "amount_type": "percent",
            "amount": 5,
            "fiscal_position_ids": [(6, 0, fiscal_position.ids)],
            "original_tax_ids": [(6, 0, self.discount_tax_a.ids)],
        })
        source_amounts = [
            (self.discount_product_a, self.discount_tax_a | self.discount_tax_b, destination_tax_a | self.discount_tax_b, 100),
            (self.discount_product_b, self.discount_tax_b, self.discount_tax_b, 50),
        ]
        mapped_amounts = [
            mapped_taxes.compute_all(amount, product=product)
            for product, _, mapped_taxes, amount in source_amounts
        ]
        discount_amounts = [
            mapped_taxes.compute_all(-amount * 0.1, product=self.discount_product)
            for _, _, mapped_taxes, amount in source_amounts
        ]
        self.main_pos_config.default_fiscal_position_id = fiscal_position
        source_tax = sum(amounts["total_included"] - amounts["total_excluded"] for amounts in mapped_amounts)
        expected = {
            "source_tax": source_tax,
            "mapped_tax": source_tax + sum(amounts["total_included"] - amounts["total_excluded"] for amounts in discount_amounts),
            "total": sum(amounts["total_included"] for amounts in mapped_amounts + discount_amounts) + 20,
            "lines": [{
                "product_id": product.id,
                "tax_ids": source_taxes.ids,
                "subtotal": amounts["total_excluded"],
                "total": amounts["total_included"],
            } for (product, source_taxes, _, _), amounts in zip(source_amounts, mapped_amounts)] + [{
                "product_id": self.discount_product.id,
                "tax_ids": source_taxes.ids,
                "subtotal": amounts["total_excluded"],
                "total": amounts["total_included"],
            } for (_, source_taxes, _, _), amounts in zip(source_amounts, discount_amounts)] + [{
                "product_id": self.tip_product.id,
                "tax_ids": [],
                "subtotal": 20,
                "total": 20,
            }],
        }
        self.browser_js(
            f"/pos/react/{self.main_pos_config.id}",
            f"""
            (async () => {{
                const check = (condition, message) => {{ if (!condition) throw new Error(message); }};
                const waitFor = async (condition, message) => {{
                    for (let attempt = 0; attempt < 100; attempt++) {{
                        const value = await condition();
                        if (value) return value;
                        await new Promise(resolve => setTimeout(resolve, 20));
                    }}
                    throw new Error(message);
                }};
                const data = JSON.parse(document.getElementById('pos-react-data').textContent);
                const expected = {json.dumps(expected)};
                check(data.discount?.enabled && data.discount.product.id === {self.discount_product.id}, 'discount config missing');
                check(data.discount.tipProductId === {self.tip_product.id}, 'tip config missing');
                let count = 0;
                try {{
                    for (const id of [{self.discount_product_a.id}, {self.discount_product_b.id}, {self.tip_product.id}]) {{
                        const product = await waitFor(() => [...document.querySelectorAll('.product')].find(node => data.products.find(item => item.id === id)?.name === node.querySelector('strong')?.textContent && !node.disabled), 'discount source unavailable');
                        product.click();
                        count += 1;
                        await waitFor(() => document.querySelectorAll('aside .line').length === count, 'cart line missing');
                    }}
                    const discountButton = document.querySelector('[data-action-id="pos_discount_react.global_discount"]');
                    check(discountButton?.textContent === 'Giảm giá toàn đơn', `localized discount action missing: ${{discountButton?.textContent}}`);
                discountButton.click();
                let dialog = await waitFor(() => document.querySelector('[role="dialog"][aria-modal="true"]'), 'discount dialog missing');
                check(dialog.querySelector('label')?.textContent === 'Phần trăm giảm giá', 'localized dialog label missing');
                let input = dialog.querySelector('#pos-discount-percentage');
                    check(input && document.activeElement === input && input.min === '0' && input.max === '100', 'discount input semantics/focus mismatch');
                    const setInputValue = (node, value) => {{
                        Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(node, value);
                        node.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    }};
                    setInputValue(input, '');
                    dialog.querySelector('form').requestSubmit();
                    await waitFor(() => input.getAttribute('aria-invalid') === 'true' && dialog.querySelector('[role="alert"]')?.textContent === 'Phần trăm giảm giá phải từ 0 đến 100.', 'invalid discount error not announced');
                    check(document.querySelectorAll('aside .line').length === 3, 'invalid discount mutated cart');
                    setInputValue(input, '10');
                    dialog.querySelector('form').requestSubmit();
                    await waitFor(() => !document.querySelector('[role="dialog"]') && document.activeElement === discountButton, 'discount dialog did not close/restore focus');
                    await waitFor(() => document.querySelectorAll('aside .line').length === 5, `tax-grouped discount lines missing: cart=${{[...document.querySelectorAll('aside .line')].map(line => line.textContent).join('|')}}; recovery=${{document.querySelector('[aria-label="Recovery error"]')?.textContent || 'no recovery error'}}; discount=${{JSON.stringify(data.discount)}}`);
                    discountButton.click();
                    dialog = await waitFor(() => document.querySelector('[role="dialog"]'), 'discount dialog reopen failed');
                    dialog.dispatchEvent(new KeyboardEvent('keydown', {{ key: 'Escape', bubbles: true }}));
                    await waitFor(() => !document.querySelector('[role="dialog"]') && document.activeElement === discountButton, 'Escape did not close/restore focus');
                    const discountRows = [...document.querySelectorAll('aside .line')].filter(line => line.textContent.includes(data.discount.product.name));
                    check(discountRows.length === 2 && discountRows.every(line => !line.querySelector('button[aria-label^="Remove one"]')), 'discount line mutation control exposed');
                    check([...document.querySelectorAll('aside .line')].filter(line => !discountRows.includes(line)).every(line => line.querySelector('button[aria-label^="Remove one"]')), 'regular line mutation control missing');
                    const payCash = await waitFor(
                        () => [...document.querySelectorAll('button')].find(button => button.textContent === 'Pay cash' && !button.disabled),
                        'Pay cash unavailable after discount',
                    );
                    payCash.click();
                    const order = await waitFor(async () => {{
                        const orders = await posReact.rpc('pos.order', 'search_read', [[
                            ['session_id', '=', data.sessionId], ['state', '=', 'paid'], ['lines.product_id', '=', {self.discount_product.id}],
                        ], ['lines', 'payment_ids', 'amount_tax', 'amount_total', 'amount_paid'], 0, 1, 'id desc']);
                        return orders[0];
                    }}, 'paid discounted order missing');
                    const lines = await posReact.rpc('pos.order.line', 'search_read', [[['id', 'in', order.lines]], ['product_id', 'price_unit', 'tax_ids', 'price_subtotal', 'price_subtotal_incl']]);
                    const [payment] = await posReact.rpc('pos.payment', 'search_read', [[['id', 'in', order.payment_ids]], ['amount']]);
                    const discounts = lines.filter(line => line.product_id[0] === {self.discount_product.id});
                    check(discounts.length === 2 && discounts.every(line => line.price_unit < 0), `persisted discount lines mismatch: ${{JSON.stringify(lines)}}`);
                    check(lines.length === expected.lines.length && expected.lines.every(expectedLine => lines.some(line =>
                        line.product_id[0] === expectedLine.product_id &&
                        JSON.stringify([...line.tax_ids].sort((a, b) => a - b)) === JSON.stringify([...expectedLine.tax_ids].sort((a, b) => a - b)) &&
                        line.price_subtotal === expectedLine.subtotal && line.price_subtotal_incl === expectedLine.total,
                    )), `persisted line tax/totals mismatch: ${{JSON.stringify({{ lines, expected }})}}`);
                    check(order.amount_tax === expected.mapped_tax && order.amount_total === expected.total && order.amount_paid === expected.total && payment.amount === expected.total,
                        `persisted mapped tax/payment/order total mismatch: ${{JSON.stringify({{ order, payment, expected }})}}`);
                    check(expected.source_tax > order.amount_tax, `source tax was not discounted: ${{JSON.stringify({{ order, expected }})}}`);
                    console.log('POS React global discount checkout succeeded');
                }} finally {{ document.querySelector('[role="dialog"] button[type="button"]')?.click(); }}
            }})();
            """,
            "Boolean(document.querySelector('#pos-react-root .product') || document.querySelector('#pos-react-root[role=alert]'))",
            login="pos_user",
            success_signal="POS React global discount checkout succeeded",
        )
