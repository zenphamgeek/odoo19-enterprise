import json
import re

from odoo import api, fields, models
from odoo.exceptions import AccessError, ValidationError, UserError


class TemplateRelease(models.Model):
    _name = 'insilos.template.release'
    _description = 'Template Release'
    _order = 'name desc, id desc'

    name = fields.Char(required=True)
    template_id = fields.Many2one('insilos.industry.template', required=True, ondelete='restrict')
    artifact_uri = fields.Char(required=True)
    artifact_sha256 = fields.Char(required=True, string='Artifact SHA-256')
    catalog_sha256 = fields.Char(required=True, string='Catalog SHA-256')
    module_manifest = fields.Text(required=True)
    required_entitlements = fields.Json(default=lambda self: ['enterprise'])
    conflicts = fields.Json(default=list)
    app_version = fields.Char(required=True)
    image_ref = fields.Char(required=True, string='Immutable Image Reference')
    postgres_version = fields.Char(required=True)
    schema_sha256 = fields.Char(required=True, string='Schema SHA-256')
    filestore_manifest_uri = fields.Char(required=True)
    test_evidence_uri = fields.Char(required=True)
    state = fields.Selection([('draft', 'Draft'), ('published', 'Published')], default='draft', required=True)
    notes = fields.Text()

    _release_unique = models.UniqueIndex('(template_id, name)', 'A template release name must be unique.')
    _release_artifact_unique = models.UniqueIndex('(template_id, artifact_sha256)', 'A template artifact can only have one release.')

    @api.constrains('artifact_sha256', 'catalog_sha256', 'schema_sha256', 'image_ref', 'artifact_uri', 'filestore_manifest_uri', 'test_evidence_uri')
    def _check_immutable_identifiers(self):
        for release in self:
            if any(not re.fullmatch(r'[0-9a-f]{64}', value or '') for value in (
                release.artifact_sha256, release.catalog_sha256, release.schema_sha256,
            )):
                raise ValidationError(self.env._('Release checksums must be lowercase SHA-256 values.'))
            if not re.fullmatch(r'.+@sha256:[0-9a-f]{64}', release.image_ref or ''):
                raise ValidationError(self.env._('Release image must be pinned by SHA-256 digest.'))
            if release.artifact_sha256 not in (release.artifact_uri or ''):
                raise ValidationError(self.env._('Artifact URI must contain its SHA-256 digest.'))
            for uri in (release.filestore_manifest_uri, release.test_evidence_uri):
                if not re.fullmatch(r'(?:s3|https)://[^?#]+/[0-9a-f]{64}(?:\.[a-z0-9.]+)?', uri or ''):
                    raise ValidationError(self.env._('Manifest and evidence URIs must be immutable and content-addressed.'))

    def _check_entitlement_contract(self, entitlements):
        self.ensure_one()
        try:
            manifest = set(json.loads(self.module_manifest))
        except (TypeError, ValueError):
            raise ValidationError(self.env._('Release module manifest must be a JSON list.'))
        if self.app_version != '19.0':
            raise ValidationError(self.env._('Release app version is not supported.'))
        if not set(self.required_entitlements or ()) <= set(entitlements):
            raise ValidationError(self.env._('Release entitlement is not satisfied.'))
        if manifest & set(self.conflicts or ()):
            raise ValidationError(self.env._('Release module manifest contains a conflict.'))
        return True

    def action_publish(self):
        if not self.env.user.has_group('insilos_tenant_control.group_tenant_operator'):
            raise AccessError(self.env._('Only tenant operators can publish releases.'))
        for release in self.filtered(lambda item: item.state == 'draft'):
            release._check_entitlement_contract({'enterprise'})
        self.filtered(lambda release: release.state == 'draft').write({'state': 'published'})

    def write(self, vals):
        if self.filtered(lambda release: release.state == 'published'):
            raise UserError(self.env._('Published template releases are immutable.'))
        return super().write(vals)

    def unlink(self):
        if self.filtered(lambda release: release.state == 'published'):
            raise UserError(self.env._('Published template releases are immutable.'))
        return super().unlink()
