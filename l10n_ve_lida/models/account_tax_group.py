# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AccountTaxGroup(models.Model):
    _inherit = 'account.tax.group'

    l10n_ve_type = fields.Selection([
        ('VAT', 'Impuesto al valor agregado'),
    ], string='Tipo de impuesto', index=True, readonly=True)
