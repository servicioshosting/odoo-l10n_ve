import json
import logging
import re
from datetime import datetime
from textwrap import shorten

from odoo import Command, _, api, fields, models
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

    product_balance_ids = fields.One2many("account.move.product.balance", "origin_id", "Balances de productos")
    # credit_note_balance_ids = fields.One2many(related="reversed_entry_id.product_balance_ids")
    # debit_note_balance_ids = fields.One2many(related="debit_origin_id.product_balance_ids")
    product_balance_count = fields.Integer("", compute="_compute_product_balance_count")

    l10n_ve_was_reversed = fields.Boolean("Documento fue reversado", compute='_compute_l10n_ve_was_reversed', store=True, default=0)

    ## OVERWRITES
    ## Organizados en orden de addons base y addons de localization.

    @api.depends('posted_before', 'move_type')
    def _compute_show_reset_to_draft_button(self):
        """ Previene que un movimiento sea regresado a  """
        super()._compute_show_reset_to_draft_button()

        self.filtered(lambda move:\
            move.country_code == 'VE'\
            and move.l10n_ve_doc_type_internal_type in ('invoice', 'debit_note', 'credit_note')\
            and move.state == 'posted'\
            and not move.is_purchase_document()
        ).show_reset_to_draft_button = False

    def _compute_debit_count(self):
        debit_data = self.env['account.move']._read_group([('debit_origin_id', 'in', self.ids), ('l10n_ve_doc_type_internal_type', '=', 'debit_note'), ('state', 'in', ['draft', 'posted'])],
                                                          ['debit_origin_id'], ['__count'])
        data_map = {debit_origin.id: count for debit_origin, count in debit_data}
        for inv in self:
            inv.debit_note_count = data_map.get(inv.id, 0.0)

    def _get_invoice_reference_odoo_invoice(self):
        """ This computes the reference based on the Odoo format.
            We simply return the number of the invoice, defined on the journal
            sequence.
        """
        self.ensure_one()
        return self.name

    def _get_move_display_name(self, show_ref=False):
        self.ensure_one()

        if not self.l10n_ve_doc_type_internal_type:
            return super()._get_move_display_name(show_ref)

        name = ''
        if self.state == 'draft' or not self.l10n_latam_document_number:
            name += {
                'invoice': _('Borrador de factura'),
                'credit_note': _('Borrador de nota de crédito'),
                'debit_note': _('Borrador de nota de débito'),
            }[self.l10n_ve_doc_type_internal_type]
            if self.move_type.startswith('in_'):
                name += ' de compra'
            name += ' '
        if not self.name or self.name == '/':
            if self.id:
                name += '(* %s)' % str(self.id)
        else:
            name += self.name
            if self.env.context.get('input_full_display_name'):
                if self.partner_id:
                    name += f', {self.partner_id.name}'
                if self.date:
                    name += f', {format_date(self.env, self.date)}'
        return name + (f" ({shorten(self.ref, width=50)})" if show_ref and self.ref else '')

    def _get_all_reconciled_invoice_partials(self):
        """Previene que se muestren documentos que no deberían conciliarse con este."""
        # EXTENDS: account
        partial_values_list = super()._get_all_reconciled_invoice_partials()

        return partial_values_list

    def _compute_payments_widget_to_reconcile_info(self):
        # EXTENDS: account
        # super(AccountMove, self)._compute_payments_widget_to_reconcile_info()
        # return

        ve_moves = self.filtered(lambda m: m.country_code == 'VE')
        for move in ve_moves:
            move.invoice_outstanding_credits_debits_widget = False
            move.invoice_has_outstanding = False

            if move.state != 'posted' \
                    or move.payment_state not in ('not_paid', 'partial') \
                    or not move.is_invoice(include_receipts=True):
                continue

            pay_term_lines = move.line_ids\
                .filtered(lambda line: line.account_id.account_type in ('asset_receivable', 'liability_payable'))

            domain = [
                ('account_id', 'in', pay_term_lines.account_id.ids),
                ('parent_state', '=', 'posted'),
                ('partner_id', '=', move.commercial_partner_id.id),
                ('reconciled', '=', False),
                '|', ('amount_residual', '!=', 0.0), ('amount_residual_currency', '!=', 0.0),
            ]

            if move.is_outbound() and move.l10n_ve_doc_type_internal_type:
                if move.l10n_ve_doc_type_internal_type == 'invoice':
                    domain.extend([
                        '|',
                        # Si no tiene documento afectado, es una factura u otro tipo de entrada
                        ('move_id.affected_invoice_id', '=', False),
                        # Si tiene documento afectado, es una nota y debe coincidir con este documento.
                        ('move_id.affected_invoice_id', '=', move.id),
                    ])
                if move.l10n_ve_doc_type_internal_type in ('debit_note', 'credit_note'):
                    domain.extend([
                        '|',
                        '|',
                        # Que no sea un documento fiscal, sino otra cosa
                        ('l10n_ve_doc_type_internal_type', '=', False),
                        # Que sea el documento afectado
                        ('move_id', '=', move.affected_invoice_id.id),
                        # Que sea otra nota relacionada al mismo documento afectado
                        ('move_id.affected_invoice_id', '=', move.affected_invoice_id.id),
                    ])

            payments_widget_vals = {'outstanding': True, 'content': [], 'move_id': move.id}

            if move.is_inbound():
                domain.append(('balance', '<', 0.0))
                payments_widget_vals['title'] = _('Outstanding credits')
            else:
                domain.append(('balance', '>', 0.0))
                payments_widget_vals['title'] = _('Outstanding debits')

            for line in self.env['account.move.line'].search(domain):

                if line.currency_id == move.currency_id:
                    # Same foreign currency.
                    amount = abs(line.amount_residual_currency)
                else:
                    # Different foreign currencies.
                    amount = line.company_currency_id._convert(
                        abs(line.amount_residual),
                        move.currency_id,
                        move.company_id,
                        line.date,
                    )

                if move.currency_id.is_zero(amount):
                    continue

                payments_widget_vals['content'].append({
                    'journal_name': line.ref or line.move_id.name,
                    'amount': amount,
                    'currency_id': move.currency_id.id,
                    'id': line.id,
                    'move_id': line.move_id.id,
                    'date': fields.Date.to_string(line.date),
                    'account_payment_id': line.payment_id.id,
                })

            if not payments_widget_vals['content']:
                continue

            move.invoice_outstanding_credits_debits_widget = payments_widget_vals
            move.invoice_has_outstanding = True

        super(AccountMove, self - ve_moves)._compute_payments_widget_to_reconcile_info()


    def _is_manual_document_number(self):
        # EXTENDS: l10n_latam_document_number
        if self.country_code != 'VE':
            return super()._is_manual_document_number()

        return self.journal_id.type == 'purchase' or self.is_contingency

    def _post(self, soft=True):
        for move in self:
            if move.l10n_ve_doc_type_internal_type not in ['credit_note', 'debit_note']:
                continue

            if move.affected_invoice_id and move.affected_invoice_id.l10n_ve_was_reversed:
                self.env['auditlog.fiscalevent'].sudo().record_event(
                    move, 
                    f"Se evitó la confirmación del borrador de nota [{move.display_name}] porque el documento afectado [{move.affected_invoice_id.name}] ya fue reversado por completo.",
                    [fields.Command.link(self.env.ref('l10n_ve_auditlog.fiscalevent_tag_facturacion').id)                    ]
                )
                raise UserError(f"No puede confirmar el borrador de nota [{move.name}] porque el documento afectado [{move.affected_invoice_id.name}] ya fue reversado por completo.")

        posted_moves = super()._post(soft)

        for move in posted_moves:
            if move.is_sale_document() and move.l10n_ve_doc_type_internal_type in ['invoice', 'credit_note', 'debit_note']:
                move._update_product_balance()

        return posted_moves

    def _reverse_moves(self, default_values_list=None, cancel=False):
        ''' Reverse a recordset of account.move.
        If cancel parameter is true, the reconcilable or liquidity lines
        of each original move will be reconciled with its reverse's.
        :param default_values_list: A list of default values to consider per move.
                                    ('type' & 'reversed_entry_id' are computed in the method).
        :return:                    An account.move recordset, reverse of the current self.
        '''
        for move in self:
            if move.country_code != 'VE':
                continue

            if move.l10n_ve_doc_type_internal_type in ['invoice']:
                self.env['auditlog.fiscalevent'].sudo().record_event(
                    move, 
                    f"Se evitó reversar el asiento de la factura [{move.name}] directamente sin nota de crédito.",
                    [fields.Command.link(self.env.ref('l10n_ve_auditlog.fiscalevent_tag_facturacion').id)                    ]
                )
                raise UserError("No puede reversar el asiento de la factura. Debe crear una nota de crédito.")

            if move.l10n_ve_doc_type_internal_type in ['credit_note', 'debit_note']:
                self.env['auditlog.fiscalevent'].sudo().record_event(
                    move, 
                    f"Se evitó reversar el asiento de la nota [{move.name}] en lugar de su documento origen.",
                    [fields.Command.link(self.env.ref('l10n_ve_auditlog.fiscalevent_tag_facturacion').id)                    ]
                )
                raise UserError("No puede reversar notas de crédito o débito.")

        return super(AccountMove, self)._reverse_moves(default_values_list, cancel)

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

        if not self.is_contingency and not PREPRINTED_CORRELATIVE_PATTERN.match(l10n_ve_control_number):
            raise UserError(_("El número de control generado no cumple con el patrón secuencia '00-00000'"))

        return l10n_ve_control_number

    # OVERWRITE LOCALIZATION
    @api.depends('journal_id')
    def _compute_is_debit_journal(self):
        for move in self:
            move.is_debit_journal = True

    # ADDED
    @api.depends('reversal_move_id')
    def _compute_credit_count(self):
        credit_data = self.env['account.move']._read_group([('reversed_entry_id', 'in', self.ids), ('l10n_ve_doc_type_internal_type', '=', 'credit_note'), ('state', 'in', ['draft', 'posted'])],
                                                           ['reversed_entry_id'], ['__count'])
        data_map = {credit_origin.id: count for credit_origin, count in credit_data}
        for inv in self:
            inv.credit_note_count = data_map.get(inv.id, 0.0)

    @api.depends('product_balance_ids.quantity')
    def _compute_l10n_ve_was_reversed(self):
        for move in self:
            move.l10n_ve_was_reversed = move.product_balance_ids and not any(balance.quantity > 0 for balance in move.product_balance_ids)

    @api.depends('l10n_ve_doc_type_internal_type')
    def _compute_l10n_ve_is_fiscal_document(self):
        # fiscal_documents = ['invoice', 'credit_note', 'debit_note']
        for move in self:
            move.is_debit = move.l10n_ve_doc_type_internal_type == 'debit_note'
            # move.l10n_ve_is_fiscal_document = move.l10n_ve_doc_type_internal_type and move.l10n_ve_doc_type_internal_type in fiscal_documents

    @api.depends('l10n_ve_doc_type_internal_type')
    def _computed_affected_document(self):
        for move in self:
            move.affected_invoice_id = False
            is_note = False

            if not move.l10n_ve_doc_type_internal_type:
                continue

            if move.l10n_ve_doc_type_internal_type == 'debit_note':
                move.affected_invoice_id = move.debit_origin_id
                is_note = True
            elif move.l10n_ve_doc_type_internal_type == 'credit_note':
                move.affected_invoice_id = move.reversed_entry_id
                is_note = True

            if is_note and (not move.affected_invoice_id or move.affected_invoice_id.l10n_ve_doc_type_internal_type != 'invoice'):
                self.env['auditlog.fiscalevent'].sudo().record_event(
                    move, 
                    f"Se evitó una edición a la nota [{move.display_name}] que iba a dejar a dicho documento sin un documento origen válido",
                    [fields.Command.link(self.env.ref('l10n_ve_auditlog.fiscalevent_tag_facturacion').id)                    ]
                )
                raise UserError(_("La nota [%d] no tiene un documento origen válido", move.id), )

            move.affected_invoice_number = move.affected_invoice_id.name if move.affected_invoice_id else ''

    @api.depends('product_balance_ids')
    def _compute_product_balance_count(self):
        balance_data = self.env['account.move.product.balance']._read_group([('invoice_id', 'in', self.ids)],
                                                                            ['invoice_id'], ['id:count'])
        data_map = {invoice_origin.id: count for invoice_origin, count in balance_data}
        for inv in self:
            inv.product_balance_count = data_map.get(inv.id, 0.0)

    def _update_product_balance(self):
        self.ensure_one()

        self.l10n_ve_was_reversed = False

        if self.l10n_ve_doc_type_internal_type == 'invoice':
            self.write({
                'product_balance_ids': [
                    Command.create({
                        "invoice_line_id": line.id,
                        "invoice_id": line.move_id.id,
                        "origin_id": line.move_id.id,
                        "quantity": line.quantity,
                        "unit_price": line.price_unit * (1 - (line.discount / 100.0)),
                    })
                    for line in self.invoice_line_ids if line.display_type == 'product'
                ]
            })
        elif self.l10n_ve_doc_type_internal_type == 'credit_note':
            balances = self.reversed_entry_id.product_balance_ids

            balances_by_product_id = {}
            for balance in balances:
                balances_by_product_id[balance.product_id.id] = balance

            for line in self.invoice_line_ids:
                balances_by_product_id[line.product_id.id].quantity -= line.quantity
        elif self.l10n_ve_doc_type_internal_type == 'debit_note':
            balances = self.debit_origin_id.product_balance_ids

            balances_by_product_id = {}
            for balance in balances:
                balances_by_product_id[balance.product_id.id] = balance

            for line in self.invoice_line_ids:
                balances_by_product_id[line.product_id.id].unit_price += line.price_unit
        else:
            raise UserError("No puede generar balances de productos para movimientos que no sean documentos fiscales")

    def action_view_product_balance(self):
        return {
            "name": "Balances de productos",
            "type": "ir.actions.act_window",
            "res_model": "account.move.product.balance",
            "view_mode": "tree",
            "domain": [("invoice_id", "in", self.ids)],
        }

    def action_update_product_balance(self):
        self.ensure_one()

        if self.l10n_ve_doc_type_internal_type != 'invoice':
            raise UserError("No puede generar balances de productos para movimientos que no sean documentos fiscales")

        self.product_balance_ids.unlink()

        balances_by_product_id = dict(
            (
                line.product_id.id,
                {
                    "invoice_id": line.move_id.id,
                    "origin_id": line.move_id.id,
                    "invoice_line_id": line.id,
                    "quantity": line.quantity,
                    # "unit_price": line.price_unit * (1 - (line.discount / 100.0)),
                    "unit_price": self.currency_id.round(line.price_unit * (1 - (line.discount / 100.0))),
                }
            )
            for line in self.invoice_line_ids if line.display_type == 'product'
        )

        credit_notes = self.reversal_move_id.filtered(lambda n: n.posted_before)
        debit_notes = self.debit_note_ids.filtered(lambda n: n.posted_before)

        for line in credit_notes.invoice_line_ids:
            balances_by_product_id[line.product_id.id]['quantity'] -= line.quantity

        for line in debit_notes.invoice_line_ids:
            balances_by_product_id[line.product_id.id]['unit_price'] += line.price_unit

        lines = [Command.create(line) for line in balances_by_product_id.values()]
        self.write({
            'product_balance_ids': lines
        })

        return self.action_view_product_balance()

    def action_view_credit_notes(self):
        self.ensure_one()

        return {
            "name": "Notas de crédito",
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "view_mode": "tree,form",
            "domain": [("reversed_entry_id", "=", self._origin.id)],
        }

    def button_draft(self):
        res = super().button_draft()

        self.product_balance_ids.unlink()

        return res
