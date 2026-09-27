# -*- coding: utf-8 -*-
# Part of Insilos. See LICENSE file for full copyright and licensing details.

import base64
import csv
import io
import json
import logging

from odoo import models, fields, api, _
from odoo.exceptions import AccessError, UserError

_logger = logging.getLogger(__name__)


class ESGExportScorecardWizard(models.TransientModel):
    _name = 'is.esg.export.scorecard.wizard'
    _description = 'Export ESG Facility Scorecards & Emissions Disclosures'

    reporting_year = fields.Integer(string='Reporting Year', default=lambda self: fields.Date.today().year, required=True)
    facility_ids = fields.Many2many('is.hse.facility', string='Industrial Facilities',
                                    help='Leave empty to export all facilities')
    export_format = fields.Selection([
        ('csv', 'CSV Dataset (Spreadsheet & Analysis)'),
        ('json', 'JSON Scorecard Export (ESG API)'),
    ], string='Export Format', default='csv', required=True)

    file_data = fields.Binary(string='Downloaded File', readonly=True)
    file_name = fields.Char(string='File Name', readonly=True)
    is_exported = fields.Boolean(string='Export Completed', default=False)

    def action_export(self):
        self.ensure_one()
        if not self.env.user.has_group('insilos_esg_bridge.group_esg_bridge_manager'):
            raise AccessError(_('Only ESG managers can export disclosures.'))
        domain = [('reporting_year', '=', self.reporting_year), ('state', '=', 'published')]
        if self.facility_ids:
            domain.append(('facility_id', 'in', self.facility_ids.ids))

        scorecards = self.env['is.esg.facility.scorecard'].search(domain)
        scorecards.check_access('read')
        scorecards.check_access_rule('read')
        if not scorecards:
            raise UserError(_("No ESG Scorecards found for year %d.") % self.reporting_year)
        for scorecard in scorecards:
            scorecard._check_source_provenance()

        if self.export_format == 'csv':
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow([
                'Scorecard Reference', 'Facility Name', 'Reporting Year', 'Period',
                'Scope 1 Direct GHG (tCO2e)', 'Scope 2 Indirect GHG (tCO2e)', 'Total Scope 1+2 (tCO2e)',
                'SO2 Emissions (kg)', 'NOx Emissions (kg)', 'TSP Dust (kg)',
                'Wastewater Discharged (m3)', 'Water Compliance (%)', 'Recycled Waste (%)',
                'LTIFR Rate', 'Internal Environmental Score (0-100)', 'Internal Scorecard Band',
                'Source URL', 'Source Version', 'Source Date', 'Evidence Summary',
                'Audited By', 'Audited At', 'Published By', 'Published At',
                'Workflow Status (published; not independently assured)'
            ])
            for sc in scorecards:
                writer.writerow([
                    sc.name or '',
                    sc.facility_id.name or '',
                    sc.reporting_year,
                    sc.reporting_period,
                    f"{sc.scope1_direct_co2e:.2f}",
                    f"{sc.scope2_indirect_co2e:.2f}",
                    f"{sc.total_scope1_2_co2e:.2f}",
                    f"{sc.cems_so2_emissions_kg:.1f}",
                    f"{sc.cems_nox_emissions_kg:.1f}",
                    f"{sc.cems_tsp_dust_kg:.1f}",
                    f"{sc.wastewater_discharged_m3:.1f}",
                    f"{sc.wastewater_compliance_pct:.1f}",
                    f"{sc.recycled_waste_percentage:.1f}",
                    f"{sc.ltifr_safety_rate:.2f}",
                    f"{sc.environmental_score:.1f}",
                    sc.sustainability_grade or '',
                    sc.source_url,
                    sc.source_version,
                    sc.source_date.isoformat(),
                    sc.evidence_summary or '',
                    sc.auditor_id.name or '',
                    sc.audited_at.isoformat() if sc.audited_at else '',
                    sc.publisher_id.name or '',
                    sc.published_at.isoformat() if sc.published_at else '',
                    sc.state or ''
                ])
            raw_bytes = output.getvalue().encode('utf-8-sig')
            filename = f"ESG_Scorecards_{self.reporting_year}.csv"
            mimetype = 'text/csv'
        else:
            payload = {
                "standard": "Insilos ESG scorecard export (not GRI/SASB-aligned or assured)",
                "reporting_year": self.reporting_year,
                "exported_at": fields.Datetime.now().isoformat(),
                "facility_count": len(scorecards),
                "scorecards": [{
                    "name": sc.name,
                    "facility": sc.facility_id.name,
                    "period": sc.reporting_period,
                    "source": {
                        "url": sc.source_url,
                        "version": sc.source_version,
                        "date": sc.source_date.isoformat(),
                    },
                    "governance": {
                        "evidence_summary": sc.evidence_summary,
                        "audited_by": sc.auditor_id.name,
                        "audited_at": sc.audited_at.isoformat() if sc.audited_at else None,
                        "published_by": sc.publisher_id.name,
                        "published_at": sc.published_at.isoformat() if sc.published_at else None,
                    },
                    "ghg_emissions": {
                        "scope1_direct_tco2e": sc.scope1_direct_co2e,
                        "scope2_indirect_tco2e": sc.scope2_indirect_co2e,
                        "total_scope1_2_tco2e": sc.total_scope1_2_co2e,
                    },
                    "cems_air_emissions_kg": {
                        "so2": sc.cems_so2_emissions_kg,
                        "nox": sc.cems_nox_emissions_kg,
                        "tsp": sc.cems_tsp_dust_kg,
                    },
                    "water_waste_metrics": {
                        "wastewater_m3": sc.wastewater_discharged_m3,
                        "water_compliance_pct": sc.wastewater_compliance_pct,
                        "recycled_waste_pct": sc.recycled_waste_percentage,
                    },
                    "safety_governance": {
                        "ltifr": sc.ltifr_safety_rate,
                        "environmental_score": sc.environmental_score,
                        "sustainability_grade": sc.sustainability_grade,
                        "state": sc.state,
                    }
                } for sc in scorecards]
            }
            raw_bytes = json.dumps(payload, indent=2, ensure_ascii=False).encode('utf-8')
            filename = f"ESG_Disclosures_{self.reporting_year}.json"
            mimetype = 'application/json'

        encoded = base64.b64encode(raw_bytes)
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': encoded,
            'mimetype': mimetype,
        })

        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%d?download=true' % attachment.id,
            'target': 'self',
        }
