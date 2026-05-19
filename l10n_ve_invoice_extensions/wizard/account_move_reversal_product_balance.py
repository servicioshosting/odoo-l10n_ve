import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AccountMoveReversalProductBalance(models.TransientModel):
    _name = "account.move.reversal.product.balance"
    _inherit = ['product.balance.mixin']
    _description = "Balance de productos a reversar en una factura"
    _check_company_auto = True

    reversal_id = fields.Many2one('account.move.reversal', store=True)
    origin_balance_id = fields.Many2one('account.move.product.balance', "Origen", required=True)
    origin_available_quantity = fields.Float("Cantidad disponible", related='origin_balance_id.quantity', store=True)

    invoice_id = fields.Many2one('account.move', compute='_compute_from_origin', store=True)
    origin_id = fields.Many2one('account.move', compute='_compute_from_origin', store=True)
    invoice_line_id = fields.Many2one('account.move.line', compute='_compute_from_origin', store=True)
    product_id = fields.Many2one('product.product', compute='_compute_from_origin', store=True)
    tax_id = fields.Many2one('account.tax', compute='_compute_from_origin', store=True)
    quantity = fields.Float("A Retornar", compute='_compute_from_origin', store=True, readonly=False)
    unit_price = fields.Float(compute='_compute_from_origin', store=True)

    @api.onchange('origin_available_quantity', 'quantity')
    def _onchange_quantity_price(self):
        for balance in self:
            if not balance.origin_available_quantity:
                continue

            balance.quantity = max(0, min(balance.quantity, balance.origin_available_quantity))

    @api.constrains('origin_balance_id', 'quantity', 'unit_price')
    def _constrains_quantity_price(self):
        for balance in self:
            if not balance.origin_balance_id:
                continue

            if balance.quantity < 0:
                raise UserError("La cantidad de [%s] retornada / reversada no puede menor a cero" %
                                (balance.product_id.name, balance.origin_id.name))

            if balance.unit_price < 0:
                raise UserError("El precio unitario del producto [%s] no puede ser negativo" %
                                (balance.product_id.name, balance.origin_id.name))

            if balance.quantity > balance.origin_balance_id.quantity:
                raise UserError("La cantidad de [%s] retornada / reversada no puede mayor a la disponible por retornar [%.2f] en del documento [%s]" % (
                    balance.product_id.name, balance.origin_balance_id.quantity, balance.origin_id.name))

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
            balance.unit_price = balance.origin_balance_id.unit_price

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
                'tax_id': origin.tax_id.id,
                'unit_price': origin.unit_price,
            })

        return super().create(vals_list)

    def write(self, vals):
        return super().write(vals)
