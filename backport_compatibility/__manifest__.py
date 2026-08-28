# -*- coding: utf-8 -*-
{
    'name': "Modulo de Compatibilidad con Backport",

    'summary': "Se asegura de corre scripts de migracion",

    'description': """ """,

    'author': "Servitepuy, C.A.",
    'website': "https://servicioshosting.com",
    'category': 'Other',
    'version': '17.0.0.0.1',
    'depends': ['base'],
    'data': [
        # 'security/ir.model.access.csv',
        # 'views/views.xml',
        # 'views/templates.xml',
    ],
    'auto_install': True,
    "post_init_hook": "post_init_hook",
}

