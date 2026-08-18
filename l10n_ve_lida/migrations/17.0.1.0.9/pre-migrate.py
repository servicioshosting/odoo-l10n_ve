from odoo.upgrade import util


def migrate(cr, version):
    if util.module_installed(cr, "l10n_ve_tax_payer"):
        util.merge_module(cr, "l10n_ve_tax_payer", "l10n_ve_lida")