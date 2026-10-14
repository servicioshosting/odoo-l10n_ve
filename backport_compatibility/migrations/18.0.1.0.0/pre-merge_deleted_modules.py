import logging

from odoo import SUPERUSER_ID, api
from odoo.upgrade import util

_logger = logging.getLogger(__name__)

# Modules removed from the tree for 18.0 — see MIGRATION-18.md §0.1 / OpenUpgrade map.
MODULES_TO_REMOVE = [
    "l10n_binaural",
    "l10n_ve_binaural",
    "l10n_ve_binaural_pre",
    "l10n_ve_base",
    "l10n_ve_rate",
    "l10n_ve_tax",
    "l10n_ve_tax_payer",
    "l10n_ve_igtf",
    "l10n_ve_igtf_extensions",
    "l10n_ve_location_extensions",
    "l10n_ve_contact_extensions",
    "l10n_ve_payment_extension",
    "l10n_ve_withholding_extensions",
]


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    for old_module in MODULES_TO_REMOVE:
        if not util.module_installed(env.cr, old_module):
            _logger.info(
                "[backport_compatibility] %s not installed, skip remove", old_module
            )
            continue
        _logger.info("[backport_compatibility] Removing %s...", old_module)
        util.remove_module(env.cr, old_module)
        env.cr.commit()
