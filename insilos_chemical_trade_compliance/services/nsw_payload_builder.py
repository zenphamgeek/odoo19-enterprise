# -*- coding: utf-8 -*-
# Part of Insilos. See LICENSE file for full copyright and licensing details.

from datetime import date, datetime
from math import isfinite
from xml.etree import ElementTree as ET


class NSWChemicalPayloadBuilder:
    """Build NSW declaration payloads from explicit consignment data."""

    @staticmethod
    def build_json_payload(dossier):
        def required(value, field):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"Missing required NSW field: {field}")
            return value

        def number(value, field, maximum=None):
            if (isinstance(value, bool) or not isinstance(value, (int, float))
                    or not isfinite(value) or value <= 0
                    or (maximum is not None and value > maximum)):
                raise ValueError(f"Invalid NSW numeric field: {field}")
            return value

        company = dossier.importer_company_id
        partner = dossier.partner_id
        if not company or not partner:
            raise ValueError("NSW importer and exporter are required")
        if not dossier.line_ids:
            raise ValueError("NSW chemical items are required")
        required(dossier.jurisdiction, 'jurisdiction')
        try:
            invoice_date = date.fromisoformat(str(dossier.invoice_date)).isoformat()
        except (TypeError, ValueError):
            raise ValueError("Valid NSW invoice_date is required") from None
        payload = {
            "header": {
                "procedure_code": required(dossier.nsw_procedure_code, 'procedure_code'),
                "dossier_id": required(dossier.name, 'dossier_id'),
                "created_at": datetime.now().isoformat(),
                "dossier_type": required(dossier.dossier_type, 'dossier_type'),
                "importer": {
                    "tax_code": required(company.vat, 'importer.tax_code'),
                    "company_name": required(company.name, 'importer.company_name'),
                    "address": required(company.street, 'importer.address'),
                    "phone": company.phone or "",
                    "email": company.email or "",
                },
                "exporter": {
                    "company_name": required(partner.name, 'exporter.company_name'),
                    "country_code": required(partner.country_id.code if partner.country_id else None, 'exporter.country_code'),
                    "address": required(partner.street, 'exporter.address'),
                },
                "customs_office_code": required(dossier.customs_office_code, 'customs_office_code'),
                "port_of_loading": required(dossier.port_of_loading, 'port_of_loading'),
                "port_of_discharge": required(dossier.port_of_discharge, 'port_of_discharge'),
                "invoice_number": required(dossier.invoice_number, 'invoice_number'),
                "invoice_date": invoice_date,
                "total_net_weight_kg": 0,
            },
            "chemical_items": [],
        }
        for idx, line in enumerate(dossier.line_ids, start=1):
            item = {
                "item_no": idx,
                "trade_name": required(line.trade_name, f'item {idx}.trade_name'),
                "chemical_name": line.chemical_substance_id.name if line.chemical_substance_id else line.trade_name,
                "cas_number": required(line.cas_number or (line.chemical_substance_id.cas_number if line.chemical_substance_id else None), f'item {idx}.cas_number'),
                "hs_code": required(line.hs_code, f'item {idx}.hs_code'),
                "concentration_pct": number(line.concentration_percentage, f'item {idx}.concentration_pct', 100),
                "net_weight_kg": number(line.net_weight_kg, f'item {idx}.net_weight_kg'),
                "package_type": required(line.package_type, f'item {idx}.package_type'),
                "package_quantity": number(line.quantity, f'item {idx}.package_quantity'),
                "intended_use": required(line.intended_use, f'item {idx}.intended_use'),
                "regulatory_status": line.regulatory_status,
                "sds_attached": bool(line.chemical_substance_id and line.chemical_substance_id.sds_ids),
                "permit_number": line.permit_id.permit_number if line.permit_id else None,
            }
            payload["chemical_items"].append(item)
            payload["header"]["total_net_weight_kg"] += item["net_weight_kg"]
        number(payload["header"]["total_net_weight_kg"], 'total_net_weight_kg')
        return payload

    @staticmethod
    def build_xml_payload(dossier):
        json_data = NSWChemicalPayloadBuilder.build_json_payload(dossier)
        root = ET.Element("NSWChemicalDeclaration", version="2.0")
        hdr = ET.SubElement(root, "Header")
        for k, v in json_data["header"].items():
            if isinstance(v, dict):
                sub = ET.SubElement(hdr, k)
                for sub_k, sub_v in v.items():
                    ET.SubElement(sub, sub_k).text = str(sub_v)
            else:
                ET.SubElement(hdr, k).text = str(v)
        items_el = ET.SubElement(root, "ChemicalItems")
        for item in json_data["chemical_items"]:
            item_el = ET.SubElement(items_el, "Item")
            for k, v in item.items():
                ET.SubElement(item_el, k).text = str(v) if v is not None else ""
        return ET.tostring(root, encoding="utf-8", xml_declaration=True).decode("utf-8")
