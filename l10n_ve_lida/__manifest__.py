# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": "Venezuela - Plan de cuentas",
    "category": "Accounting/Localizations/Account Charts",
    "website": "https://www.odoo.com/documentation/17.0/applications/finance/fiscal_localizations.html",
    "icon": "/account/static/description/l10n.png",
    "countries": ["ve"],
    "license": "LGPL-3",
    "version": "17.0.1.0.9",
    "description": """
        Plantilla de plan de cuentas de servicio donde se agregan las
        cuentas contables y diarios para tipo de empresa servicio
""",
    "depends": [
        "base",
        "account",
        "account_accountant",
        "sale",
        "contacts",
        "l10n_ve_auditlog",
        "l10n_ve_base",
        "l10n_latam_invoice_document",
    ],
    "data": [
        "data/decimal_precision.xml",
        "data/l10n_latam.document.type.csv",
        "data/res.bank.csv",
        "views/account_tax_views.xml",
        "views/account_journal_view.xml",
        "views/account_move_view.xml",
        "views/account_move.xml",
        "views/res_config_settings.xml",
        "views/res_config_settings_currency.xml",
        "views/res_currency_views.xml",
        "views/res_partner.xml",
    ],
    "demo": [
        "demo/demo_company.xml",
    ],

    "post_init_hook": "post_init_hook",
    "assets": {
        "web.assets_backend": ["l10n_ve_lida/static/src/components/**/*"],
    },
}
