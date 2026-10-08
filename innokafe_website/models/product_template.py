# -*- coding: utf-8 -*-
import json
import logging
from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class ProductAttribute(models.Model):
    _inherit = 'product.attribute'

    # Explicitly bind to PostgreSQL table and column names to ensure compatibility
    # with the database schema under sovereign table mappings
    product_tmpl_ids = fields.Many2many(
        comodel_name='product.template',
        relation='product_attribute_product_template_rel',
        column1='product_attribute_id',
        column2='product_template_id',
        string="Related Products",
        compute='_compute_products',
        store=True,
    )


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    innokafe_elevation = fields.Char(
        string="Độ cao (masl)",
        help="Độ cao nông trại canh tác so với mực nước biển (ví dụ: 1.620 masl)",
    )
    innokafe_varietal = fields.Char(
        string="Giống hạt (Varietal)",
        help="Dòng giống sinh học của cây cà phê (ví dụ: Robusta Sẻ, Arabica Bourbon)",
    )
    innokafe_process = fields.Selection(
        selection=[
            ('natural', "Natural"),
            ('honey', "Honey"),
            ('washed', "Washed"),
        ],
        string="Phương pháp sơ chế",
        help="Phương pháp chế biến quả cà phê: Natural (Khô), Honey (Mật ong/Bán ướt), Washed (Ướt kiểm soát)",
    )
    innokafe_cupping_score = fields.Float(
        string="Điểm SCA Cupping",
        digits=(4, 2),
        help="Điểm số đánh giá chất lượng thử nếm theo chuẩn Hiệp hội Cà phê Đặc sản Quốc tế (SCA)",
    )
    innokafe_roast_level = fields.Selection(
        selection=[
            ('light', "Light Roast"),
            ('medium', "Medium Roast"),
            ('dark', "Dark Roast"),
        ],
        string="Cấp độ rang",
        help="Cấp độ rang mộc thủ công: Light Roast (Sáng), Medium Roast (Vừa), Dark Roast (Đậm vừa)",
    )
    innokafe_tasting_notes = fields.Char(
        string="Tasting Notes",
        help="Hương vị chủ đạo khi thưởng thức (ví dụ: Sô-cô-la đen, Hoa nhài, Caramel)",
    )
    innokafe_sensory_vector = fields.Char(
        string="Sensory Vector JSON",
        help="Dữ liệu vector 6 trục biểu đồ cảm quan Sensory Wheel dạng JSON string",
    )

    def get_innokafe_sensory_dict(self):
        """Return the parsed 6-axis sensory scores dictionary."""
        self.ensure_one()
        if self.innokafe_sensory_vector:
            try:
                return json.loads(self.innokafe_sensory_vector)
            except Exception as e:
                _logger.warning("Error parsing sensory vector for product %s: %s", self.id, e)
        return {
            "aroma": 8.0,
            "acidity": 6.0,
            "body": 8.0,
            "sweetness": 8.0,
            "cleancup": 8.5,
            "aftertaste": 8.0,
        }

    @api.model
    def _innokafe_setup_variant_prices(self):
        """Configure attribute price extras and publish variants for Innokafe products."""
        price_extra_map = {
            'INNO-ROBUSTA-NAT-01': {
                '500g': 110000.0,
                '1kg': 315000.0,
            },
            'INNO-ARABICA-WASH-02': {
                '500g': 165000.0,
                '1kg': 475000.0,
            },
            'INNO-SIGNATURE-HONEY-03': {
                '500g': 140000.0,
                '1kg': 395000.0,
            },
            'INNO-COLDBREW-CITRUS-05': {
                '500g': 155000.0,
                '1kg': 445000.0,
            },
            'INNO-HORECA-BARISTA-06': {
                '500g': 100000.0,
                '1kg': 265000.0,
            },
        }
        for default_code, extras in price_extra_map.items():
            tmpl = self.search([('default_code', '=', default_code)], limit=1)
            if not tmpl:
                continue
            for ptav in tmpl.attribute_line_ids.product_template_value_ids:
                val_name = ptav.product_attribute_value_id.name
                if val_name in extras:
                    ptav.price_extra = extras[val_name]
        return True
