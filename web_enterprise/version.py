# -*- coding: utf-8 -*-
# Part of Insilos. See LICENSE file for full copyright and licensing details.

import insilos

# ----------------------------------------------------------
# Monkey patch release to set the edition as 'enterprise'
# ----------------------------------------------------------
insilos.release.version_info = insilos.release.version_info[:5] + ('e',)
if '+e' not in insilos.release.version:     # not already patched by packaging
    insilos.release.version = '{0}+e{1}{2}'.format(*insilos.release.version.partition('-'))
insilos.release.full_version = f"{insilos.release.version} (Build {insilos.release.build_id})"

insilos.service.common.RPC_VERSION_1.update(
    server_version=insilos.release.version,
    server_version_info=insilos.release.version_info,
    server_serie=insilos.release.serie,
    server_build_id=insilos.release.build_id,
    server_build_timestamp=insilos.release.build_timestamp,
    server_build_datetime=insilos.release.build_datetime,
    server_build_commit=insilos.release.build_commit,
    server_build_tag=insilos.release.build_tag,
    server_full_version=insilos.release.full_version,
)

