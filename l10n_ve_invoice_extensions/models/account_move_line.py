import json
import logging
import re
from datetime import datetime

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare, float_is_zero

_logger = logging.getLogger(__name__)


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    l10n_ve_doc_type_internal_type = fields.Selection(related='move_id.l10n_ve_doc_type_internal_type', store=True)
    affected_invoice_id = fields.Many2one(related='move_id.affected_invoice_id')

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

    def _compute_totals(self):
        """Calcula el monto total del item
        
        Es necesario redondear el precio unitario con el descuento antes de realizar los demás cálculos para que la funcionalidad de las notas no tengan errores de calculo.
        """
        from_ve = self.filtered(lambda x: x.move_id.country_code == 'VE')
        not_ve = self - from_ve
        super(AccountMoveLine, not_ve)._compute_totals()

        for line in from_ve:
            if line.display_type != 'product':
                line.price_total = line.price_subtotal = False
            # Compute 'price_subtotal'.
            line_discount_price_unit = line.price_unit * (1 - (line.discount / 100.0))
            line_discount_price_unit = line.currency_id.round(line_discount_price_unit)
            subtotal = line.quantity * line_discount_price_unit

            # Compute 'price_total'.
            if line.tax_ids:
                taxes_res = line.tax_ids.compute_all(
                    line_discount_price_unit,
                    quantity=line.quantity,
                    currency=line.currency_id,
                    product=line.product_id,
                    partner=line.partner_id,
                    is_refund=line.is_refund,
                )
                line.price_subtotal = taxes_res['total_excluded']
                line.price_total = taxes_res['total_included']
            else:
                line.price_total = line.price_subtotal = subtotal

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

            product_balances = dict(
                (balance.product_id.id, balance)
                for balance in origin_move.product_balance_ids
            )

            if aml.product_id.id not in product_balances:
                self.env['auditlog.fiscalevent'].sudo().record_event(
                    aml.move_id,
                    f"Se evitó agregar el producto [{aml.product_id.name}] al borrador de nota [{aml.move_id.id}] el cual no aparece en el documento afectado [{origin_move.name}].",
                    [fields.Command.link(self.env.ref('l10n_ve_auditlog.fiscalevent_tag_facturacion').id)]
                )
                raise UserError("El documento origen [%s] no tiene un item correspondiente al producto [%s]" % (origin_move.name, aml.product_id.name))

            origin_line_id = product_balances[aml.product_id.id]

            if aml.quantity < aml.product_uom_id.rounding:
                aml.quantity = origin_line_id.quantity
                continue

            if aml.move_id.l10n_ve_doc_type_internal_type == 'credit_note':
                if origin_line_id.quantity < aml.quantity:
                    uom = aml.product_id.uom_id
                    self.env['auditlog.fiscalevent'].sudo().record_event(
                        aml.move_id,
                        f"Se evitó agregar una cantidad del producto [{aml.product_id.name}] al borrador de nota crédito [{aml.move_id.name}] mayor al disponible en el documento de origen [{origin_move.name}].",
                        [fields.Command.link(self.env.ref('l10n_ve_auditlog.fiscalevent_tag_facturacion').id)]
                    )
                    raise UserError("El balance del documento origen [%s] no permite retornar más de [%d %s] de [%s]" % (origin_move.name, origin_line_id.quantity, uom.name, aml.product_id.name))

                if not float_is_zero(origin_line_id.unit_price - aml.price_unit, precision_rounding=aml.company_currency_id.rounding):
                    self.env['auditlog.fiscalevent'].sudo().record_event(
                        aml.move_id,
                        f"Se evitó modificar el precio unitario del producto [{aml.product_id.name}] al borrador de nota crédito [{aml.move_id.name}].",
                        [fields.Command.link(self.env.ref('l10n_ve_auditlog.fiscalevent_tag_facturacion').id)]
                    )
                    raise UserError("El precio unitario de [%s] debe ser igual al de documento origen" % (aml.product_id.name))

            elif aml.move_id.l10n_ve_doc_type_internal_type == 'debit_note':
                if float_compare(origin_line_id.quantity, aml.quantity, precision_rounding=aml.product_uom_id.rounding) != 0:
                    self.env['auditlog.fiscalevent'].sudo().record_event(
                        aml.move_id,
                        f"Se evitó modificar la cantidad del producto [{aml.product_id.name}] del borrador de nota débito [{aml.move_id.id}].",
                        [fields.Command.link(self.env.ref('l10n_ve_auditlog.fiscalevent_tag_facturacion').id)]
                    )
                    raise UserError("No puede alterar la cantidad de (%(quantity)f de %(product_name)s) en el balance del documento origen [%(origin_move)s]" % ({"quantity": origin_line_id.quantity, "product_name": aml.product_id.name, "origin_move": origin_move.name}))
