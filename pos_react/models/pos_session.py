from odoo import models, api


class PosSession(models.Model):
    _inherit = "pos.session"

    def load_data(self, models_to_load=None):
        self.ensure_one()
        if isinstance(models_to_load, list):
            params = {
                'models': models_to_load,
                'only_records': True,
            }
            requested_models = models_to_load
        elif isinstance(models_to_load, dict):
            params = models_to_load
            requested_models = models_to_load.get('models', [])
        else:
            params = {'only_records': True}
            requested_models = []

        data = super(
            PosSession,
            self.with_company(self.company_id),
        ).load_data(params)

        if not requested_models or "account.fiscal.position" in requested_models:
            fiscal_position = self.config_id.default_fiscal_position_id
            if "account.fiscal.position" in data:
                fp_data = data["account.fiscal.position"]
                records = fp_data if isinstance(fp_data, list) else fp_data.get("records", [])
                if fiscal_position and fiscal_position.id not in {
                    record["id"]
                    for record in records
                }:
                    records.extend(
                        fiscal_position._load_pos_data_read(
                            fiscal_position,
                            self.config_id,
                        )
                    )
        # Ensure all models in data have a valid string or int id on each record
        for model, records in data.items():
            if isinstance(records, list):
                for idx, r in enumerate(records, start=1):
                    if isinstance(r, dict) and not r.get("id"):
                        r["id"] = r.get("key") or r.get("uuid") or str(idx)

        alias_map = {
            'res.partner': ['rs.partner', 'party.master'],
            'res.company': ['rs.company', 'organization.unit'],
            'res.users': ['rs.users'],
            'res.country': ['rs.country'],
            'res.country.state': ['rs.country.state'],
            'res.currency': ['rs.currency'],
            'res.lang': ['rs.lang'],
        }
        for base_model, aliases in alias_map.items():
            if base_model in data:
                for alias in aliases:
                    if alias not in data:
                        data[alias] = data[base_model]

        return data

    @api.model
    def _load_pos_data_relations(self, model, fields):
        if model not in self.env:
            return {}
        model_fields = self.env[model]._fields
        relations = {}
        seen_m2m_tables = set()

        sorted_items = sorted(
            model_fields.items(),
            key=lambda item: (bool(getattr(item[1], "compute", False)), len(item[0]))
        )

        for name, params in sorted_items:
            if (name not in fields and len(fields)) or (getattr(params, "manual", False) and not len(fields)):
                continue

            field_type = getattr(params, "type", "char") or "char"
            comodel = getattr(params, "comodel_name", False)
            if not isinstance(comodel, str) or not comodel:
                comodel = False

            if comodel and field_type in ("many2one", "one2many", "many2many"):
                rel = {
                    "name": name,
                    "model": getattr(params, "model_name", model) or model,
                    "compute": bool(getattr(params, "compute", False)),
                    "related": bool(getattr(params, "related", False)),
                    "relation": comodel,
                    "type": field_type,
                }
                ondelete = getattr(params, "ondelete", False)
                if field_type == "many2one" and ondelete and isinstance(ondelete, str):
                    rel["ondelete"] = ondelete
                inverse_name = getattr(params, "inverse_name", False)
                if field_type == "one2many" and inverse_name and isinstance(inverse_name, str):
                    rel["inverse_name"] = inverse_name
                if field_type == "many2many":
                    relation_table = getattr(params, "relation", False)
                    m2m_key = (comodel, relation_table)
                    if relation_table and isinstance(relation_table, str) and m2m_key not in seen_m2m_tables:
                        rel["relation_table"] = relation_table
                        seen_m2m_tables.add(m2m_key)
                relations[name] = rel
            else:
                rel_type = field_type if field_type not in ("many2one", "one2many", "many2many") else "char"
                relations[name] = {
                    "name": name,
                    "type": rel_type,
                    "compute": bool(getattr(params, "compute", False)),
                    "related": bool(getattr(params, "related", False)),
                }

        if fields:
            for name in fields:
                if name not in relations:
                    relations[name] = {
                        "name": name,
                        "type": "char",
                        "compute": False,
                        "related": False,
                    }
        return relations

    def load_data_params(self, *args, **kwargs):
        session = self
        if not session and args and isinstance(args[0], int):
            session = self.browse(args[0])
        elif not session:
            session = self.search([], order='id desc', limit=1)
        session.ensure_one()

        response = {}
        fields = session._load_pos_data_fields(session.config_id)
        response['pos.session'] = {
            'fields': fields,
            'relations': session._load_pos_data_relations('pos.session', fields)
        }

        models_to_load = session._load_pos_data_models(session.config_id)
        for model in models_to_load:
            if model not in session.env:
                continue
            m_fields = session.env[model]._load_pos_data_fields(session.config_id)
            response[model] = {
                'fields': m_fields,
                'relations': session._load_pos_data_relations(model, m_fields)
            }

        alias_map = {
            'res.partner': ['rs.partner', 'party.master'],
            'res.company': ['rs.company', 'organization.unit'],
            'res.users': ['rs.users'],
            'res.country': ['rs.country'],
            'res.country.state': ['rs.country.state'],
            'res.currency': ['rs.currency'],
            'res.lang': ['rs.lang'],
        }
        for base_model, aliases in alias_map.items():
            if base_model in response:
                for alias in aliases:
                    if alias not in response:
                        response[alias] = dict(response[base_model])

        return response
