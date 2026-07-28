# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class UsersLoginAttempts(models.Model):
    _name = 'users.login.attempts'
    _description = 'Users login Attempts'

    name = fields.Datetime('Fecha y hora', default=fields.Datetime.now)
    username = fields.Char("Username", required=True, help="Esta información se registra para facilitar la identificación de posibles credenciales filtradas.")
    method = fields.Char("Método", required=True, help="Método de acceso. En caso de que se soporten distintos mecanismos de acceso (email, oauth, etc), cuál se está intentando utilizar.")
    ip = fields.Char("IP", required=True, size=128)
    user_agent = fields.Char("Browser user-agent", index='trigram')
    successful = fields.Boolean("Exitoso", required=True, default=False, help="")

    user_id = fields.Many2one(comodel_name='res.users')
