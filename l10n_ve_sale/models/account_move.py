# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'


    @api.depends('posted_before', 'move_type')
    def _compute_show_reset_to_draft_button(self):
        """ Previene que un movimiento sea regresado a borrador si tiene sale.order asociadas
        
        Esto se previene para evitar el caso en el que se facturen todos los renglones de un sale.order por completo y 
        luego se retorne a borrador una factura vieja que haya sido cancelada, permitiendo facturar dos veces un 
        sale.order.line.
        """
        super()._compute_show_reset_to_draft_button()

        self.filtered(lambda move:\
            move.country_code == 'VE'
            and move.sale_order_count > 0\
            and not move.is_purchase_document()
        ).show_reset_to_draft_button = False
        # for move in self:
            # if move.country_code == 'VE' and move.sale_order_count > 0 and not move.is_purchase_document():
                # move.show_reset_to_draft_button = False