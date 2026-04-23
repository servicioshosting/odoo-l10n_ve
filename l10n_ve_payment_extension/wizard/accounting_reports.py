import logging
from datetime import datetime

import xlsxwriter
from odoo import _, api, models
from odoo.osv import expression

_logger = logging.getLogger(__name__)


class WizardAccountingReports(models.TransientModel):
    _inherit = "wizard.accounting.reports"

    def _determinate_resume_retention_books(self, moves):
        retention_resume_lines = []
        retention_moves = moves.filtered(lambda m: bool(m.retention_iva_line_ids.ids))
        credit_notes = retention_moves.filtered(
            lambda m: m.move_type in ["out_refund", "in_refund"]
        )
        retention_moves -= credit_notes

        retention_resume_lines.append(0.0)
        retention_resume_lines.append(
            sum(
                [
                    self._sum_retention_total(
                        move.retention_iva_line_ids.filtered(
                            lambda x: x.retention_id.state == "emitted"
                            and not self._check_future_retention_dates(
                                x.retention_id.date_accounting
                            )
                        )
                    )
                    for move in retention_moves
                ]
            )
        )
        retention_resume_lines.append(0.0)
        retention_resume_lines.append(
            sum(
                [
                    self._sum_retention_total(
                        move.retention_iva_line_ids.filtered(
                            lambda x: x.retention_id.state == "emitted"
                            and not self._check_future_retention_dates(
                                x.retention_id.date_accounting
                            )
                        )
                    )
                    * -1
                    for move in credit_notes
                ]
            )
        )

        return retention_resume_lines

    # def _resume_sale_book_fields(self, moves):
    #     res_book = super()._resume_sale_book_fields(moves)
    #     res_book.extend(
    #         [
    #             {
    #                 "name": "Total Retenciones",
    #                 "format": "number",
    #                 "values": self._determinate_resume_retention_books(moves),
    #             }
    #         ]
    #     )

    #     return res_book

    # def _resume_purchase_book_fields(self, moves):
    #     res_book = super()._resume_purchase_book_fields(moves)
    #     res_book.extend(
    #         [
    #             {
    #                 "name": "Total Retenciones",
    #                 "format": "number",
    #                 "values": self._determinate_resume_retention_books(moves),
    #             }
    #         ]
    #     )
    #     return res_book

    def sale_book_fields(self):
        fields = super().sale_book_fields()
        fields.extend(
            [
                {
                    "name": "Fecha Retención",
                    "field": "date_retention",
                    "size": 12,
                },
                {
                    "name": "N° Retención",
                    "field": "number_retention",
                    "size": 20,
                },
                {"name": "IVA retenido", "field": "iva_retained", "format": "number"},
            ]
        )
        return fields

    def purchase_book_fields(self):
        fields = super().purchase_book_fields()
        fields.extend(
            [
                {
                    "name": "Fecha Retención",
                    "field": "date_retention",
                    "size": 12,
                },
                {
                    "name": "N° Retención",
                    "field": "number_retention",
                    "size": 20,
                },
                {"name": "IVA retenido", "field": "iva_retained", "format": "number"},
            ]
        )
        return fields

    def _get_retention_domain(self):
        is_purchase = self.report == "purchase"
        field_date = "date" if is_purchase else "date_accounting"
        move_type = (
            ["out_invoice", "out_refund"] if not is_purchase else ["in_invoice", "in_refund"]
        )

        domain = [
            (field_date, ">=", self.date_from),
            (field_date, "<=", self.date_to),
            ("type", "in", move_type),
            ("type_retention", "=", "iva"),
            ("state", "=", "emitted"),
            ("company_id", "=", self.company_id.id),
        ]
        return domain

    # def search_moves(self):
    #     res_moves = super().search_moves()

    #     # retention = self.env["account.retention"]
    #     # domain = self._get_retention_domain()
    #     # retention_ids = retention.search(domain)
    #     # moves = retention_ids.mapped("retention_line_ids.move_id")
    #     # res_moves |= moves

    #     # return res_moves.sorted(lambda m: f"{m.invoice_date} {m.correlative}")
    #     return res_moves

    def _sort_book_data(self, lines_data: list):
        return sorted(
            lines_data, 
            key=lambda x: f"{x['_sort_document_date']}-{x['_sort_document_number']}-{x['_sort_order']}"
        )

    def parse_sale_book_data(self):
        retention = self.env["account.retention"]
        domain = self._get_retention_domain()
        retention_ids = retention.search(domain)
        retention_lines = retention_ids.retention_line_ids

        withholdings_data = []
        for rl in retention_lines:
            move = rl.move_id
            multiplier = -1 if move.move_type == "out_refund" else 1
            withholdings_data.append(
                {
                    "_id": move.id,
                    "_sort_document_date": move.invoice_date,
                    "_sort_document_number": move.l10n_latam_document_number if move.is_invoice() else move.name,
                    "_sort_order": 20,
                    "document_date": self._format_date(move.invoice_date),
                    "accounting_date": self._format_date(move.date),
                    "vat": move.vat,
                    "partner_name": move.invoice_partner_display_name,
                    "document_number": "-",
                    "move_type": self._determinate_type_for_move(move),
                    "transaction_type": "COM",
                    "number_invoice_affected": move.l10n_latam_document_number if move.is_invoice() else move.name,
                    "correlative": '-',
                    "reduced_aliquot": 0,
                    "general_aliquot": 0,
                    "extend_aliquot":  0,
                    "total_sales_iva": 0,
                    "total_sales_not_iva": 0,
                    "amount_reduced_aliquot": 0,
                    "amount_general_aliquot": 0,
                    "amount_extend_aliquot": 0,
                    "tax_base_reduced_aliquot": 0,
                    "tax_base_general_aliquot": 0,
                    "tax_base_extend_aliquot": 0,
                    "date_retention": self._format_date(rl.retention_id.date),
                    "number_retention": rl.retention_id.number,
                    "iva_retained": rl.retention_amount * multiplier,
                })

        data = super().parse_sale_book_data()

        for record in data:
            record.update({
                "date_retention": "",
                "number_retention": "",
                "iva_retained": 0,
            })

        return self._sort_book_data(data + withholdings_data)

    def parse_purchase_book_data(self):
        retention = self.env["account.retention"]
        domain = self._get_retention_domain()
        retention_ids = retention.search(domain)
        retention_lines = retention_ids.retention_line_ids

        withholdings_data = []
        for rl in retention_lines:
            move = rl.move_id
            multiplier = -1 if move.move_type == "in_refund" else 1
            withholdings_data.append(
                {
                    "_id": move.id,
                    "_sort_document_date": move.invoice_date,
                    "_sort_document_number": move.l10n_latam_document_number if move.is_invoice() else move.name,
                    "_sort_order": 20,
                    "document_date": self._format_date(move.invoice_date),
                    "accounting_date": self._format_date(move.date),
                    "vat": move.vat,
                    "partner_name": move.invoice_partner_display_name,
                    "document_number": "-",
                    "move_type": self._determinate_type_for_move(move),
                    "transaction_type": "COM",
                    "number_invoice_affected": move.l10n_latam_document_number if move.is_invoice() else move.name,
                    "correlative": '-',
                    "reduced_aliquot": 0,
                    "general_aliquot": 0,
                    "extend_aliquot":  0,
                    "total_purchases_iva": 0,
                    "total_purchases_not_iva": 0,
                    "amount_reduced_aliquot": 0,
                    "amount_general_aliquot": 0,
                    "amount_extend_aliquot": 0,
                    "tax_base_reduced_aliquot": 0,
                    "tax_base_general_aliquot": 0,
                    "tax_base_extend_aliquot": 0,
                    "date_retention": self._format_date(rl.retention_id.date),
                    "number_retention": rl.retention_id.number,
                    "iva_retained": rl.retention_amount * multiplier,
                })

        data = super().parse_purchase_book_data()

        for record in data:
            record.update({
                "date_retention": "",
                "number_retention": "",
                "iva_retained": 0,
            })

        return self._sort_book_data(data + withholdings_data)

    def _fill_sales_summary(self, summary: dict, line: dict):
        summary = super()._fill_sales_summary(summary, line)
        summary['iva_retenido'] = summary['iva_retenido'] + line['iva_retained']

        return summary

    def _fill_purchases_summary(self, summary: dict, line: dict):
        summary = super()._fill_purchases_summary(summary, line)
        summary['iva_retenido'] = summary['iva_retenido'] + line['iva_retained']

        return summary

    def _sum_retention_total(self, lines):
        is_check_currency_system = self.currency_system
        retention = lines.mapped("retention_id")

        if (
            self.report == "purchase"
            and retention
            and self._check_future_retention_dates(retention.date)
            or lines.move_id.state == "cancel"
        ):
            return 0.0
        if not is_check_currency_system:
            return sum(lines.mapped("foreign_retention_amount"))

        return sum(lines.mapped("retention_amount"))

    def _check_future_retention_dates(self, cmp_date):
        return cmp_date < self.date_from or cmp_date > self.date_to
