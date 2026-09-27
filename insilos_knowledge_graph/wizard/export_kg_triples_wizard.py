# -*- coding: utf-8 -*-
# Part of Insilos. See LICENSE file for full copyright and licensing details.

import base64
import csv
import io
import json
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ExportKGTriplesWizard(models.TransientModel):
    _name = 'kg.export.triples.wizard'
    _description = 'Export Knowledge Graph Triples & Entity Lineage'

    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, required=True)
    relation_filter = fields.Char(string='Filter Relation (Predicate)', help='Optional relation filter, e.g. HAS_SUPPLIER, HAS_ITEM')
    export_format = fields.Selection([
        ('jsonld', 'JSON-LD (Semantic Knowledge Graph)'),
        ('ntriples', 'N-Triples / RDF (<subject> <predicate> <object> .)'),
        ('csv', 'CSV Triple Table (Spreadsheet Analysis)'),
    ], string='Export Format', default='jsonld', required=True)

    file_data = fields.Binary(string='Downloaded File', readonly=True)
    file_name = fields.Char(string='File Name', readonly=True)
    is_exported = fields.Boolean(string='Export Completed', default=False)

    def action_export(self):
        self.ensure_one()
        domain = [('company_id', '=', self.company_id.id)]
        if self.relation_filter:
            domain.append(('relation', '=ilike', f"%{self.relation_filter}%"))

        edges = self.env['kg.edge'].search(domain)
        if not edges:
            raise UserError(_("No Knowledge Graph edges found for company %s.") % self.company_id.name)

        if self.export_format == 'csv':
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow([
                'Edge Hash', 'Subject Node URN', 'Subject Model', 'Relation (Predicate)',
                'Object Node URN', 'Object Model', 'Confidence', 'Verified',
                'Source Type', 'Source Reference', 'Source Hash', 'Evidence Reference'
            ])
            for edge in edges:
                writer.writerow([
                    edge.edge_hash or '',
                    edge.from_node_id.urn or '',
                    edge.from_node_id.source_model or '',
                    edge.relation or '',
                    edge.to_node_id.urn or '',
                    edge.to_node_id.source_model or '',
                    f"{edge.confidence:.2f}",
                    'TRUE' if edge.verified else 'FALSE',
                    edge.source_type or '',
                    edge.source_reference or '',
                    edge.source_hash or '',
                    edge.evidence_reference or ''
                ])
            raw_bytes = output.getvalue().encode('utf-8-sig')
            filename = f"KG_Triples_{self.company_id.id}_{fields.Date.today()}.csv"
            mimetype = 'text/csv'

        elif self.export_format == 'ntriples':
            output = io.StringIO()
            for edge in edges:
                subj = f"<{edge.from_node_id.urn}>"
                pred = f"<https://insilos.com/ontology/{edge.relation}>"
                obj = f"<{edge.to_node_id.urn}>"
                output.write(f"{subj} {pred} {obj} .\n")
            raw_bytes = output.getvalue().encode('utf-8')
            filename = f"KG_Triples_{self.company_id.id}_{fields.Date.today()}.nt"
            mimetype = 'application/n-triples'

        else:  # JSON-LD
            triples = []
            for edge in edges:
                triples.append({
                    "@id": edge.from_node_id.urn,
                    edge.relation: {
                        "@id": edge.to_node_id.urn,
                        "confidence": edge.confidence,
                        "verified": edge.verified,
                        "provenance": {
                            "source_type": edge.source_type,
                            "source_reference": edge.source_reference,
                            "source_hash": edge.source_hash,
                            "evidence_reference": edge.evidence_reference,
                        }
                    }
                })
            payload = {
                "@context": {
                    "insilos": "https://insilos.com/ontology/",
                    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
                    "xsd": "http://www.w3.org/2001/XMLSchema#",
                },
                "@graph": triples
            }
            raw_bytes = json.dumps(payload, indent=2, ensure_ascii=False).encode('utf-8')
            filename = f"KG_Triples_{self.company_id.id}_{fields.Date.today()}.jsonld"
            mimetype = 'application/ld+json'

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
