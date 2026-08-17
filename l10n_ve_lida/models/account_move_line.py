from odoo import fields, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    config_deductible_tax = fields.Boolean(related='company_id.config_deductible_tax')

    not_deductible_tax = fields.Boolean(default=False)
