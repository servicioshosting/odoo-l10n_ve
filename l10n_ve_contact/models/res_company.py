from odoo import models, fields, api, _

import logging

_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = "res.company"

    validate_user_creation_by_company = fields.Boolean(
        default = False,
        string='Validate user creation by company',
    )
    
    validate_user_creation_general = fields.Boolean(
        default = True,
        string='Validate user creation general',
    )

    l10n_ve_vat = fields.Char(related='partner_id.l10n_ve_vat', store=True)
    l10n_ve_vat_formatted = fields.Char(related='partner_id.l10n_ve_vat_formatted', store=True)
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            partner = self.env["res.partner"].create(
                {
                    "name": vals["name"],
                    "is_company": False,
                    "image_1920": vals.get("logo"),
                    "email": vals.get("email"),
                    "phone": vals.get("phone"),
                    "website": vals.get("website"),
                    "vat": vals.get("vat"),
                    "country_id": vals.get("country_id"),
                }
            )
            partner.company_id = False
            vals["partner_id"] = partner.id
        return super().create(vals_list)
