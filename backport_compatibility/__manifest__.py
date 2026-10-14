{
    'name': "Modulo de Compatibilidad con Backport",

    'summary': "Se asegura de corre scripts de migracion",

    'description': """ """,

    'author': "Servitepuy, C.A.",
    'license': "Other proprietary",
    'website': "https://servicioshosting.com",
    'category': 'Other',
    'version': "18.0.1.0.0",
    'depends': ['base'],
    'data': [
        # 'security/ir.model.access.csv',
        # 'views/views.xml',
        # 'views/templates.xml',
    ],
    'auto_install': True,
    "post_init_hook": "post_init_hook",
}

