# -*- coding: utf-8 -*-
{
    "name": "Extensiones de Venezuela - Facturación",
    "summary": "Usa el modulo nativo l10n_latam_document_type para asignar números de documento.",
    "author": "LIDALabs",
    "website": "https://lidalabs.com",
    "category": "Accountant/Accountant",
    "version": "17.0.1.1.1",
    "license": "LGPL-3",
    "depends": [
        # "product",
        "account",
        "account_debit_note",
        "l10n_ve_lida",
        "l10n_ve_contact_extensions",
        "l10n_ve_invoice",
        "l10n_latam_invoice_document"
    ],
    "auto_install": True,
    "application": False,
    "data": [
        "data/l10n_ve_invoice_groups.xml",
        "data/ir_sequence_data.xml",
        # "data/report_paperformat_data.xml",
        "views/account_journal_views.xml",
        "views/account_move_view.xml",
        "views/product_views.xml",
        "report/invoice_payments_template.xml",
        "report/invoice_payments_report.xml",
        "report/report_templates.xml",
        "wizard/account_debit_note_view.xml",
        "wizard/account_move_reversal_view.xml",
        "wizard/invoice_payments_reports_wizard.xml",
        "views/menu.xml",
    ],
    "demo": [
    ],
}
