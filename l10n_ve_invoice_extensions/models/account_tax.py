import logging

from odoo import _, fields, models
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_is_zero, float_round
from odoo.tools.misc import formatLang

_logger = logging.getLogger(__name__)


class AccountTax(models.Model):
    _inherit = "account.tax"

    l10n_ve_tax_type = fields.Selection(related='tax_group_id.l10n_ve_type', store=True)
