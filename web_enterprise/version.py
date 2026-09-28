# -*- coding: utf-8 -*-
# Part of Insilos. See LICENSE file for full copyright and licensing details.

import insilos

# ----------------------------------------------------------
# Monkey patch release to set the edition as 'enterprise'
# ----------------------------------------------------------
insilos.release.version_info = insilos.release.version_info[:5] + ('e',)
if '+e' not in insilos.release.version:     # not already patched by packaging
    insilos.release.version = '{0}+e{1}{2}'.format(*insilos.release.version.partition('-'))

insilos.service.common.RPC_VERSION_1.update(
    server_version=insilos.release.version,
    server_version_info=insilos.release.version_info)

