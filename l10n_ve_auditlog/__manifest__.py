{
    "name": "Venezuela - Auditoría",
    "summary": """
        Módulo de Auditoría de la localización de Venezuela
    """,
    "license": "LGPL-3",
    "author": "Servitepuy, C.A.",
    "website": "https://servicioshosting.com",
    "category": "Technical",
    "version": "17.0.0.0.0",
    'data': [
        "data/auditlog_fiscalevent_tag.xml",
        "data/auditlog_rule.xml",
        "data/ir_cron.xml",
        "security/ir.model.access.csv",
        "views/auditlog_http_request_views.xml",
        "views/auditlog_http_session_views.xml",
        "views/auditlog_log_views.xml",
        "views/users_login_attempts_views.xml",
        "views/auditlog_fiscalevent_views.xml",
        "views/auditlog_fiscalevent_tag_views.xml",
        "views/menu.xml",
    ],
    "depends": [
        "base",
        "auditlog",
    ],
}
