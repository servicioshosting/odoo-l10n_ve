import json
import logging
import re
from datetime import datetime

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Command
from odoo.tools import float_is_zero, format_date

_logger = logging.getLogger(__name__)


class ProductBalanceMixin(models.AbstractModel):
    _name = "product.balance.mixin"
    _description = "Balance de productos"
    _check_company_auto = True

    origin_id = fields.Many2one('account.move', "Documento origen", required=True,
                                help="El documento que originó esta modificación al balance")
    invoice_id = fields.Many2one('account.move', "Factura", required=True, store=True, compute='_compute_invoice_id', 
                                 help="La factura original de donde se origina este balance")
    invoice_line_id = fields.Many2one('account.move.line', "Item de Factura", required=True, readonly=True)
    product_id = fields.Many2one('product.product', "Producto", related='invoice_line_id.product_id', store=True, readonly=True)
    tax_id = fields.Many2one('account.tax', "Impuesto", compute='_compute_tax_id', store=True, readonly=True)
    quantity = fields.Float('Cantidad disponible', required=True, readonly=True)
    unit_price = fields.Float('Precio unitario', required=True, readonly=True)

    # Denormalized attributes
    currency_id = fields.Many2one('res.currency', related='invoice_id.currency_id')
    invoice_name = fields.Char("Número de documento", related='invoice_line_id.name')
    product_name = fields.Char("Nombre del producto", related='product_id.name')

    tax_percentage = fields.Float("Alícuota del IVA", compute="_compute_amounts")
    amount_untaxed = fields.Float("Base", compute="_compute_amounts")
    amount_tax = fields.Float("IVA", compute="_compute_amounts")
    amount_total = fields.Float("Monto", compute="_compute_amounts")

    @api.constrains('origin_id')
    def _constrains_origin_id(self):
        for product_balance in self:
            if not product_balance.origin_id:
                continue

            if product_balance.origin_id.move_type != 'out_invoice' or product_balance.origin_id.l10n_ve_doc_type_internal_type not in ['invoice', 'debit_note']:
                raise UserError("El documento origen [%s] no es una factura ni una nota débito" % (product_balance.origin_id.name))
    
    @api.constrains('invoice_id')
    def _constrains_invoice_id(self):
        for product_balance in self:
            if not product_balance.invoice_id:
                continue

            if product_balance.invoice_id.l10n_ve_doc_type_internal_type != 'invoice':
                raise UserError("El documento origen [%s] no es una factura" % (product_balance.invoice_id.name))
            
            if product_balance.origin_id.l10n_ve_doc_type_internal_type == 'debit_note' \
                and product_balance.invoice_id != product_balance.origin_id.affected_invoice_id:
                raise UserError("La factura origen [%s] del balance no es el documento afectado por la nota [%s]" % (product_balance.invoice_id.name, product_balance.origin_id.name))
            
            if product_balance.origin_id.l10n_ve_doc_type_internal_type == 'invoice' \
                and product_balance.invoice_id != product_balance.origin_id:
                raise UserError("La factura [%s] debe ser igual al documento origen del balance [%s]" % (product_balance.invoice_id.name, product_balance.origin_id.name))

    @api.depends('origin_id')
    def _compute_invoice_id(self):
        for product_balance in self:
            if product_balance.origin_id.l10n_ve_doc_type_internal_type == 'debit_note':
                product_balance.invoice_id = product_balance.origin_id.affected_invoice_id
            else:
                product_balance.invoice_id = product_balance.origin_id

    @api.depends('product_id')
    def _compute_tax_id(self):
        for balance in self:
            if not balance.product_id:
                balance.tax_id = False
            else:
                tax_ids = balance.product_id.taxes_id
                if len(tax_ids) != 1:
                    raise UserError(_("El producto [%s] tiene más de un impuesto asignado.", balance.product_id.name))
                balance.tax_id = tax_ids

    @api.depends('currency_id', 'product_id', 'tax_id', 'quantity', 'unit_price')
    def _compute_amounts(self):
        self._compute_tax_id()
        for balance in self:
            balance.tax_percentage = 0
            balance.amount_untaxed = 0
            balance.amount_tax = 0
            balance.amount_total = 0
            if not balance.product_id or not balance.tax_id:
                continue

            balance.tax_percentage = balance.tax_id.amount
            if float_is_zero(balance.quantity, 2):
                balance.amount_untaxed = 0
                balance.amount_tax = 0
                balance.amount_total = 0
            else:
                balance.amount_untaxed = balance.currency_id.round(balance.quantity * balance.unit_price)
                balance.amount_tax = balance.currency_id.round(balance.amount_untaxed * balance.tax_percentage / 100)
                balance.amount_total = balance.amount_untaxed + balance.amount_tax

    @api.depends('origin_id', 'product_id')
    def _compute_display_name(self):
        for balance in self:
            balance.display_name = f"{balance.origin_id.name} :: {balance.product_id.name}"
