import json

from odoo import tools
from odoo.addons.insilos_logistics_idp.tests.development_uat_harness import run_orm_corpus

DB = "insilos_migration_digiforce_v2"


def run(env):
    if env.cr.dbname != DB:
        raise AssertionError("DB mismatch: expected %s" % DB)
    company = env["res.company"].create({"name": "Logistics UAT Evidence"})
    operator = env["res.users"].create({
        "name": "Logistics UAT Operator", "login": "logistics_uat_operator",
        "company_id": company.id, "company_ids": [(6, 0, [company.id])],
        "group_ids": [(4, env.ref("insilos_logistics_idp.group_logistics_operator").id)],
    })
    policies = env["logistics.idp.policy.source"].search(
        [("code", "=", "TRADE_COMPLIANCE_VN_REFERENCE")], order="effective_from desc, id desc")
    policy = next((item for item in policies if isinstance(json.loads(item.payload).get("horizontal", {}).get(
        "extraction", {}).get("critical_fields"), dict)), env["logistics.idp.policy.source"])
    if not policy:
        raise AssertionError("UAT policy fixture unavailable")
    env["logistics.idp.policy.source"]._controlled_create({
        "code": policy.code, "version": policy.version, "company_id": company.id,
        "jurisdiction": policy.jurisdiction, "regime": policy.regime, "source_tier": policy.source_tier,
        "citation": policy.citation, "provenance": policy.provenance, "effective_from": policy.effective_from,
        "effective_to": policy.effective_to, "expected_refresh_hours": policy.expected_refresh_hours,
        "stale_after_hours": policy.stale_after_hours, "last_successful_sync_at": policy.last_successful_sync_at,
        "stale_disposition": policy.stale_disposition, "state": "active", "payload": policy.payload,
    }, "test_fixture")
    return run_orm_corpus(env["logistics.idp.case"].with_company(company).env, operator, write_result=True)


test_enable = tools.config["test_enable"]
try:
    tools.config["test_enable"] = True
    result = run(env)
    print("UAT regenerated: detailed=%s golden=%s" % (result["detailed_case_counts"], result["golden_counts"]))
finally:
    tools.config["test_enable"] = test_enable
    env.cr.rollback()
