# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class AccountResequenceWizard(models.TransientModel):
    _inherit = 'account.resequence.wizard'

    def resequence(self):
        return super(AccountResequenceWizard, self.with_context(auditlog_disabled=True))

