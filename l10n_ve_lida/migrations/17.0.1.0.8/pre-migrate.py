from odoo.upgrade import util


def migrate(cr, version):
    if util.module_installed(cr, "l10n_ve_rate"):
        util.merge_module(cr, "l10n_ve_rate", "l10n_ve_lida")
