import json
import logging
import re
from datetime import datetime

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_is_zero, format_date

_logger = logging.getLogger(__name__)


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    l10n_ve_doc_type_internal_type = fields.Selection(related='move_id.l10n_ve_doc_type_internal_type', store=True)

    l10n_ve_parent_is_note = fields.Boolean(compute='_compute_l10n_ve_parent_is_note')

    # available_product_ids = fields.One2many('product.product', compute='_compute_available_product_ids')

    @api.depends('move_id.l10n_ve_doc_type_internal_type')
    def _compute_l10n_ve_parent_is_note(self):
        for line in self:
            line.l10n_ve_parent_is_note = line.move_id.l10n_ve_doc_type_internal_type in ['credit_note', 'debit_note']

    # @api.depends('move_id.invoice_line_ids', 'l10n_ve_parent_is_note')
    # def _compute_available_product_ids(self):
    #     from_notes = self.filtered(lambda aml: aml.l10n_ve_parent_is_note)
    #     invoices = [[note, note.affected_invoice_id] for note in from_notes.mapped('move_id')]
    #     by_invoice = {}
    #     for note, invoice in invoices:
    #         by_invoice[invoice._origin.id] = invoice.invoice_line_ids.product_id
    #     # for line in self:
    #     #     line.

    @api.constrains(
        'move_id',
        'product_id',
        'quantity',
        'price_unit',
    )
    def _constrains_product_balances(self):
        """Valida que la línea de una nota no rompe el balance de una factura"""
        for aml in self:
            if aml.display_type != 'product' or not aml.product_id or not aml.l10n_ve_parent_is_note:
                continue

            origin_move = self.env['account.move']
            if aml.move_id.l10n_ve_doc_type_internal_type == 'credit_note':
                origin_move += aml.move_id.reversed_entry_id
            elif aml.move_id.l10n_ve_doc_type_internal_type == 'debit_note':
                origin_move += aml.move_id.debit_origin_id

            if not origin_move:
                raise UserError("El documento origen [%s] no es un documento fiscal válido" % (aml.move_id.name))
