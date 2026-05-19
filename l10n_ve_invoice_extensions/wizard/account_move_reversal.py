# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Command
from odoo.tools import float_is_zero
from odoo.tools.translate import _


class AccountMoveReversal(models.TransientModel):
    _inherit = "account.move.reversal"
    _name = 'account.move.reversal'
    _description = 'Account Move Reversal'
    _check_company_auto = True

    is_invoice = fields.Boolean(compute="_compute_is_invoice")

    product_balance_ids = fields.One2many('account.move.reversal.product.balance', 'reversal_id', compute="_compute_product_balance_ids", store=True)
    fully_reverse_invoice = fields.Boolean('Reverso completo',
                                           compute="_compute_fully_reverse_invoice",
                                           readonly=True,
                                           store=True)

    @api.constrains('move_ids')
    def _check_move_ids(self):
        if all(move.country_code != 'VE' for move in self.move_ids):
            return

        if len(self.move_ids) > 1 and any(move.is_sale_document() and move.l10n_ve_doc_type_internal_type == 'invoice' for move in self.move_ids):
            self.env['auditlog.fiscalevent'].sudo().record_event(
                None,
                f"Se evitó que se intentaran reversar los documentos [{", ".join(self.move_ids.mapped('name'))}] con una misma nota.",
                [fields.Command.link(self.env.ref('l10n_ve_auditlog.fiscalevent_tag_facturacion').id)]
            )
            raise ValidationError("No puede reversar más de un documento fiscal a la vez.")

        if any(move.l10n_ve_doc_type_internal_type == 'invoice' and move.l10n_ve_was_reversed for move in self.move_ids):
            self.env['auditlog.fiscalevent'].sudo().record_event(
                self.move_ids,
                f"Se evitó que se intentara reversar el documento [{self.move_ids.name}] que ya fue reversado.",
                [fields.Command.link(self.env.ref('l10n_ve_auditlog.fiscalevent_tag_facturacion').id)]
            )
            raise ValidationError(_("El documento [%s] ya fue reversado y no puede ser afectado por más notas.", self.move_ids.name))

        if any(move.l10n_ve_doc_type_internal_type in ['credit_note', 'debit_note'] for move in self.move_ids):
            self.env['auditlog.fiscalevent'].sudo().record_event(
                self.move_ids,
                f"Se evitó que se intentara reversar la nota [{self.move_ids.name}] con otra nota.",
                [fields.Command.link(self.env.ref('l10n_ve_auditlog.fiscalevent_tag_facturacion').id)]
            )
            raise ValidationError("No puede reversar notas de crédito o débito.")

    @api.constrains('product_balance_ids')
    def _check_product_balance_ids(self):
        for wizard in self:
            if wizard.is_invoice and all(float_is_zero(balance.quantity, 2) for balance in wizard.product_balance_ids):
                wizard.env['auditlog.fiscalevent'].sudo().record_event(
                    wizard.move_ids,
                    f"Se evitó que se intentara crear una nota de crédito vacía del documento [{wizard.move_ids.name}].",
                    [fields.Command.link(self.env.ref('l10n_ve_auditlog.fiscalevent_tag_facturacion').id)]
                )
                raise ValidationError("No puede crear una nota de crédito vacía")

    @api.depends('move_ids', 'is_invoice')
    def _compute_available_journal_ids(self):
        # OVERWRITE
        from_invoices = self.filtered(lambda x: x.is_invoice)
        for record in from_invoices:
            record.available_journal_ids = record.move_ids.journal_id

        super(AccountMoveReversal, self - from_invoices)._compute_available_journal_ids()

    @api.depends('move_ids')
    def _compute_is_invoice(self):
        self.is_invoice = len(self.move_ids) == 1 and all(move.l10n_ve_doc_type_internal_type == 'invoice' for move in self.move_ids)

    @api.depends('is_invoice', 'move_ids.product_balance_ids')
    def _compute_product_balance_ids(self):
        for wizard in self:
            if not wizard.is_invoice:
                wizard.product_balance_ids = []
            elif not wizard.product_balance_ids:
                balances = wizard.move_ids.mapped('product_balance_ids')
                vals_list = [balance.copy_data()[0] for balance in balances]
                for balance, vals in zip(balances, vals_list):
                    vals.update({'origin_balance_id': balance.id})
                wizard.product_balance_ids = [
                    fields.Command.create(vals)
                    for balance, vals in zip(balances, vals_list) if balance.quantity > 0
                ] if balances else []

    @api.depends('product_balance_ids.quantity', 'product_balance_ids.origin_available_quantity')
    def _compute_fully_reverse_invoice(self):
        for wizard in self:
            wizard.fully_reverse_invoice = wizard.product_balance_ids and all(float_is_zero(balance.origin_available_quantity - balance.quantity, 2) for balance in wizard.product_balance_ids)

    def _prepare_default_reversal(self, move):
        vals = super()._prepare_default_reversal(move)
        if not self.is_invoice:
            return vals

        vals.update({
            'note_reason': self.reason,
            # 'line_ids': line_vals,
        })

        return vals

    def reverse_moves(self, is_modify=False):
        self.ensure_one()
        if not self.is_invoice:
            return super().reverse_moves(is_modify)

        if is_modify:
            raise UserError("No se soporta el reverso y la creación de una copia del documento ")

        if not any(balance.quantity > 0 for balance in self.product_balance_ids):
            raise ValidationError("No se seleccionó ningún balance para reversar.")

        # Este segmento no fue modificado

        moves = self.move_ids

        # Create default values.
        partners = moves.company_id.partner_id + moves.commercial_partner_id

        bank_ids = self.env['res.partner.bank'].search([
            ('partner_id', 'in', partners.ids),
            ('company_id', 'in', moves.company_id.ids + [False]),
        ], order='sequence DESC')
        partner_to_bank = {bank.partner_id: bank for bank in bank_ids}
        default_values_list = []
        for move in moves:
            if move.is_outbound():
                partner = move.company_id.partner_id
            else:
                partner = move.commercial_partner_id
            default_values_list.append({
                'partner_bank_id': partner_to_bank.get(partner, self.env['res.partner.bank']).id,
                **self._prepare_default_reversal(move),
            })

        # Hasta aquí, es igual
        # batches = [
        #     [self.env['account.move'], [], True],   # Moves to be cancelled by the reverses.
        #     [self.env['account.move'], [], False],  # Others.
        # ]
        # for move, default_vals in zip(moves, default_values_list):
        #     is_auto_post = default_vals.get('auto_post') != 'no'
        #     is_cancel_needed = not is_auto_post and (is_modify or self.move_type == 'entry')
        #     batch_index = 0 if is_cancel_needed else 1
        #     batches[batch_index][0] |= move
        #     batches[batch_index][1].append(default_vals)

        # Handle reverse method.
        moves_to_redirect = self.env['account.move']
        for move, default_vals in zip(moves, default_values_list):
            default_vals.update({
                'move_type': 'out_refund' if move.move_type == 'out_invoice' else 'in_refund',
                'reversed_entry_id': move._origin.id,
            })
            new_move_vals = move.copy_data(default_vals)[0]
            product_balance_map = {balance.product_id.id: balance for balance in self.product_balance_ids}

            line_vals_list = []
            for line in move.invoice_line_ids:
                if line.display_type == 'product' and line.product_id.id in product_balance_map and product_balance_map[line.product_id.id].quantity > 0:
                    line_vals_list.append(Command.create(
                        {
                            'name': line.name,
                            'analytic_distribution': line.analytic_distribution,
                            'analytic_distribution_search': line.analytic_distribution_search,
                            'analytic_precision': line.analytic_precision,
                            'display_type': line.display_type,
                            'sequence': line.sequence,
                            'currency_id': line.currency_id.id,
                            'product_id': line.product_id.id,
                            'product_uom_id': line.product_uom_id.id,
                            'price_unit': product_balance_map[line.product_id.id].unit_price,
                            'quantity': product_balance_map[line.product_id.id].quantity,
                            'tax_ids': [Command.set(line.tax_ids.ids)],
                            'group_tax_id': line.group_tax_id.ids,
                            'tax_tag_ids': [Command.set(line.tax_tag_ids.ids)],
                        }
                    ))

            new_move_vals['line_ids'] = line_vals_list
            self._l10n_ve_modify_reverse_move_data(new_move_vals, move)
            reverse = self.env['account.move'].create(new_move_vals)
            self._l10n_ve_post_create_reverse_move(reverse, move)

            moves_to_redirect |= reverse

        self.new_move_ids = moves_to_redirect

        # Create action.
        action = {
            'name': _('Reverse Moves'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
        }
        if len(moves_to_redirect) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': moves_to_redirect.id,
                'context': {'default_move_type':  moves_to_redirect.move_type},
            })
        else:
            action.update({
                'view_mode': 'tree,form',
                'domain': [('id', 'in', moves_to_redirect.ids)],
            })
            if len(set(moves_to_redirect.mapped('move_type'))) == 1:
                action['context'] = {'default_move_type':  moves_to_redirect.mapped('move_type').pop()}
        return action

    def _l10n_ve_modify_reverse_move_data(self, vals, move):
        return

    def _l10n_ve_post_create_reverse_move(self, reverse_move, move):
        return
