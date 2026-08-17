import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = "res.company"

    def _localization_use_documents(self):
        self.ensure_one()
        return self.account_fiscal_country_id.code == "VE" or super()._localization_use_documents()

    unique_tax = fields.Boolean()
    show_discount_on_moves = fields.Boolean()

    exent_aliquot_sale = fields.Many2one("account.tax", domain=[("type_tax_use", "=", "sale")])
    general_aliquot_sale = fields.Many2one("account.tax", domain=[("type_tax_use", "=", "sale")])
    reduced_aliquot_sale = fields.Many2one("account.tax", domain=[("type_tax_use", "=", "sale")])
    extend_aliquot_sale = fields.Many2one("account.tax", domain=[("type_tax_use", "=", "sale")])
    not_show_reduced_aliquot_sale = fields.Boolean()
    not_show_extend_aliquot_sale = fields.Boolean()

    exent_aliquot_purchase = fields.Many2one(
        "account.tax", domain=[("type_tax_use", "=", "purchase")]
    )
    general_aliquot_purchase = fields.Many2one(
        "account.tax", domain=[("type_tax_use", "=", "purchase")]
    )
    reduced_aliquot_purchase = fields.Many2one(
        "account.tax", domain=[("type_tax_use", "=", "purchase")]
    )
    extend_aliquot_purchase = fields.Many2one(
        "account.tax", domain=[("type_tax_use", "=", "purchase")]
    )
    not_show_reduced_aliquot_purchase = fields.Boolean()
    not_show_extend_aliquot_purchase = fields.Boolean()

    config_deductible_tax = fields.Boolean()

    no_deductible_general_aliquot_purchase = fields.Many2one(
        "account.tax", domain=[("type_tax_use", "=", "purchase")]
    )
    no_deductible_reduced_aliquot_purchase = fields.Many2one(
        "account.tax", domain=[("type_tax_use", "=", "purchase")]
    )
    no_deductible_extend_aliquot_purchase = fields.Many2one(
        "account.tax", domain=[("type_tax_use", "=", "purchase")]
    )
