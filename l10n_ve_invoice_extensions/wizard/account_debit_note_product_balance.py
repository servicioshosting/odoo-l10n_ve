import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare

_logger = logging.getLogger(__name__)


class AccountDebitNoteProductBalance(models.TransientModel):
    _name = "account.debit.note.product.balance"
    _inherit = ['product.balance.mixin']
    _description = "Balance de productos a modificar en una factura"
    _check_company_auto = True

    debit_id = fields.Many2one('account.debit.note', store=True)
    origin_balance_id = fields.Many2one('account.move.product.balance', "Origen", required=True)
    origin_available_quantity = fields.Float("Cantidad disponible", related='origin_balance_id.quantity', store=True)
    origin_unit_price = fields.Float("Precio original", related='origin_balance_id.unit_price', store=True)

    invoice_id = fields.Many2one('account.move', compute='_compute_from_origin', store=True, copy=True)
    origin_id = fields.Many2one('account.move', compute='_compute_from_origin', store=True, copy=True)
    invoice_line_id = fields.Many2one('account.move.line', compute='_compute_from_origin', store=True, copy=True)
    product_id = fields.Many2one('product.product', compute='_compute_from_origin', store=True, copy=True)
    tax_id = fields.Many2one('account.tax', compute='_compute_from_origin', store=True, copy=True)
    quantity = fields.Float(compute='_compute_from_origin', store=True, copy=True)
    unit_price = fields.Float("Diferencia de precio unitario", compute='_compute_from_origin', store=True, readonly=False, copy=True)
    new_unit_price = fields.Float(
        compute='_compute_new_unit_price',
        # inverse='_inverse_new_unit_price',
        store=True,
        readonly=False
    )

    currency_rounding = fields.Float(related='currency_id.rounding')

    @api.onchange('new_unit_price', 'quantity')
    def _onchange_new_unit_price(self):
        for balance in self:
            if not balance.quantity:
                continue

            balance.new_unit_price = max(balance.new_unit_price, balance.origin_unit_price)
            balance._inverse_new_unit_price()

    @api.constrains('origin_balance_id', 'quantity', 'unit_price')
    def _constrains_quantity_price(self):
        # self.fetch(['product_id.uom_id.rounding'])
        for balance in self:
            if not balance.origin_balance_id:
                continue

            if float_compare(balance.quantity, balance.origin_available_quantity, precision_rounding=balance.product_id.uom_id.rounding) != 0:
                raise ValidationError("La cantidad de [%s] afectada debe ser el total disponible en el balance de la factura" %
                                (balance.product_id.name))

            if balance.unit_price < 0:
                raise ValidationError("La diferencia del precio unitario del producto [%s] no puede ser negativo" %
                                (balance.product_id.name))

            # if balance.quantity > balance.origin_balance_id.quantity:
            #     raise ValidationError("La cantidad de [%s] retornada / reversada no puede mayor a la disponible por retornar [%.2f] en del documento [%s]" % (
            #         balance.product_id.name, balance.origin_balance_id.quantity, balance.origin_id.name))

    @api.depends('origin_balance_id')
    def _compute_from_origin(self):
        for balance in self:
            if not balance.origin_balance_id:
                continue

            balance.invoice_id = balance.origin_balance_id.invoice_id
            balance.origin_id = balance.origin_balance_id.origin_id
            balance.invoice_line_id = balance.origin_balance_id.invoice_line_id
            balance.product_id = balance.origin_balance_id.product_id
            balance.tax_id = balance.origin_balance_id.tax_id
            balance.quantity = balance.origin_balance_id.quantity
            balance.unit_price = 0  # balance.origin_balance_id.unit_price

    @api.depends('origin_unit_price', 'unit_price')
    def _compute_new_unit_price(self):
        for wizard in self:
            wizard.new_unit_price = wizard.currency_id.round(wizard.origin_unit_price + wizard.unit_price)

    def _inverse_new_unit_price(self):
        for wizard in self:
            wizard.unit_price = wizard.currency_id.round(wizard.new_unit_price - wizard.origin_unit_price)

    @api.model_create_multi
    def create(self, vals_list):
        origins = {
            origin._origin.id: origin
            for origin in self.env['account.move.product.balance'].browse(vals['origin_balance_id'] for vals in vals_list)
        }
        for vals in vals_list:
            origin = origins[vals['origin_balance_id']]
            vals.update({
                'invoice_id': origin.invoice_id.id,
                'origin_id': origin.origin_id.id,
                'invoice_line_id': origin.invoice_line_id.id,
                'product_id': origin.product_id.id,
                # 'tax_id': origin.tax_id.id,
                'quantity': origin.quantity,
            })

        return super().create(vals_list)

    def write(self, vals):
        return super().write(vals)
