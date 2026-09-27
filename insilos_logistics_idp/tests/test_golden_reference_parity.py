# -*- coding: utf-8 -*-
"""
Synthetic schema and taxonomy regression suite for Insilos Logistics IDP.
Verifies deterministic local schema/extraction behavior; it does not establish external reference parity.
"""

import json
import unittest
from ..services.document_processor import SyntheticDocumentProcessor, IAPDocumentProcessor, extraction_response_schema, _semantic_diagnostics
from ..services.document_schemas import DOCUMENT_TYPES, validate

class TestGoldenReferenceParity(unittest.TestCase):

    def setUp(self):
        super().setUp()
        self.processor = SyntheticDocumentProcessor()

    def test_01_all_srs_seven_document_types_registered(self):
        """Assert all 7 core document groups in SRS v1.4 exist in DOCUMENT_TYPES."""
        required_types = {
            'purchase_order',
            'draft_vat_invoice',
            'main_vat_invoice',
            'sales_invoice',
            'commercial_invoice',
            'packing_list',
            'warehouse_release',
            'export_declaration_draft',
            'export_declaration_final',
            'import_declaration',
            'customs_declaration',
            'manifest',
            'bill_of_lading',
            'e11', 'e13', 'e15'
        }
        for doc_type in required_types:
            self.assertIn(doc_type, DOCUMENT_TYPES, f"Missing core document type: {doc_type}")

    def test_02_purchase_order_parity_extraction(self):
        """Test purchase order extraction parity with Reference App golden sample."""
        sample_payload = {
            "supplier": "CTY TNHH CONG NGHE THIET BI LOC MIEN NAM",
            "supplier_address": "93A Street No. 59, An Hoi Tay Ward, Ho Chi Minh City Vietnam",
            "supplier_number": "144750",
            "po_reference": "4000245142",
            "document_date": "2026-08-12",
            "currency": "VND",
            "total_value": "1500000",
            "lines": [
                {
                    "description": 'Filter for Washing line - BDM 10"-1um',
                    "quantity": "30",
                    "unit_price": "25000",
                    "uom": "PCE",
                    "value": "750000"
                },
                {
                    "description": 'Filter for Washing line - BDM 10"-10um',
                    "quantity": "30",
                    "unit_price": "25000",
                    "uom": "PCE",
                    "value": "750000"
                }
            ]
        }
        validated, warnings = validate('purchase_order', sample_payload, with_warnings=True, allow_review=True)
        self.assertEqual(validated['po_reference'], '4000245142')
        self.assertEqual(validated['document_date'], '2026-08-12')
        self.assertEqual(validated['currency'], 'VND')
        self.assertEqual(len(validated['lines']), 2)
        self.assertEqual(warnings, [])

    def test_03_vat_invoice_parity_extraction(self):
        """Test VAT Invoice extraction parity with Reference App golden sample."""
        sample_payload = {
            "supplier": "CÔNG TY TNHH MỘT THÀNH VIÊN THIẾT BỊ VIỆT TIẾN PHÁT",
            "invoice_number": "00000045",
            "invoice_serial": "1C26TTP",
            "document_date": "18/06/2026",
            "total_gross": "8000000",
            "lines": [
                {
                    "description": "DÂY CƯỚC 4.0 - 951814",
                    "quantity": "40",
                    "unit_price": "35000",
                    "uom": "Cuộn",
                    "value": "1400000"
                }
            ]
        }
        validated, warnings = validate('main_vat_invoice', sample_payload, with_warnings=True, allow_review=True)
        self.assertEqual(validated['invoice_number'], '00000045')
        self.assertEqual(validated['document_date'], '2026-06-18')
        self.assertEqual(len(validated['lines']), 1)

    def test_04_date_formats_parity(self):
        """Test normalization for Vietnamese date formats (DD/MM/YYYY, DD.MM.YYYY, YYYY-MM-DD)."""
        for raw_date, expected_iso in [
            ("12.08.2026", "2026-08-12"),
            ("18/06/2026", "2026-06-18"),
            ("2026-07-31", "2026-07-31")
        ]:
            validated = validate('purchase_order', {
                'supplier': 'S', 'supplier_address': 'A', 'supplier_number': '1',
                'po_reference': 'PO1', 'total_value': '100', 'currency': 'VND',
                'lines': [], 'document_date': raw_date
            }, allow_review=True)
            self.assertEqual(validated['document_date'], expected_iso)
