import json
import logging
from datetime import datetime

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import format_date
from odoo.tools.sql import column_exists, create_column, rename_column

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _name = "account.move"
    _inherit = "account.move"

    l10n_ve_responsible_id = fields.Many2one("res.users", "Responsable")
    l10n_ve_control_number = fields.Char("Número de control", copy=False, help="Será asignado al confirmar el documento")
    l10n_ve_doc_datetime = fields.Datetime(
        string='Fecha y hora de la factura',
        readonly=True,
        copy=False,
    )
    invoice_reception_date = fields.Date(
        "Reception Date",
        help="Indicates when the invoice was received by the client/company",
        tracking=True,
    )
    last_payment_date = fields.Date(compute="_compute_payment_dates", store=True)
    first_payment_date = fields.Date(compute="_compute_payment_dates", store=True)
    is_contingency = fields.Boolean(related="journal_id.is_contingency")

    next_installment_date = fields.Date(compute="_compute_next_installment_date")

    display_date_warning = fields.Boolean(
        compute="_compute_display_date_warning")

    is_debit_journal = fields.Boolean(
        compute="_compute_is_debit_journal",
        store=True
    )

    # 0: not printed yet, 1: first print (original), 2 or more: copies
    free_form_copy_number = fields.Integer(default=0, copy=False)
    is_print_copy = fields.Boolean(compute='_compute_is_print_copy')

    # Backwards compatibility
    correlative = fields.Char("Correlativo", compute='_compute_correlative')

    def _auto_init(self):
        if not column_exists(self.env.cr, "account_move", "l10n_ve_control_number"):
            if column_exists(self.env.cr, "account_move", "correlative"):
                rename_column(self.env.cr, "account_move", "correlative", "l10n_ve_control_number")

        if not column_exists(self.env.cr, "account_move", "l10n_ve_doc_datetime"):
            if column_exists(self.env.cr, "account_move", "l10n_ve_invoice_date"):
                rename_column(self.env.cr, "account_move", "l10n_ve_invoice_date", "l10n_ve_doc_datetime")
            else:
                create_column(self.env.cr, "account_move", "l10n_ve_doc_datetime", "timestamp")

                # Agregar +4 horas en postgres -> (invoice_date::timestamp + interval '12 hours') 5
                self.env.cr.execute(
                    "UPDATE account_move SET l10n_ve_doc_datetime = invoice_date::timestamp with time zone + INTERVAL '4 hours' WHERE state != 'draft'" 
                )

        if not column_exists(self.env.cr, "account_move", "l10n_ve_responsible_id"):
            create_column(self.env.cr, "account_move", "l10n_ve_responsible_id", "integer")
            self.env.cr.execute(
                "UPDATE account_move SET l10n_ve_responsible_id = invoice_user_id"
            )
        return super()._auto_init()

    @api.depends("l10n_ve_control_number")
    def _compute_correlative(self):
        for rec in self:
            rec.correlative = rec.l10n_ve_control_number

    @api.constrains("invoice_line_ids")
    def _check_price_in_zero(self):
        for line in self.filtered(lambda m: m.is_invoice()).mapped("invoice_line_ids"):
            if line.price_unit <= 0 and line.display_type not in ("line_section", "line_note"):
                raise ValidationError(_("An invoice cannot have a line with a price of zero"))

    @api.onchange("move_type")
    def _onchange_move_type(self):
        if self.move_type == "out_invoice":
            self.invoice_date = False
        elif not self.invoice_date:
            self.invoice_date = fields.Date.today()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('move_type', False) in ['out_invoice', 'out_refund', 'out_receipt']:
                vals['l10n_ve_responsible_id'] = self.env.user.id if self.env.user else vals.get('invoice_user_id')
        res = super().create(vals_list)
        return res

    def action_post(self):
        for record in self:
            sequence = record.env["ir.sequence"].sudo().search([("code", "=", "l10n_ve.invoice.control_number"), ("company_id", "=", self.env.company.id)])
            l10n_ve_control_number = str(sequence.number_next_actual).zfill(sequence.padding)

            invoices = record.env['account.move'].with_company(self.env.company.id).sudo().search([("l10n_ve_control_number", "=", l10n_ve_control_number), ('move_type', 'in', ["out_invoice", "out_refund"]), ('company_id', '=', self.env.company.id)])

            if invoices and record.move_type in ["out_invoice", "out_refund"]:
                raise ValidationError(_("An invoice already exists with the Control Number: %s" % l10n_ve_control_number))
        return super().action_post()

    @api.constrains("l10n_ve_control_number", "is_contingency")
    def _check_correlative(self):
        AccountMove = self.env["account.move"]
        is_series_invoicing_enabled = self.company_id.group_sales_invoicing_series
        for move in self:
            if not move.is_contingency:
                continue
            if not is_series_invoicing_enabled and not move.l10n_ve_control_number:
                raise ValidationError(
                    _(
                        "Contingency journal's invoices should always have a l10n_ve_control_number if series "
                        "invoicing is not enabled"
                    )
                )
            repeated_moves = AccountMove.search(
                [
                    ("is_contingency", "=", True),
                    ("id", "!=", move.id),
                    ("is_contingency", "=", True),
                    ("l10n_ve_control_number", "!=", False),
                    ("l10n_ve_control_number", "=", move.l10n_ve_control_number),
                    ("journal_id", "=", move.journal_id.id),
                ],
                limit=1,
            )
            if repeated_moves:
                raise UserError(
                    _("The l10n_ve_control_number must be unique per journal when using a contingency journal")
                )

    @api.depends('journal_id')
    def _compute_is_debit_journal(self):
        for move in self:
            move.is_debit_journal = move.journal_id.is_debit if move.journal_id else False

    @api.depends("amount_residual")
    def _compute_payment_dates(self):
        def clear_dates(move):
            move.last_payment_date = False
            move.first_payment_date = False

        for move in self:
            if not move.is_invoice(include_receipts=True) and move.state != "posted":
                clear_dates(move)
                continue

            is_invoice_payment_widget = bool(move.invoice_payments_widget)
            if not is_invoice_payment_widget:
                clear_dates(move)
                continue

            payments = move.invoice_payments_widget
            if not payments or not payments.get("content", False):
                clear_dates(move)
                continue

            last_date = False
            first_date = False

            dates = list()

            for payment in payments.get("content"):
                if not self.validate_payment(payment):
                    continue

                dates.append(payment.get("date", False))

            if len(dates) > 0:
                last_date = fields.Date.from_string(max(dates))
                first_date = fields.Date.from_string(min(dates))

            move.last_payment_date = last_date
            move.first_payment_date = first_date

    @api.model
    def validate_payment(self, payment):
        """This function was created to validate payments through external modules"""
        return True

    @api.onchange("invoice_line_ids")
    def _onchange_invoice_line_ids(self):
        """
        Limit the number of products that can be added to the invoice
        """
        if self.invoice_line_ids and self.move_type in ["out_invoice", "out_refund"]:
            max_product_invoice = self.company_id.max_product_invoice
            if len(self.invoice_line_ids) > max_product_invoice:
                raise ValidationError(
                    _("You can not add more than %s products to the invoice." % max_product_invoice)
                )

    @api.depends("payment_term_details")
    def _compute_next_installment_date(self):
        lang = self.env["res.lang"].search([("code", "=", self.env.user.lang)])
        date_format = lang.date_format if lang else "%Y-%m-%d"
        for invoice in self:
            invoice.next_installment_date = False
            if not invoice.payment_term_details:
                invoice.next_installment_date = invoice.invoice_date_due
                continue
            for term in invoice.payment_term_details:
                term_date = datetime.strptime(term.get("date", ""), date_format).date()
                if term_date and term_date >= fields.Date.today():
                    invoice.next_installment_date = term_date
                    break

    @api.depends("invoice_date", "state")
    def _compute_display_date_warning(self):
        today = fields.Date.context_today(self)
        for move in self:
            move.display_date_warning = bool(
                move.invoice_date and move.state == "draft" and move.invoice_date < today
            )

    def _post(self, soft=True):
        res = super()._post(soft)
        for move in res:

            if "invoice_print_type" in move.company_id._fields:
                invoice_print_type = move.company_id.invoice_print_type
            else:
                invoice_print_type = None

            move.l10n_ve_responsible_id =  self.env.user or move.invoice_user_id \
                if move.move_type in ['out_invoice', 'out_refund', 'out_receipt'] else False
            if move.is_valid_to_sequence() and invoice_print_type != "fiscal":
                move.l10n_ve_doc_datetime = fields.Datetime.now()
                move.invoice_date = move.l10n_ve_doc_datetime
                move.l10n_ve_control_number = move.get_sequence()

        return res

    @api.model
    def is_valid_to_sequence(self) -> bool:
        """
        Check if the invoice satisfies the conditions to associate a new sequence number to its
        l10n_ve_control_number.

        Returns:
            True or False whether the invoice already has a sequence number or not.
        """

        is_contingency = self.journal_id.is_contingency
        journal_type = self.journal_id.type == "sale"
        is_series_invoicing_enabled = self.company_id.group_sales_invoicing_series
        is_valid = (
            not self.l10n_ve_control_number
            and journal_type
            and (not is_contingency or is_series_invoicing_enabled)
        )

        return is_valid

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
        is_series_invoicing_enabled = self.company_id.group_sales_invoicing_series
        sequence = self.env["ir.sequence"].sudo()
        l10n_ve_control_number = None

        if is_series_invoicing_enabled:
            l10n_ve_control_number = self.journal_id.series_correlative_sequence_id

            if not l10n_ve_control_number:
                raise UserError(_("The sale's series sequence must be in the selected journal."))
            return l10n_ve_control_number.next_by_id(l10n_ve_control_number.id)

        l10n_ve_control_number = sequence.search(
            [("code", "=", "l10n_ve.invoice.control_number"), ("company_id", "=", self.env.company.id)]
        )
        if not l10n_ve_control_number:
            l10n_ve_control_number = sequence.create(
                {
                    "name": "Número de control",
                    "code": "l10n_ve.invoice.control_number",
                    "padding": 5,
                }
            )
        return l10n_ve_control_number.next_by_id(l10n_ve_control_number.id)

    @api.depends('state', 'free_form_copy_number')
    def _compute_is_print_copy(self):
        for move in self:
            move.is_print_copy = move.state == 'draft' or move.free_form_copy_number > 1

    def action_debit_note_button(self):
        action = ""
        for picking in self:
            action = picking.env.ref('account_debit_note.action_view_account_move_debit').read()[0]
        return action

    def print_invoice_free_form(self):
        report = self.env.ref(
            "l10n_ve_invoice.action_invoice_free_form_l10n_ve_invoice"
        )

        self.free_form_copy_number = self.free_form_copy_number + 1

        return report.report_action(self)
