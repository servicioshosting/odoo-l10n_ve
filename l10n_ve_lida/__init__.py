# Part of Odoo. See LICENSE file for full copyright and licensing details.
from . import models


def post_init_hook(env):
    from odoo import api, SUPERUSER_ID
    from odoo.upgrade import util

    env = api.Environment(env.cr, SUPERUSER_ID, {})

    if not util.module_installed(env.cr, "l10n_ve_binaural"):
        return

    util.rename_module(env.cr, "l10n_ve_binaural", "l10n_ve_lida")
    util.uninstall_module(env.cr, "l10n_ve_binaural")
    
    if not util.module_installed(env.cr, "l10n_ve_binaural_pre"):
        return
    util.rename_module(env.cr, "l10n_ve_binaural_pre", "l10n_ve_lida")
    util.uninstall_module(env.cr, "l10n_ve_binaural_pre")