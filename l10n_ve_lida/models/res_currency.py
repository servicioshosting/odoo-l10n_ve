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

    def _convert(self, from_amount, to_currency, company=None, date=None, round=True, custom_rate=0.0):
        """Returns the converted amount of ``from_amount``` from the currency
           ``self`` to the currency ``to_currency`` for the given ``date`` and
           company.

           :param company: The company from which we retrieve the convertion rate
           :param date: The nearest date from which we retriev the conversion rate.
           :param round: Round the result or not
        """
        if date is None:
            date = fields.Date.today()
        if company is None:
            company = self.rate_ids.company_id
        self, to_currency = self or to_currency, to_currency or self
        assert self, "convert amount from unknown currency"
        assert to_currency, "convert amount to unknown currency"
        assert company, "convert amount from unknown company"
        assert date, "convert amount from unknown date"
        # apply conversion rate
        if self == to_currency:
            to_amount = from_amount
        elif from_amount:
            if custom_rate > 0:
                to_amount = from_amount * custom_rate
            else:
                to_amount = from_amount * self._get_conversion_rate(self, to_currency, company, date)
        else:
            return 0.0

        # apply rounding
        return to_currency.round(to_amount) if round else to_amount


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

    @api.model
    def compute_rate(self, foreign_currency_id, rate_date):
        """
        Compute the rate and inverse rate for the given currency and date.

        If the foreign currency is USD then the rate will be the inverse company rate and the
        inverse rate will be the company rate, Else both rates will be the company rate.

        This is done because the foreign rate will be the rate that is gonna be shown to the user
        and the inverse rate will be the rate that will be used as factor to multiply for the
        computation of the foreign amounts.

        The logic is that if the foreign currency is VEF then we will be always multiplying by the
        value the user uses and see as the rate, but if the foreign currency is USD then we will be
        always multiplying by the inverse rate because the user will see the rate as the inverse
        rate.

        Parameters
        ----------
        foreign_currency_id : int
            The id of the foreign currency.
        rate_date : date
            The date of the rate that is gonna be searched for the given currency
            (foreign_currency_id).

        Returns
        -------
        dict
            A dictionary with the rate and inverse rate for the given currency and date.
        """
        rates = self.env["res.currency.rate"].search(
            [
                ("currency_id", "=", foreign_currency_id),
                ("company_id", "=", self.env.company.id),
                ("name", "<=", rate_date),
            ], order='name desc', limit=1
        )
        if not rates:
            rates = self.env['res.currency.rate'].search([
                ("currency_id", "=", foreign_currency_id),
                ("company_id", "=", self.env.company.id),
            ], order='name asc', limit=1)
        if not rates:
            return {}

        rate = rates[0]
        base_vef_id = self.env["ir.model.data"]._xmlid_to_res_id(
            "base.VEF", raise_if_not_found=False
        )
        if foreign_currency_id == base_vef_id:
            return {"foreign_rate": rate.company_rate, "foreign_inverse_rate": rate.company_rate}
        else:
            return {
                "foreign_rate": rate.inverse_company_rate,
                "foreign_inverse_rate": rate.company_rate,
            }

    @api.model
    def compute_inverse_rate(self, rate):
        """
        Compute the inverse rate for the given rate.
        The inverse rate will be the inverse of the given rate if the foreign currency is USD, else
        the inverse rate will be the same as the given rate.

        Parameters
        ----------
        rate : float
            The rate that is gonna be used to compute the inverse rate.

        Returns
        -------
        float
            The inverse rate for the given rate.
        """
        base_vef_id = self.env["ir.model.data"]._xmlid_to_res_id(
            "base.VEF", raise_if_not_found=False
        )
        foreign_currency_id = self.env.company.currency_foreign_id.id or False
        inverse_rate = rate if foreign_currency_id == base_vef_id else 1 / rate
        return inverse_rate
