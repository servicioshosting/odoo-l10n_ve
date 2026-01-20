import json
import logging
import re
from datetime import datetime

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import format_date

_logger = logging.getLogger(__name__)

PREPRINTED_CORRELATIVE_PATTERN = re.compile('^\d{2}[-]\d{1,8}$')


class AccountMove(models.Model):
    _inherit = "account.move"

    l10n_ve_doc_type_internal_type = fields.Selection(related='l10n_latam_document_type_id.internal_type', store=True)

    is_debit = fields.Boolean(compute='_compute_l10n_ve_is_fiscal_document')

    credit_note_count = fields.Integer('Número de Notas de Crédito', compute='_compute_credit_count')

    affected_invoice_id = fields.Many2one("account.move", "Documento afectado", store=True, compute='_computed_affected_document')
    affected_invoice_number = fields.Char("Nro. documento afectado", store=True, compute='_computed_affected_document')

    note_reason = fields.Char("Motivo de la nota")

    def _is_manual_document_number(self):
        return self.journal_id.type == 'purchase' or self.is_contingency

    @api.depends('l10n_ve_doc_type_internal_type')
    def _compute_l10n_ve_is_fiscal_document(self):
        # fiscal_documents = ['invoice', 'credit_note', 'debit_note']
        for move in self:
            move.is_debit = move.l10n_ve_doc_type_internal_type == 'debit_note'
            # move.l10n_ve_is_fiscal_document = move.l10n_ve_doc_type_internal_type and move.l10n_ve_doc_type_internal_type in fiscal_documents

    @api.depends('reversal_move_id')
    def _compute_credit_count(self):
        credit_data = self.env['account.move']._read_group([('reversed_entry_id', 'in', self.ids), ('l10n_ve_doc_type_internal_type', '=', 'credit_note'), ('state', '=', 'posted')],
                                                           ['reversed_entry_id'], ['__count'])
        data_map = {credit_origin.id: count for credit_origin, count in credit_data}
        for inv in self:
            inv.credit_note_count = data_map.get(inv.id, 0.0)

    @api.depends('l10n_ve_doc_type_internal_type')
    def _computed_affected_document(self):
        for move in self:
            move.affected_invoice_id = False
            is_note = False

            if not move.l10n_ve_doc_type_internal_type:
                continue

            if move.l10n_ve_doc_type_internal_type == 'debit_note':
                if move.debit_origin_id and move.debit_origin_id.l10n_ve_doc_type_internal_type == 'invoice':
                    move.affected_invoice_id = move.debit_origin_id
                is_note = True
            elif move.l10n_ve_doc_type_internal_type == 'credit_note':
                if move.debit_origin_id and move.reversed_entry_id.l10n_ve_doc_type_internal_type == 'invoice':
                    move.affected_invoice_id = move.debit_origin_id
                move.affected_invoice_id = move.reversed_entry_id
                is_note = True

            if is_note and not move.affected_invoice_id:
                raise UserError(_("La nota [%s] no tiene un documento origen válido", move.name), )

            move.affected_invoice_number = move.affected_invoice_id.name if move.affected_invoice_id else ''

    @api.depends('journal_id')
    def _compute_is_debit_journal(self):
        for move in self:
            move.is_debit_journal = True

    def _get_invoice_reference_odoo_invoice(self):
        """ This computes the reference based on the Odoo format.
            We simply return the number of the invoice, defined on the journal
            sequence.
        """
        self.ensure_one()
        return self.name

    @api.depends('posted_before', 'move_type')
    def _compute_show_reset_to_draft_button(self):
        """ Previene que un movimiento sea regresado a  """
        super()._compute_show_reset_to_draft_button()
        for move in self:
            if move.move_type in ('out_invoice', 'out_refund', 'out_receipt') and move.posted_before:
                move.show_reset_to_draft_button = False

    @api.model
    def get_sequence(self):
        """
        Allows the invoice to have both a generic sequence
        number or a specific one given certain conditions.

        Returns
        -------
            The next number from the sequence to be assigned.
        """

        self.ensure_one()
        sequence = self.journal_id.series_correlative_sequence_id

        if not sequence:
            raise UserError(_("The sale's series sequence must be in the selected journal."))

        l10n_ve_control_number = sequence.next_by_id(sequence.id)

        if not PREPRINTED_CORRELATIVE_PATTERN.match(l10n_ve_control_number):
            raise UserError(_("El número de control generado no cumple con el patrón secuencia '00-00000'"))

        return l10n_ve_control_number

    def action_view_credit_notes(self):
        self.ensure_one()

        return {
            "name": "Notas de crédito",
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "view_mode": "tree,form",
            "domain": [("reversed_entry_id", "=", self._origin.id)],
        }
