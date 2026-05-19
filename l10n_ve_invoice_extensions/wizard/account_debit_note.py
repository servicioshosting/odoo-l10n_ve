# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Command
from odoo.tools import float_is_zero
from odoo.tools.translate import _


class AccountDebitNote(models.TransientModel):
    _inherit = "account.debit.note"

    reason = fields.Char(required=True)

    is_invoice = fields.Boolean(compute="_compute_is_invoice")

    product_balance_ids = fields.One2many('account.debit.note.product.balance', 'debit_id')

    @api.model
    def default_get(self, fields):
        res = super(AccountDebitNote, self).default_get(fields)
        move_ids = self.env['account.move'].browse(self.env.context['active_ids']) if self.env.context.get('active_model') == 'account.move' else self.env['account.move']
        
        if move_ids and len(move_ids) == 1:
            res['journal_id'] = move_ids.journal_id
            if move_ids.l10n_ve_doc_type_internal_type == 'invoice':
                balances = move_ids.product_balance_ids
                vals_list = [balance.copy_data()[0] for balance in balances]
                for balance, vals in zip(balances, vals_list):
                    vals.update({'origin_balance_id': balance.id})
                res['product_balance_ids'] = [
                    Command.create(vals)
                    for balance, vals in zip(balances, vals_list) if balance.quantity > 0
                ]
        return res

    @api.constrains('move_ids')
    def _check_move_ids(self):
        if all(move.company_id.account_fiscal_country_id.code != 'VE' for move in self.move_ids):
            return

        if len(self.move_ids) > 1 and any(move.is_sale_document() and move.l10n_ve_doc_type_internal_type == 'invoice' for move in self.move_ids):
            raise ValidationError("No puede reversar más de un documento fiscal a la vez.")

        if any(move.l10n_ve_doc_type_internal_type == 'invoice' and move.l10n_ve_was_reversed for move in self.move_ids):
            raise ValidationError(_("El documento [%s] ya fue reversado y no puede ser afectado por más notas.", self.move_ids.name))

        if any(move.l10n_ve_doc_type_internal_type in ['credit_note', 'debit_note'] for move in self.move_ids):
            raise ValidationError("No puede reversar notas de crédito o débito.")

    # @api.constrains('product_balance_ids')
    # def _check_product_balance_ids(self):
    #     for wizard in self:
    #         if wizard.is_invoice and all(float_is_zero(balance.quantity, 2) for balance in wizard.product_balance_ids):
    #             raise ValidationError("No puede reversar notas de crédito o débito.")

    @api.depends('move_ids')
    def _compute_is_invoice(self):
        self.is_invoice = len(self.move_ids) == 1 and all(move.l10n_ve_doc_type_internal_type == 'invoice' for move in self.move_ids)

    # @api.depends('is_invoice', 'move_ids.product_balance_ids')
    # def _compute_product_balance_ids(self):
    #     for wizard in self:
    #         if not wizard.is_invoice:
    #             wizard.product_balance_ids = []
    #         elif not wizard.product_balance_ids:
    #             balances = wizard.move_ids.mapped('product_balance_ids')
    #             vals_list = [balance.copy_data()[0] for balance in balances]
    #             for balance, vals in zip(balances, vals_list):
    #                 vals.update({'origin_balance_id': balance.id})
    #             wizard.product_balance_ids = [
    #                 fields.Command.create(vals)
    #                 for balance, vals in zip(balances, vals_list) if balance.quantity > 0
    #             ] if balances else []

    def _prepare_default_values(self, move):
        vals = super()._prepare_default_values(move)
        if not self.is_invoice:
            return vals

        vals.update({
            'note_reason': self.reason,
            'line_ids': self._get_move_lines_from_balances(move),
        })

        return vals

    def _get_move_lines_from_balances(self, move):
        price_change_map = {
            balance.product_id.id: {'quantity': balance.quantity, 'price_unit': balance.unit_price} 
            for balance in self.product_balance_ids if balance.unit_price > 0
        }

        line_vals_list = []
        for line in move.invoice_line_ids:
            if line.display_type == 'product' and line.product_id.id in price_change_map and price_change_map[line.product_id.id]['price_unit'] > 0:
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
                        # 'price_unit': price_change_map[line.product_id.id]['unit_price'],
                        # 'quantity': price_change_map[line.product_id.id]['quantity'],
                        'tax_ids': [Command.set(line.tax_ids.ids)],
                        'group_tax_id': line.group_tax_id.ids,
                        'tax_tag_ids': [Command.set(line.tax_tag_ids.ids)],
                        **price_change_map[line.product_id.id]
                    }
                ))
        return line_vals_list

