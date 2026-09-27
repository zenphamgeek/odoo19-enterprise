import json

from odoo.exceptions import AccessError

from .graph_identity import canonical_hash
from .graph_projection import GraphProjection


LOGISTICS_MODELS = (
    'logistics.idp.case', 'logistics.idp.document', 'logistics.idp.evidence',
    'logistics.idp.extraction.run', 'logistics.idp.check.result',
    'logistics.idp.policy.decision', 'logistics.idp.policy.source',
    'logistics.idp.supplier.profile', 'logistics.idp.po.snapshot',
    'logistics.idp.po.snapshot.line', 'logistics.idp.exception',
)


class LogisticsProjection:
    def __init__(self, env):
        self.env = env
        self.graph = GraphProjection(env)

    @property
    def available(self):
        return all(model in self.env.registry.models for model in LOGISTICS_MODELS)

    def project_case(self, case):
        if not self.available:
            return False
        case.ensure_one()
        case.check_access('read')
        company = case.company_id
        if company not in self.env.companies:
            raise AccessError('Logistics projection company is not allowed.')
        self.env['kg.node'].check_access('create')
        case_node = self.graph.project_node(company, case._name, case.id, {
            'source_system': case.source_system, 'source_key': case.source_key,
            'source_version': case.source_version, 'provenance': case.provenance,
        })
        for document in case.document_ids:
            document_node = self.graph.project_node(company, document._name, document.id, {
                'content_hash': document.content_hash, 'document_type': document.document_type,
                'version': document.version, 'status': document.status,
            })
            self.graph.project_edge(company, case_node, 'CONTAINS', document_node, {
                'source_type': 'LOGISTICS_DOCUMENT',
                'source_reference': '%s:%s' % (document._name, document.id),
                'source_hash': document.content_hash,
                'evidence_reference': 'sha256:%s' % document.content_hash,
                'derivation': 'DETERMINISTIC', 'state': 'VERIFIED', 'verified': True,
            })
            for run in document.extraction_run_ids:
                run_node = self.graph.project_node(company, run._name, run.id, {
                    'payload_hash': run.payload_hash, 'schema_version': run.schema_version,
                    'status': run.status,
                })
                self.graph.project_edge(company, document_node, 'REFERENCES', run_node, {
                    'source_type': 'LOGISTICS_EXTRACTION',
                    'source_reference': '%s:%s' % (run._name, run.id),
                    'source_hash': run.payload_hash,
                    'evidence_reference': 'sha256:%s' % run.payload_hash,
                    'confidence': run.confidence, 'derivation': 'AI_EXTRACTION',
                    'state': 'CANDIDATE', 'verified': False,
                })
        for evidence in case.evidence_ids:
            evidence_node = self.graph.project_node(company, evidence._name, evidence.id, {
                'payload_hash': evidence.payload_hash, 'category': evidence.category,
                'status': evidence.status,
            })
            verified = evidence.status == 'valid'
            self.graph.project_edge(company, case_node, 'SUPPORTED_BY', evidence_node, {
                'source_type': 'LOGISTICS_EVIDENCE',
                'source_reference': evidence.source_reference,
                'source_hash': evidence.payload_hash,
                'evidence_reference': 'sha256:%s' % evidence.payload_hash,
                'derivation': 'DETERMINISTIC',
                'state': 'VERIFIED' if verified else 'CANDIDATE', 'verified': verified,
            })
        for check in case.check_result_ids:
            check_node = self.graph.project_node(company, check._name, check.id, {
                'code': check.code, 'verdict': check.verdict,
            })
            self.graph.project_edge(company, case_node, 'SUBJECT_TO', check_node, {
                'source_type': 'LOGISTICS_CHECK',
                'source_reference': '%s:%s' % (check._name, check.id),
                'source_hash': check.payload_hash,
                'evidence_reference': 'sha256:%s' % check.payload_hash,
                'derivation': 'DETERMINISTIC', 'state': 'VERIFIED', 'verified': True,
            })
            if check.policy_source_id:
                policy_node = self.graph.project_node(company, check.policy_source_id._name, check.policy_source_id.id, {
                    'code': check.policy_source_id.code, 'version': check.policy_version,
                    'source_tier': check.policy_source_tier, 'citation': check.policy_citation,
                })
                self.graph.project_edge(company, check_node, 'BASED_ON', policy_node, {
                    'source_type': 'LOGISTICS_POLICY',
                    'source_reference': '%s:%s' % (check.policy_source_id._name, check.policy_source_id.id),
                    'source_hash': check.policy_hash,
                    'evidence_reference': 'sha256:%s' % check.policy_hash,
                    'derivation': 'DETERMINISTIC', 'state': 'VERIFIED', 'verified': True,
                })
        for decision in case.decision_ids:
            decision_node = self.graph.project_node(company, decision._name, decision.id, {
                'policy_code': decision.policy_code, 'policy_version': decision.policy_version,
                'verdict': decision.verdict,
            })
            self.graph.project_edge(company, case_node, 'SUBJECT_TO', decision_node, {
                'source_type': 'LOGISTICS_POLICY_DECISION',
                'source_reference': '%s:%s' % (decision._name, decision.id),
                'source_hash': decision.payload_hash,
                'evidence_reference': 'sha256:%s' % decision.payload_hash,
                'derivation': 'DETERMINISTIC', 'state': 'VERIFIED', 'verified': True,
            })
        for profile in self.env['logistics.idp.supplier.profile'].search([
                ('company_id', '=', company.id),
                ('supplier_reference', '=', case.supplier_reference)]):
            profile_node = self.graph.project_node(company, profile._name, profile.id, {
                'supplier_reference': profile.supplier_reference, 'profile_code': profile.profile_code,
                'version': profile.version,
            })
            self.graph.project_edge(company, case_node, 'PURCHASED_FROM', profile_node, {
                'source_type': 'LOGISTICS_SUPPLIER_PROFILE',
                'source_reference': '%s:%s' % (profile._name, profile.id),
                'source_hash': profile.payload_hash,
                'evidence_reference': 'sha256:%s' % profile.payload_hash,
                'derivation': 'DETERMINISTIC', 'state': 'VERIFIED', 'verified': True,
            })
        for snapshot in self.env['logistics.idp.po.snapshot'].search([
                ('company_id', '=', company.id),
                ('po_reference', '=', case.po_reference)]):
            snapshot_node = self.graph.project_node(company, snapshot._name, snapshot.id, {
                'po_reference': snapshot.po_reference, 'snapshot_date': str(snapshot.snapshot_date),
            })
            self.graph.project_edge(company, case_node, 'REFERENCES', snapshot_node, {
                'source_type': 'LOGISTICS_PO_SNAPSHOT',
                'source_reference': '%s:%s' % (snapshot._name, snapshot.id),
                'source_hash': snapshot.payload_hash,
                'evidence_reference': 'sha256:%s' % snapshot.payload_hash,
                'derivation': 'DETERMINISTIC', 'state': 'VERIFIED', 'verified': True,
            })
            payload = json.loads(snapshot.payload) if snapshot.payload else {}
            failures = {item['line_key'] for item in self.env['logistics.idp.po.snapshot']._material_validation_failures(
                company.id, snapshot.snapshot_date, payload.get('lines', []))}
            for line in snapshot.line_ids:
                line_payload = json.loads(line.payload) if line.payload else {}
                line_node = self.graph.project_node(company, line._name, line.id, {
                    'line_key': line.line_key, 'material_code': line.material_code,
                    'hs_code': line_payload.get('hs_code'),
                })
                verified = line.line_key not in failures
                self.graph.project_edge(company, snapshot_node, 'CONTAINS', line_node, {
                    'source_type': 'LOGISTICS_PO_LINE',
                    'source_reference': '%s:%s' % (line._name, line.id),
                    'source_hash': line.payload_hash,
                    'evidence_reference': 'sha256:%s' % line.payload_hash,
                    'derivation': 'DETERMINISTIC',
                    'state': 'VERIFIED' if verified else 'CANDIDATE', 'verified': verified,
                })
                line_identity = (line.line_key, line.material_code)
                matches = self.env['logistics.idp.check.result']
                if all(line_identity):
                    matches = case.check_result_ids.filtered(lambda check: (
                        json.loads(check.payload or '{}').get('line_key'),
                        json.loads(check.payload or '{}').get('material_code'),
                    ) == line_identity)
                if len(matches) == 1:
                    check = matches[0]
                    check_node = self.graph.project_node(company, check._name, check.id, {
                        'code': check.code, 'verdict': check.verdict,
                    })
                    lineage_hash = canonical_hash([line.payload_hash, check.payload_hash])
                    self.graph.project_edge(company, line_node, 'SUBJECT_TO', check_node, {
                        'source_type': 'LOGISTICS_PO_LINE_CHECK',
                        'source_reference': '%s:%s|%s:%s' % (line._name, line.id, check._name, check.id),
                        'source_hash': lineage_hash,
                        'evidence_reference': 'sha256:%s' % lineage_hash,
                        'derivation': 'DETERMINISTIC', 'state': 'VERIFIED', 'verified': True,
                    })
        for exception in case.exception_ids:
            exception_node = self.graph.project_node(company, exception._name, exception.id, {
                'exception_type': exception.exception_type, 'severity': exception.severity,
                'state': exception.state,
            })
            self.graph.project_edge(company, case_node, 'SUBJECT_TO', exception_node, {
                'source_type': 'LOGISTICS_EXCEPTION',
                'source_reference': '%s:%s' % (exception._name, exception.id),
                'source_hash': '%s:%s:%s' % (exception.exception_type, exception.state, exception.severity),
                'derivation': 'DETERMINISTIC', 'state': 'CANDIDATE', 'verified': False,
            })
        return case_node
