from odoo import _, api, exceptions, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Command


class ProductTemplate(models.Model):
    _inherit = "product.template"

    taxes_id = fields.Many2many(domain=[('type_tax_use', '=', 'sale'), ('l10n_ve_tax_type', '=', 'VAT')], readonly=True)
    supplier_taxes_id = fields.Many2many(domain=[('type_tax_use', '=', 'purchase'), ('l10n_ve_tax_type', '=', 'VAT')], readonly=True)

    def default_l10n_ve_vat_id(self):
        tax = self.env['account.tax'].search([('type_tax_use', '=', 'sale'), ('l10n_ve_tax_type', '=', 'VAT')], limit=1)
        return tax.id  if tax else False

    def default_l10n_ve_supplier_vat_id(self):
        tax = self.env['account.tax'].search([('type_tax_use', '=', 'purchase'), ('l10n_ve_tax_type', '=', 'VAT')], limit=1)
        return tax.id  if tax else False

    l10n_ve_vat_id = fields.Many2one(
        "account.tax",
        "Alícuota del IVA de venta",
        compute="_compute_l10n_ve_vat_id",
        inverse="_inverse_l10n_ve_vat_id",
        domain=[('type_tax_use', '=', 'sale'), ('l10n_ve_tax_type', '=', 'VAT')],
        default=default_l10n_ve_vat_id,
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
        default=default_l10n_ve_supplier_vat_id,
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

        if len(taxes_id) != 1:
            self.env['auditlog.fiscalevent'].sudo().record_event(
                self,
                f"Se evitó asignar una cantidad inválida (distinta de 1) de alícuotas del IVA al producto [{self.display_name or self.default_code or self.id}]",
                [fields.Command.link(self.env.ref('l10n_ve_auditlog.fiscalevent_tag_facturacion').id)]
            )
            raise UserError(_("El producto debe estar asociado a una sola alícuota del IVA para %s", tax_type))

        for t in taxes_id:
            if t.l10n_ve_tax_type != 'VAT':
                self.env['auditlog.fiscalevent'].sudo().record_event(
                    self,
                    f"Se evitó asignar un impuesto al producto [{self.display_name or self.default_code or self.id}] que no es una alícuota del IVA",
                    [fields.Command.link(self.env.ref('l10n_ve_auditlog.fiscalevent_tag_facturacion').id)]
                )
                raise ValidationError(_("El impuesto [%s] no es una alícuota del IVA", t.name))
