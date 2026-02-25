from odoo import _, api, exceptions, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Command


class ProductTemplate(models.Model):
    _inherit = "product.template"

    taxes_id = fields.Many2many(domain=[('type_tax_use', '=', 'sale'), ('l10n_ve_tax_type', '=', 'VAT')], readonly=True)
    supplier_taxes_id = fields.Many2many(domain=[('type_tax_use', '=', 'purchase'), ('l10n_ve_tax_type', '=', 'VAT')], readonly=True)

    l10n_ve_vat_id = fields.Many2one(
        "account.tax",
        "Alícuota del IVA de venta",
        compute="_compute_l10n_ve_vat_id",
        inverse="_inverse_l10n_ve_vat_id",
        domain=[('type_tax_use', '=', 'sale'), ('l10n_ve_tax_type', '=', 'VAT')],
        store=True,
        copy=True,
        required=True,
    )
    l10n_ve_supplier_vat_id = fields.Many2one(
        "account.tax",
        "Alícuota del IVA de compra",
        compute="_compute_l10n_ve_supplier_vat_id",
        inverse="_inverse_l10n_ve_supplier_vat_id",
        domain=[('type_tax_use', '=', 'purchase'), ('l10n_ve_tax_type', '=', 'VAT')],
        store=True,
        copy=True,
        required=True,
    )

    @api.depends('taxes_id')
    def _compute_l10n_ve_vat_id(self):
        for p in self:
            p.l10n_ve_vat_id = p.taxes_id[0] if p.taxes_id else False

    def _inverse_l10n_ve_vat_id(self):
        for p in self:
            p.taxes_id = [Command.set(p.l10n_ve_vat_id.ids)]

    @api.depends('supplier_taxes_id')
    def _compute_l10n_ve_supplier_vat_id(self):
        for p in self:
            p.l10n_ve_supplier_vat_id = p.supplier_taxes_id[0] if p.supplier_taxes_id else False

    def _inverse_l10n_ve_supplier_vat_id(self):
        for p in self:
            p.supplier_taxes_id = [Command.set(p.l10n_ve_supplier_vat_id.ids)]

    @api.constrains('taxes_id')
    def _check_taxes_are_vat(self):
        for product in self:
            self._l10n_ve_check_tax_id(product.taxes_id, "ventas")

    @api.constrains('supplier_taxes_id')
    def _check_supplier_taxes_are_vat(self):
        for product in self:
            self._l10n_ve_check_tax_id(product.supplier_taxes_id, "compras")

    @api.model
    def _l10n_ve_check_tax_id(self, taxes_id, tax_type):
        if not taxes_id:
            return

        if len(taxes_id) > 1:
            taxes_id = [Command.set(taxes_id[:-1])]
        elif len(taxes_id) < 1:
            raise UserError(_("El producto debe estar asociado a una sola alícuota del IVA para %s", tax_type))

        for t in taxes_id:
            if t.l10n_ve_tax_type != 'VAT':
                raise ValidationError(_("El impuesto [%s] no es una alícuota del IVA", t.name))
