import json

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

from .services.origin import canonical, digest, evaluate, rank_scenarios


class OriginRegime(models.Model):
    _name = 'preferential.origin.regime'
    _description = 'Preferential Origin Regime'

    name = fields.Char(required=True)
    code = fields.Char(required=True, index=True)
    version = fields.Char(required=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    destination_country_id = fields.Many2one('res.country', required=True)
    effective_from = fields.Date(required=True)
    effective_to = fields.Date()
    policy_hash = fields.Char(required=True, size=64)
    state = fields.Selection([('draft', 'Draft'), ('active', 'Active'), ('superseded', 'Superseded')], default='draft', required=True)


class OriginRule(models.Model):
    _name = 'preferential.origin.rule'
    _description = 'Preferential Origin Rule'

    regime_id = fields.Many2one('preferential.origin.regime', required=True, ondelete='restrict')
    company_id = fields.Many2one(related='regime_id.company_id', store=True)
    hs_from = fields.Char(required=True)
    hs_to = fields.Char(required=True)
    criterion = fields.Selection([(value, value) for value in ('WO', 'CC', 'CTH', 'CTSH', 'RVC', 'LVC', 'DE_MINIMIS', 'CUMULATION', 'PROCESS', 'CONSIGNMENT')], required=True)
    rule_json = fields.Json(required=True)
    rule_hash = fields.Char(compute='_compute_rule_hash', store=True)

    @api.depends('rule_json')
    def _compute_rule_hash(self):
        for record in self:
            record.rule_hash = digest(record.rule_json or {})

    def evaluate(self, facts):
        self.ensure_one()
        rule = dict(self.rule_json)
        rule.update(criterion=self.criterion, policy_hash=self.regime_id.policy_hash)
        return evaluate(rule, facts)


class OriginFormTemplate(models.Model):
    _name = 'preferential.origin.form.template'
    _description = 'Preferential Origin Working Paper Template'

    name = fields.Char(required=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    regime_id = fields.Many2one('preferential.origin.regime', required=True, ondelete='restrict')
    schema_json = fields.Json(required=True, default=dict)
    template_hash = fields.Char(compute='_compute_template_hash', store=True)
    effective_from = fields.Date(required=True)
    effective_to = fields.Date()
    state = fields.Selection([('draft', 'Draft'), ('active', 'Active'), ('superseded', 'Superseded')], default='draft', required=True)

    @api.depends('schema_json')
    def _compute_template_hash(self):
        for record in self:
            record.template_hash = digest(record.schema_json or {})


class OriginScenario(models.Model):
    _name = 'preferential.origin.scenario'
    _description = 'Preferential Origin Scenario'

    name = fields.Char(required=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    state = fields.Selection([('eligible', 'Eligible'), ('review', 'Review'), ('not_eligible', 'Not Eligible')], required=True, default='review')
    evidence_completeness = fields.Float()
    margin = fields.Float()
    cost = fields.Monetary()
    currency_id = fields.Many2one('res.currency', required=True, default=lambda self: self.env.company.currency_id)
    lead_time = fields.Float()
    selected = fields.Boolean()
    recommendation_rank = fields.Integer(compute='_compute_recommendation')
    explanation = fields.Char(compute='_compute_recommendation')

    def _compute_recommendation(self):
        for company in self.mapped('company_id'):
            scenarios = self.search([('company_id', '=', company.id)])
            values = [{'id': scenario.id, 'state': scenario.state,
                       'evidence_completeness': scenario.evidence_completeness,
                       'margin': scenario.margin, 'cost': scenario.cost,
                       'lead_time': scenario.lead_time} for scenario in scenarios]
            ranked = [item['id'] for item in rank_scenarios(values)]
            for scenario in scenarios:
                scenario.recommendation_rank = ranked.index(scenario.id) + 1
                scenario.explanation = '%s; evidence %.0f%%; margin %.2f; cost %.2f; lead time %.2f' % (
                    dict(scenario._fields['state'].selection).get(scenario.state),
                    scenario.evidence_completeness * 100, scenario.margin, scenario.cost, scenario.lead_time)

    @api.model
    def ranked_ids(self, records):
        records = records.filtered(lambda scenario: scenario.company_id == self.env.company)
        values = [{'id': record.id, 'state': record.state, 'evidence_completeness': record.evidence_completeness,
                   'margin': record.margin, 'cost': record.cost, 'lead_time': record.lead_time} for record in records]
        return [item['id'] for item in rank_scenarios(values)]


class OriginAssessment(models.Model):
    _name = 'preferential.origin.assessment'
    _description = 'Preferential Origin Assessment'

    name = fields.Char(required=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    production_id = fields.Many2one('mrp.production', ondelete='restrict')
    scope_key = fields.Char(required=True, index=True)
    state = fields.Selection([('planned', 'Planned'), ('terminal', 'Terminal')], required=True, default='planned')
    outcome = fields.Selection([('PASS', 'Pass'), ('BLOCK', 'Block'), ('REVIEW', 'Review'), ('NOT_APPLICABLE', 'Not Applicable')], default='REVIEW', required=True)
    reason_code = fields.Char(required=True, default='MISSING_APPROVED_POLICY')
    snapshot = fields.Json(required=True, default=dict)
    snapshot_hash = fields.Char(compute='_compute_snapshot_hash', store=True)

    _scope_unique = models.Constraint('unique(company_id, scope_key)', 'Assessment scope must be idempotent.')

    @api.depends('snapshot')
    def _compute_snapshot_hash(self):
        for record in self:
            record.snapshot_hash = digest(record.snapshot or {})

    def write(self, values):
        if any(record.state == 'terminal' for record in self):
            raise UserError('Terminal origin assessments are immutable.')
        return super().write(values)


class OriginAssessmentLine(models.Model):
    _name = 'preferential.origin.assessment.line'
    _description = 'Preferential Origin Actual Consumption Line'

    assessment_id = fields.Many2one('preferential.origin.assessment', required=True, ondelete='cascade')
    company_id = fields.Many2one(related='assessment_id.company_id', store=True)
    move_line_id = fields.Many2one('stock.move.line', required=True, ondelete='restrict')
    product_id = fields.Many2one('product.product', required=True, ondelete='restrict')
    lot_id = fields.Many2one('stock.lot', ondelete='restrict')
    quantity = fields.Float(required=True)
    uom_id = fields.Many2one('uom.uom', required=True, ondelete='restrict')
    finished_move_line_ids = fields.Many2many('stock.move.line', relation='preferential_origin_line_finished_rel')


class OriginWorkingPaper(models.Model):
    _name = 'preferential.origin.working.paper'
    _description = 'Preferential Origin Working Paper Draft'

    name = fields.Char(required=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    assessment_id = fields.Many2one('preferential.origin.assessment', required=True, ondelete='restrict')
    template_id = fields.Many2one('preferential.origin.form.template', required=True, ondelete='restrict')
    template_hash = fields.Char(required=True, size=64, readonly=True)
    values_json = fields.Json(required=True, default=dict)
    lineage_json = fields.Json(required=True, default=dict)
    missing_fields_json = fields.Json(required=True, default=list, readonly=True)
    state = fields.Selection([('draft', 'Draft'), ('complete', 'Complete')], default='draft', required=True, readonly=True)
    watermark = fields.Char(default='DRAFT — NOT A CERTIFICATE OF ORIGIN', required=True, readonly=True)

    @api.model_create_multi
    def create(self, values_list):
        for values in values_list:
            template = self.env['preferential.origin.form.template'].browse(values['template_id'])
            assessment = self.env['preferential.origin.assessment'].browse(values['assessment_id'])
            if template.state != 'active' or assessment.company_id != template.company_id:
                raise ValidationError('An active same-company template is required.')
            values['company_id'] = assessment.company_id.id
            values['template_hash'] = template.template_hash
            required = template.schema_json.get('required_fields', [])
            values['missing_fields_json'] = sorted(field for field in required if not values.get('values_json', {}).get(field))
        papers = super().create(values_list)
        papers._check_completeness()
        return papers

    def _check_completeness(self):
        for paper in self:
            required = paper.template_id.schema_json.get('required_fields', [])
            missing = sorted(field for field in required if not paper.values_json.get(field))
            paper.with_context(checking_completeness=True).write({
                'missing_fields_json': missing,
                'state': 'draft' if missing else 'complete',
            })

    def write(self, values):
        if any(key in values for key in ('watermark', 'template_hash', 'assessment_id', 'template_id')):
            raise UserError('Working paper binding and watermark are immutable.')
        result = super().write(values)
        if 'values_json' in values and not self.env.context.get('checking_completeness'):
            self._check_completeness()
        return result


class OriginActivation(models.Model):
    _name = 'preferential.origin.activation'
    _description = 'Preferential Origin Internal Activation Review'

    regime_id = fields.Many2one('preferential.origin.regime', required=True, ondelete='restrict')
    company_id = fields.Many2one(related='regime_id.company_id', store=True)
    maker_id = fields.Many2one('res.users', required=True, readonly=True)
    checker_id = fields.Many2one('res.users', readonly=True)
    payload_hash = fields.Char(required=True, size=64, readonly=True)
    preview_hash = fields.Char(required=True, size=64, readonly=True)
    state = fields.Selection([('submitted', 'Submitted'), ('approved_internal', 'Approved Internal'), ('rejected', 'Rejected')], default='submitted', required=True, readonly=True)

    _different_actors = models.Constraint('check(checker_id IS NULL OR maker_id <> checker_id)', 'Maker and checker must differ.')

    @api.model
    def submit(self, regime, preview):
        if regime.state != 'draft':
            raise ValidationError('Only a draft regime can be submitted.')
        payload = {'code': regime.code, 'version': regime.version, 'policy_hash': regime.policy_hash,
                   'company_id': regime.company_id.id}
        return self.create({'regime_id': regime.id, 'maker_id': self.env.user.id,
                            'payload_hash': digest(payload), 'preview_hash': digest(preview)})

    def check(self, approve, payload_hash, preview_hash):
        self.ensure_one()
        if self.env.user == self.maker_id:
            raise UserError('Maker and checker must differ.')
        if (payload_hash, preview_hash) != (self.payload_hash, self.preview_hash):
            raise ValidationError('Exact payload and preview hashes are required.')
        self.write({'checker_id': self.env.user.id, 'state': 'approved_internal' if approve else 'rejected'})
        return self


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    preferential_origin_scenario_id = fields.Many2one('preferential.origin.scenario', copy=False)

    def action_confirm(self):
        result = super().action_confirm()
        assessments = self.env['preferential.origin.assessment']
        for production in self.filtered('preferential_origin_scenario_id'):
            scope = 'planned:%s' % production.id
            if not assessments.search_count([('company_id', '=', production.company_id.id), ('scope_key', '=', scope)]):
                assessments.create({'name': scope, 'company_id': production.company_id.id,
                                    'production_id': production.id, 'scope_key': scope,
                                    'snapshot': {'bom_id': production.bom_id.id,
                                                 'scenario_id': production.preferential_origin_scenario_id.id}})
        return result

    def button_mark_done(self):
        result = super().button_mark_done()
        assessments = self.env['preferential.origin.assessment']
        lines = self.env['preferential.origin.assessment.line']
        for production in self.filtered(lambda mo: mo.state == 'done' and mo.preferential_origin_scenario_id):
            scope = 'actual:%s' % production.id
            if assessments.search_count([('company_id', '=', production.company_id.id), ('scope_key', '=', scope)]):
                continue
            raw_lines = production.move_raw_ids.filtered(lambda move: move.state == 'done').move_line_ids
            finished_lines = production.move_finished_ids.filtered(lambda move: move.state == 'done').move_line_ids
            snapshot = {
                'bom_id': production.bom_id.id,
                'scenario_id': production.preferential_origin_scenario_id.id,
                'raw_move_line_ids': sorted(raw_lines.ids),
                'finished_move_line_ids': sorted(finished_lines.ids),
                'finished_lot_ids': sorted(finished_lines.lot_id.ids),
            }
            assessment = assessments.create({
                'name': scope, 'company_id': production.company_id.id,
                'production_id': production.id, 'scope_key': scope,
                'state': 'planned', 'outcome': 'REVIEW',
                'reason_code': 'MISSING_APPROVED_POLICY', 'snapshot': snapshot,
            })
            for move_line in raw_lines:
                linked_finished = finished_lines.filtered(lambda line: move_line in line.consume_line_ids)
                lines.create({
                    'assessment_id': assessment.id, 'move_line_id': move_line.id,
                    'product_id': move_line.product_id.id, 'lot_id': move_line.lot_id.id,
                    'quantity': move_line.quantity, 'uom_id': move_line.product_uom_id.id,
                    'finished_move_line_ids': [(6, 0, linked_finished.ids)],
                })
            assessment.write({'state': 'terminal'})
        return result
