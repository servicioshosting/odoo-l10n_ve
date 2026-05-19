import json
import logging
import re
from datetime import datetime

from odoo import _, api, fields, models
from odoo.fields import Command
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_is_zero, format_date

_logger = logging.getLogger(__name__)


class AccountMoveProductBalance(models.Model):
    _name = "account.move.product.balance"
    _inherit = ['product.balance.mixin']
    _description = "Balance de productos de una factura"
    _check_company_auto = True

    _sql_constraints = [
        ('invoice_product_unique', "unique(invoice_id, product_id)", "Ya existe un balance para este producto en este documento.")
    ]

    @api.constrains('quantity', 'unit_price')
    def _constrains_quantity_price(self):
        for product_balance in self:
            if not product_balance.product_id:
                continue

            if product_balance.quantity < 0:
                raise UserError("El balance del producto [%s] en el documento [%s] no puede ser negativo" % (product_balance.product_id.name, product_balance.invoice_id.name))

            if product_balance.unit_price < 0:
                raise UserError("El precio unitario del producto [%s] en el documento [%s] no puede ser negativo" % (product_balance.product_id.name, product_balance.invoice_id.name))
