# Part of Odoo. See LICENSE file for full copyright and licensing details.
from . import models


def post_init_hook(env):
    import logging

    from odoo import SUPERUSER_ID, api
    from odoo.upgrade import util

    _logger = logging.getLogger(__name__)

    env = api.Environment(env.cr, SUPERUSER_ID, {})

    if not util.module_installed(env.cr, "l10n_ve_binaural"):
        return

    _logger.info("Moving everything from l10n_ve_binaural to l10n_ve_lida")
    util.merge_module(env.cr, "l10n_ve_binaural", "l10n_ve_lida")
    
    if not util.module_installed(env.cr, "l10n_ve_binaural_pre"):
        return
    _logger.info("Moving everything from l10n_ve_binaural_pre to l10n_ve_lida")
    util.merge_module(env.cr, "l10n_ve_binaural_pre", "l10n_ve_lida")