# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.tools.float_utils import float_round


class ResCurrency(models.Model):
    _inherit = 'res.currency'

    l10n_ve_is_foreign_currency = fields.Boolean(
        "Es divisa extranjera",
        compute="_compute_l10n_ve_is_foreign_currency",
        readonly=True,
        store=True
    )

    @api.depends('name')
    def _compute_l10n_ve_is_foreign_currency(self):
        for rec in self:
            rec.l10n_ve_is_foreign_currency = not rec.name.startswith("VE")

class ResCurrencyRate(models.Model):
    _inherit = 'res.currency.rate'

    def _compute_company_rate(self):
        super()._compute_company_rate()
        digits = self.env['decimal.precision'].precision_get('Tasa')
        for currency_rate in self:
            if currency_rate.company_rate and currency_rate.company_rate > 1:
                currency_rate.company_rate = float_round(currency_rate.company_rate, precision_digits=digits)

    def _compute_inverse_company_rate(self):
        super()._compute_inverse_company_rate()
        digits = self.env['decimal.precision'].precision_get('Tasa')
        for currency_rate in self:
            if currency_rate.inverse_company_rate and currency_rate.inverse_company_rate > 1:
                currency_rate.inverse_company_rate = float_round(currency_rate.inverse_company_rate, precision_digits=digits)
