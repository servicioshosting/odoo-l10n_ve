# -*- coding: utf-8 -*-
import logging

from odoo import SUPERUSER_ID, _, api, fields, models
from odoo.exceptions import AccessDenied, UserError, ValidationError
from odoo.http import DEFAULT_LANG, request

_logger = logging.getLogger(__name__)

EMPTY_DICT = {}


class ResUsers(models.Model):
    _inherit = 'res.users'

    login_attempt_ids = fields.One2many(comodel_name='users.login.attempts', inverse_name='user_id')

    @classmethod
    def authenticate(cls, db, login, password, user_agent_env):
        """Verifies and returns the user ID corresponding to the given
          ``login`` and ``password`` combination, or False if there was
          no matching user.
           :param str db: the database on which user is trying to authenticate
           :param str login: username
           :param str password: user password
           :param dict user_agent_env: environment dictionary describing any
               relevant environment attributes
        """
        envvars = request.httprequest.environ if request else EMPTY_DICT

        vars = {
            'username': login,
            'method': 'login',
            'ip': envvars.get('REMOTE_ADDR', False) or user_agent_env.get('REMOTE_ADDR', False),
            'user_agent': envvars.get('HTTP_USER_AGENT', False),
            'successful': False,
            'user_id': False,
        }

        try:
            uid = super(ResUsers, cls).authenticate(db, login, password, user_agent_env)
            with cls.pool.cursor() as cr:
                env = api.Environment(cr, SUPERUSER_ID, {})

                vars['successful'] = True
                vars['user_id'] = uid
                env['users.login.attempts'].create(vars)
        except AccessDenied:
            with cls.pool.cursor() as cr:
                env = api.Environment(cr, SUPERUSER_ID, {})

                env['users.login.attempts'].create(vars)
            raise
        return uid
