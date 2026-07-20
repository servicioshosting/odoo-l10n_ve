import logging

from odoo import _, api, models

_logger = logging.getLogger(__name__)


class AccountMoveRetention(models.Model):
    _inherit = "account.move"

    @api.onchange('partner_id', "move_type", "company_id")
    def _onchange_warn_against_ci(self):
        if not self.partner_id or self.move_type not in ['in_invoice', 'in_refund', 'in_receipt'] or self.company_id.taxpayer_type != 'special':
            return False

        if self.partner_id.prefix_vat in ['V', 'E', 'P'] and len(self.partner_id.vat) < 9:
            return {
                "warning": {
                    "title": (_("Advertencia")),
                    "message": (_(
                        "Este proveedor esta registrado con un documento de identidad personal."
                        " La empresa activa es contribuyente especial y debe emitir retenciones para esta factura."
                        " Se sugiere que ingrese el RIF del proveedor como documento de identidad."
                    )),
                    "sticky": True,
                    "next": {"type": "ir.actions.act_window_close"},
                }
            }
