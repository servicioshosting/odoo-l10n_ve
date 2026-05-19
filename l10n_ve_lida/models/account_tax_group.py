# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import _, api, fields, models
from odoo.exceptions import UserError

from odoo.tools.sql import column_exists, create_column


class AccountTaxGroup(models.Model):
    _inherit = 'account.tax.group'

    ## GLOW FEAT :01:
    # Agregando _auto_init para que no de NULL sino => VAT
    def _auto_init(self):
        if not column_exists(self.env.cr, "account_tax_group", 'l10n_ve_type'):
            create_column(self.env.cr, "account_tax_group", 'l10n_ve_type', "varchar")
            self.env.cr.execute("""
                UPDATE account_tax_group
                SET l10n_ve_type = 'VAT'
            """)
        return super()._auto_init()
    ## GLOW FEAT :01:

    l10n_ve_type = fields.Selection([
        ('VAT', 'Impuesto al valor agregado'),
    ], string='Tipo de impuesto', index=True, readonly=True)
