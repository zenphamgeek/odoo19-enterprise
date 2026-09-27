# Part of Insilos. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models
from . import services
from . import wizard
from .schema import ensure_database_invariants
from .models.logistics_idp import _INTERNAL_POLICY_LOADER_TOKEN



def post_init_hook(env):
    env['logistics.idp.policy.source'].with_context(
        _logistics_policy_loader_token=_INTERNAL_POLICY_LOADER_TOKEN)._upgrade_effective_policy_history()
    env['logistics.idp.case']._upgrade_migration_service_principal()
    env['res.users']._normalize_legacy_saigon_timezone()
    ensure_database_invariants(env.cr)
