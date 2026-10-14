from odoo import fields, models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    # Odoo 18: do not redefine default_account_id domain (company_id → company_ids;
    # core uses _get_default_account_domain + check_company=True).
