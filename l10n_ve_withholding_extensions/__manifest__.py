# -*- coding: utf-8 -*-
{
    "name": "Venezuela - Retenciones extensiones",
    "summary": """Extiende el Módulo de Retenciones Venezuela""",
    "author": "LIDALabs",
    "website": "https://lidalabs.com",
    "category": "Accountant/Accountant",
    "version": "17.0.1.4.0",
    "license": "LGPL-3",
    "depends": [
        "account",
        "l10n_ve_invoice_extensions",
        "l10n_ve_payment_extension"
    ],
    "auto_install": True,
    "application": False,
    "data": [
        "security/ir.model.access.csv",
        "views/account_move_views.xml",
        "views/retention_line_report_views.xml",
        "views/account_withholding_report_views.xml",
        "wizard/account_payment_register.xml",
    ],
    "demo": [
    ],
    "post_init_hook": "setup_accounts",
}
