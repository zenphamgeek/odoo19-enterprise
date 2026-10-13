# -*- coding: utf-8 -*-
# Part of InnoKafe Specialty Coffee Suite. See LICENSE file for full copyright and licensing details.

"""
Pricelist Item Core Compatibility Guard
=============================================================================
In Odoo 20 core, `ProductPricelistItem._compute_price_before_discount` invokes
`_compute_base_price(*args, **kwargs)` passing up to 5 positional arguments
(product, quantity, uom, date, currency).
When `_compute_base_price` declares keyword-only parameters `*, currency=None, date=False`,
a TypeError is triggered:
    "ProductPricelistItem._compute_base_price() takes 4 positional arguments but 6 were given"

This patch guarantees safe positional argument unpacking (`args[0]` -> `date`, `args[1]` -> `currency`)
across all execution paths and Docker container image lifecycles without any schema (DDL) changes.
=============================================================================
"""

from odoo.addons.product.models.product_pricelist_item import ProductPricelistItem

_orig_compute_base_price = ProductPricelistItem._compute_base_price


def _safe_compute_base_price(
    self, product, quantity, uom, *args, currency=None, date=False, depth=0, base_prices=None, **kwargs
):
    if len(args) >= 1 and not date:
        date = args[0]
    if len(args) >= 2 and not currency:
        currency = args[1]
    return _orig_compute_base_price(
        self,
        product,
        quantity,
        uom,
        currency=currency,
        date=date,
        depth=depth,
        base_prices=base_prices,
        **kwargs,
    )


ProductPricelistItem._compute_base_price = _safe_compute_base_price
