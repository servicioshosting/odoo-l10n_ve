# -*- coding: utf-8 -*-

import json
from logging import getLogger

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import date_utils
from urllib3 import request

_logger = getLogger(__name__)


class AccountJournal(models.Model):
    _inherit = "account.journal"

    def get_protected_fields_on_journals_with_documents(self):
        return ['l10n_ve_document_series']

    def write(self, vals):
        protected_fields = self.get_protected_fields_on_journals_with_documents()
        fields_to_check = [field for field in protected_fields if field in vals]

        if fields_to_check:
            self._cr.execute("SELECT DISTINCT(journal_id) FROM account_move WHERE posted_before = True")
            res = self._cr.fetchall()
            journal_with_entry_ids = [journal_id for journal_id, in res]

            for journal in self:
                if (
                    journal.company_id.account_fiscal_country_id.code != "VE"
                    or journal.type not in ['sale', 'purchase']
                    or journal.id not in journal_with_entry_ids
                ):
                    continue

                for field in fields_to_check:
                    if vals[field] != journal[field]:
                        raise UserError(
                            _("You can not change %s journal's configuration if it already has validated invoices", journal.name))

        return super().write(vals)
