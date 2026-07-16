import logging

from odoo import _, fields, models
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_is_zero, float_round
from odoo.tools.misc import formatLang
from odoo.addons.base.models.ir_model import MODULE_UNINSTALL_FLAG

_logger = logging.getLogger(__name__)


class AccountTax(models.Model):
    _inherit = "account.tax"

    l10n_ve_tax_type = fields.Selection(related='tax_group_id.l10n_ve_type', store=True)

    def unlink(self):
        for rec in self:
            if rec.l10n_ve_tax_type and not rec.env.context.get(MODULE_UNINSTALL_FLAG):
                raise UserError(_("No puede eliminar una alícuota de impuestos Venezolanos. Si desea que no se configure en productos nuevos, puede desactivarla."))
        return super().unlink()
