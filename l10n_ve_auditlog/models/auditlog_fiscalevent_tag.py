# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class AuditlogFiscalEventTag(models.Model):
    _name = 'auditlog.fiscalevent.tag'
    _description = 'Etiqueta de evento fiscal'

    name = fields.Char('Nombre', required=True)
    color = fields.Char('Color', required=False)

    # event_ids = fields.Many2many(
    #     'auditlog.fiscalevent.tag',
    #     'auditlog_fiscalevent_tag_rel',
    #     # 'tag_id',
    #     # 'event_id',
    #     string="Eventos",
    #     readonly=1
    # )

    event_count = fields.Integer(string="Eventos marcados", compute='_compute_event_count')

    # @api.depends('event_ids')
    def _compute_event_count(self):
        event_data = self.env['auditlog.fiscalevent']._read_group([('tag_ids', 'in', self.ids)],
                                                                  ['tag_ids'], ['__count'])
        data_map = {event_origin.id: count for event_origin, count in event_data}
        for tag in self:
            tag.event_count = data_map.get(tag.id, 0)
