from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )

    currency_foreign_id = fields.Many2one(
        "res.currency",
        string="Currency Foreign",
        help="Currency Foreign for the company",
        related="company_id.currency_foreign_id",
        readonly=False,
    )

    @api.constrains("currency_foreign_id")
    def _check_currency_foreign_id(self):
        self = self.with_company(self.company_id)
        for rec in self:
            if "currency_id" in rec._fields and rec.currency_id == rec.currency_foreign_id:
                raise UserError(
                    _("The currency foreign must be different from the currency of the company")
                )

    @api.onchange("currency_foreign_id")
    def _onchange_currency_foreign_id(self):
        self = self.with_company(self.company_id)
        for rec in self:
            if "currency_id" in rec._fields and rec.currency_id == rec.currency_foreign_id:
                raise UserError(
                    _("The currency foreign must be different from the currency of the company")
                )

    unique_tax = fields.Boolean(
        related="company_id.unique_tax", readonly=False)

    show_discount_on_moves = fields.Boolean(
        related="company_id.show_discount_on_moves", readonly=False
    )

    exent_aliquot_sale = fields.Many2one(
        "account.tax", related="company_id.exent_aliquot_sale", readonly=False
    )
    general_aliquot_sale = fields.Many2one(
        "account.tax", related="company_id.general_aliquot_sale", readonly=False
    )
    reduced_aliquot_sale = fields.Many2one(
        "account.tax", related="company_id.reduced_aliquot_sale", readonly=False
    )
    extend_aliquot_sale = fields.Many2one(
        "account.tax", related="company_id.extend_aliquot_sale", readonly=False
    )
    not_show_reduced_aliquot_sale = fields.Boolean(
        related="company_id.not_show_reduced_aliquot_sale", readonly=False
    )
    not_show_extend_aliquot_sale = fields.Boolean(
        related="company_id.not_show_extend_aliquot_sale", readonly=False
    )

    exent_aliquot_purchase = fields.Many2one(
        "account.tax", related="company_id.exent_aliquot_purchase", readonly=False
    )
    general_aliquot_purchase = fields.Many2one(
        "account.tax", related="company_id.general_aliquot_purchase", readonly=False
    )
    reduced_aliquot_purchase = fields.Many2one(
        "account.tax", related="company_id.reduced_aliquot_purchase", readonly=False
    )
    extend_aliquot_purchase = fields.Many2one(
        "account.tax", related="company_id.extend_aliquot_purchase", readonly=False
    )
    not_show_reduced_aliquot_purchase = fields.Boolean(
        related="company_id.not_show_reduced_aliquot_purchase", readonly=False
    )
    not_show_extend_aliquot_purchase = fields.Boolean(
        related="company_id.not_show_extend_aliquot_purchase", readonly=False
    )

    config_deductible_tax = fields.Boolean(
        related="company_id.config_deductible_tax", readonly=False
    )

    no_deductible_general_aliquot_purchase = fields.Many2one(
        "account.tax",
        related="company_id.no_deductible_general_aliquot_purchase",
        readonly=False,
    )
    no_deductible_reduced_aliquot_purchase = fields.Many2one(
        "account.tax",
        related="company_id.no_deductible_reduced_aliquot_purchase",
        readonly=False,
    )
    no_deductible_extend_aliquot_purchase = fields.Many2one(
        "account.tax",
        related="company_id.no_deductible_extend_aliquot_purchase",
        readonly=False,
    )
