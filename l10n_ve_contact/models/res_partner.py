import logging
import re

from odoo import _, api, fields, models
from odoo.exceptions import UserError, MissingError, ValidationError

from ...tools import binaural_cne_query

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = "res.partner"

    name = fields.Char(tracking=True)

    mobile = fields.Char(tracking=True)

    property_supplier_payment_term_id = fields.Many2one(tracking=True)

    property_payment_term_id = fields.Many2one(tracking=True)

    property_product_pricelist = fields.Many2one(tracking=True)

    property_account_position_id = fields.Many2one(tracking=True)

    street = fields.Char(tracking=True)

    street2 = fields.Char(tracking=True)

    country_id = fields.Many2one(
        'res.country',
        default=lambda self: self.env.ref('base.ve')
    )

    l10n_ve_vat = fields.Char('Venezuelan VAT', index=True, compute="_compute_l10n_ve_vat", store=True)
    l10n_ve_vat_formatted = fields.Char('Venezuelan VAT Formatted', index=True, compute="_compute_l10n_ve_vat", store=True)

    state_id = fields.Many2one(tracking=True)

    city_id = fields.Many2one(tracking=True)
    
    municipality = fields.Many2one(tracking=True)

    parish_id = fields.Many2one(tracking=True)

    zip = fields.Char(tracking=True)
   
    identity_document = fields.Char("Identify Document")

    def _default_company_id(self):
        company_id = self.env.company.id
        return company_id

    prefix_vat = fields.Selection(
        [
            ("V", "V"),
            ("E", "E"),
            ("J", "J"),
            ("G", "G"),
            ("P", "P"),
            ("C", "C"),
        ],
        string="Prefix VAT",
        default="V",
        help="Prefix of the VAT number",
        tracking=True,
    )

    def l10n_ve_identification_validation(self):
        person_vat_pattern = "^[0-9]{1,9}$"
        enterprise_vat_pattern = "^[0-9]{9}$"
        for partner in self:
            # TODO: Permitir saltar esta validación según el contexto.
            # En este punto puede que el partner se este creando como parte de un usuario y en el formulario de usuario no hay forma de agregar VAT.
            # En los formularios adecuados estos campos son requeridos.
            if not partner.prefix_vat or not partner.vat:
                continue
            # if not partner.user_ids and not partner.prefix_vat:
            #     raise ValidationError(_("Debe indicar el tipo de CI/RIF"))
            # if not partner.user_ids and not partner.vat:
            #     raise ValidationError(_("Debe indicar el CI/RIF"))
            if partner.prefix_vat == 'P':
                continue

            if partner.prefix_vat in ('V', 'E'):
                if partner.vat and not (re.match(person_vat_pattern, partner.vat)):
                    raise ValidationError(_("The vat field only accepts numbers and must be between 1 and 9 digits"))
            elif partner.vat and not re.match(enterprise_vat_pattern, partner.vat):
                raise ValidationError(_("The vat field only accepts numbers and must be 9 digits long"))

    def check_duplicate_vat(self, prefix_vat, vat, company_id=None):
        error_message = ""
        domain = [
            ("prefix_vat", "=", prefix_vat),
            ("vat", "=", vat),
            ("id", "!=", self.id if self else False),
        ]

        if prefix_vat and vat:
            if self.env.company.validate_user_creation_by_company:
                domain.extend(
                    [
                        ("company_id", "=", company_id or self.env.company.id),
                    ]
                )
                error_message = _(
                    "There is already a partner with the same VAT number for this company."
                )
            elif self.env.company.validate_user_creation_general:
                error_message = _(
                    "A partner with the same VAT number already exists for this company."
                )

            existing_partner = self.env["res.partner"].search(domain)
            if existing_partner:
                raise ValidationError(error_message)

    def check_duplicate_email(self, email, company_id=None):
        if email and (self.env.company.validate_user_creation_general or self.env.company.validate_user_creation_by_company):
            domain = [
                ("email", "=", email),
                ("id", "!=", self.id if self else False),
            ]

            if self.env.company.validate_user_creation_by_company:
                domain.extend(
                    [
                        ("company_id", "=", company_id or self.env.company.id),
                    ]
                )
                error_message = _(
                    "A partner with the same email address already exists for this company."
                )
            elif self.env.company.validate_user_creation_general:
                error_message = _(
                    "A partner with the same email already exists.")
            else:
                error_message = _(
                    "A partner with the same email address already exists for this company."
                )

            existing_partner = self.env["res.partner"].search(domain, limit=1)
            if existing_partner:
                raise ValidationError(error_message)

    company_id = fields.Many2one(
        default=_default_company_id,
    )

    @api.model_create_multi
    def create(self, vals_list):
        """This function assign the name of the person by the vat number and the prefix of the vat number
        calling the function get_default_name_by_vat from binaural_cne_query before create the partner

        Args:
            prefix_vat (string): prefix of the vat number (V)
            vat (string): vat number of the person, this number is unique in Venezuela

        Raises:
            UserError: Error to connect with CNE, please check your internet connection or try again later

        """
        for vals in vals_list:
            if vals.get("vat") and not vals.get("name", False):
                prefix_vat = vals.get("prefix_vat")
                name = vals.get("name")
                vat = vals.get("vat")
                if prefix_vat == "V" and not name and prefix_vat in ["V", "E"]:
                    name, flag = binaural_cne_query.get_default_name_by_vat(
                        self, prefix_vat, vat
                    )
                    if not flag:
                        continue
                    vals["name"] = name
            if "vat" and "prefix_vat" in vals:
                self.check_duplicate_vat(
                    vals.get("prefix_vat"), vals.get("vat"))
            if "email" in vals:
                self.check_duplicate_email(vals.get("email"))
        return super(ResPartner, self).create(vals_list)

    def write(self, vals):
        res = super().write(vals)
        if "prefix_vat" and "vat" in vals:
            for record in self:
                record.check_duplicate_vat(
                    vals.get("prefix_vat"), vals.get("vat"))
        if "email" in vals:
            for record in self:
                record.check_duplicate_email(vals.get("email"))
        return res

    def _check_vat(self):
        pattern = "^[0-9]*$"
        for record in self:
            if record.vat:
                if not re.match(pattern, record.vat):
                    raise MissingError(_("The vat field only accepts numbers"))
    
    @api.constrains('vat', 'country_id', 'prefix_vat')
    def check_vat(self):
        """ Since we validate more documents than the vat for Venezuelan partners (RIF, CI) we
        extend this method in order to process it. """
        if self.env.company.country_code != 'VE':
            return super(ResPartner, self).check_vat()

        # l10n_ve_partners = self.filtered(lambda x: x.country_code == 'VE')
        # l10n_ve_partners.l10n_ve_identification_validation()
        # return super(ResPartner, self - l10n_ve_partners).check_vat()
        self.l10n_ve_identification_validation()

    @api.onchange("vat", "prefix_vat")
    def _onchange_(self):
        """This function assign the name of the person by the vat number and the prefix of the vat number
        calling the function get_default_name_by_vat from binaural_cne_query

        Args:
            prefix_vat (string): prefix of the vat number (V)
            vat (string): vat number of the person, this number is unique in Venezuela
        """
        if self.vat and not self.name and self.prefix_vat in ["V", "E"]:
            self._check_vat()
            name, flag = binaural_cne_query.get_default_name_by_vat(
                self, self.prefix_vat, self.vat
            )
            if not flag:
                return
            for record in self:
                record.name = name

    @api.onchange("vat")
    def _onchange_vat_(self):
        """This function checks that if a VAT is being added and the identity_document field is empty,
        the identity_document field is assigned the same value as the VAT.
        """
        for record in self:
            if not record.identity_document:
                record.identity_document = record.vat
    
    @api.onchange("prefix_vat")
    def _onchange_prefix_vat(self):
        if not self.prefix_vat:
            return

        if self.prefix_vat in ('J', 'G', 'C'):
            self.company_type = 'company'
        else:
            self.company_type = 'person'

    @api.depends('prefix_vat', 'vat')
    def _compute_l10n_ve_vat(self):
        for partner in self:
            if partner.country_code == 'VE' and partner.prefix_vat and partner.vat:
                partner.l10n_ve_vat = "%s%s" % (partner.prefix_vat, partner.vat)
                if len(partner.vat) < 9 or partner.prefix_vat == 'P':
                    partner.l10n_ve_vat_formatted = "%s-%s" % (partner.prefix_vat, partner.vat)
                else:
                    partner.l10n_ve_vat_formatted = "%s-%s-%s" % (partner.prefix_vat, partner.vat[:-1], partner.vat[-1])
