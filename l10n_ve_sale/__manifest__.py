{
    "name": "Venezuela - Ventas",
    "summary": """
        Módulo de Ventas Venezuela
    """,
    "license": "LGPL-3",
    "author": "binaural-dev",
    "website": "https://binauraldev.com/",
    "category": "Sales/Sales",
    "version": "17.0.1.2.0",
    # any module necessary for this one to work correctly
    "depends": [
        "base",
        "sale",
        "l10n_ve_base",
        "l10n_ve_tax",
        "sale_management",
        "l10n_ve_rate",
        "l10n_ve_contact",
        "l10n_ve_invoice",
        "l10n_ve_filter_partner",
    ],
    'auto_install': [
        "sale",
        "l10n_ve_base",
    ],
    "data": [
        "data/ir_cron.xml",
        "security/ir.model.access.csv",
        "security/res_groups.xml",
        "views/account_move_views.xml",
        "views/menuitems.xml",
        "views/product_pricelist_item_views.xml",
        "views/res_config_settings.xml",
        "views/sale_order.xml",
        "report/report_sale_document.xml",
        "wizard/sale_order_discount_views.xml"
    ],
    "images": ["static/description/icon.png"],
    "application": True,
    "pre_init_hook": "pre_init_hook",
}
