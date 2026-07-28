# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class SaleOrderDiscount(models.TransientModel):
    _inherit = 'sale.order.discount'


    def action_apply_discount(self):
        if self.sale_order_id.country_code == 'VE':
            if self.sale_order_id.state != 'draft':
                raise UserError(_("No puede aplicar descuentos a ordenes confirmadas"))
            if self.discount_type != 'sol_discount':
                raise UserError(_("Solamente puede utilizar esta funcionalidad para aplicar descuentos a todas las líneas"))
        return super().action_apply_discount()
    
