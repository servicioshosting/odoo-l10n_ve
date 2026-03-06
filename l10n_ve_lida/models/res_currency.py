# -*- coding: utf-8 -*-

from odoo import _, api, fields, models


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
