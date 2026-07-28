# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class AuditlogLog(models.Model):
    _inherit = 'auditlog.log'
    _order = "create_date desc, id desc"
