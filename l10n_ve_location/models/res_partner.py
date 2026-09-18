# -*- coding: utf-8 -*-
import re

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class ResCountryParishBinauralLocalizacion(models.Model):
    _inherit = 'res.partner'

    city_id = fields.Many2one("res.country.city", string="City")

    city = fields.Char(string="City related",
                       related="municipality.name", store=True)

    municipality = fields.Many2one("res.country.municipality", "Municipality", domain="[('state_id', '=', state_id)]")

    parish_id = fields.Many2one(
        "res.country.parish", domain="[('municipality_id', '=', municipality)]"
    )
