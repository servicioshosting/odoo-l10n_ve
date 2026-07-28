# -*- coding: utf-8 -*-
import datetime as dt
import logging
from collections import defaultdict
from textwrap import shorten

from odoo import SUPERUSER_ID, _, api, fields, models
import os

AUDITLOG_IS_DISABLED = os.environ.get('AUDITLOG_DISABLED', True)

_logger = logging.getLogger(__name__)


class AuditlogFiscalEvent(models.Model):
    _name = 'auditlog.fiscalevent'
    _description = 'Evento fiscal'

    _order = 'name desc'

    name = fields.Datetime('Fecha', default=fields.Datetime.now, readonly=True)
    user_id = fields.Many2one('res.users', string='Autor', readonly=True)
    http_session_id = fields.Many2one(
        "auditlog.http.session", string="Sesión", index=True, readonly=True, required=False)
    http_request_id = fields.Many2one(
        "auditlog.http.request", string="HTTP Request", index=True, readonly=True, required=False)
    tag_ids = fields.Many2many(
        'auditlog.fiscalevent.tag',
        'auditlog_fiscalevent_tag_rel',
        'event_id',
        'tag_id',
        string="Etiquetas"
    )

    model_id = fields.Many2one('ir.model', 'Modelo', readonly=True)
    res_id = fields.Integer("ID del registro", readonly=True)
    res_name = fields.Char('Nombre del registro durante el evento', help="Nombre en el momento en el que ocurrió el evento", readonly=True)

    model_name = fields.Char('Nombre del modelo', compute='_compute_model_name', store=True)

    message = fields.Char("Mensaje", size=300, readonly=True)
    metadata = fields.Json("Metadata", readonly=True)

    summary = fields.Char("Resumen", compute='_compute_summary')
    has_record = fields.Boolean("¿Asociado a un registro?", compute='_compute_has_record')
    record_still_exists = fields.Boolean("¿Registro aún existe?", compute='_compute_record_still_exists')
    current_res_name = fields.Char('Nombre actual del registro', compute='_compute_current_res_name')

    @api.depends('message')
    def _compute_summary(self):
        for rec in self:
            rec.summary = rec.message and shorten(rec.message, 100)

    @api.depends('res_id')
    def _compute_has_record(self):
        for rec in self:
            rec.has_record = bool(rec.res_id)

    @api.depends('model_id')
    def _compute_model_name(self):
        for rec in self:
            rec.model_name = False
            if not rec.model_id:
                continue
            rec.model_name = rec.model_id.model

    @api.depends('model_name', 'res_id')
    def _compute_record_still_exists(self):
        for rec in self:
            rec.record_still_exists = False
        return

        ids_grouped = defaultdict(lambda: [])
        grouped = {}

        for rec in self:
            ids_grouped[rec.model_name].append(rec.res_id)
            if (rec.model_name, rec.res_id) not in grouped:
                grouped[(rec.model_name, rec.res_id)] = rec
            else:
                grouped[(rec.model_name, rec.res_id)] |= rec

        for model_name, ids in ids_grouped.items():
            exist = [
                vals['id']
                for vals in self.env[model_name].search_read([('id', 'in', ids)], ['id']) if model_name in self.env
            ]
            for id in exist:
                for rec in grouped[(rec.model_name, id)]:
                    rec.record_still_exists = True

    @api.depends('model_name', 'res_id')
    def _compute_current_res_name(self):
        for rec in self:
            rec.current_res_name = rec.res_name
            continue
            # if rec.model_name not in self.env:
            #     continue
            # Model = self.env[rec.model_name]
            # res = Model.browse(rec.res_id)
            # res.flush_recordset()
            # rec.current_res_name = "found"
            # rec.current_res_name = res.display_name
        # ids_grouped = {rec.model_name: [] for rec in self if rec}
        # grouped = {}
        # for rec in self:
        #     rec.current_res_name = '<borrado>'

        #     if rec.model_name not in self.env:
        #         continue
        #     ids_grouped[rec.model_name].append(rec.res_id)
        #     if (rec.model_name, rec.res_id) not in grouped:
        #         grouped[(rec.model_name, rec.res_id)] = rec
        #     else:
        #         grouped[(rec.model_name, rec.res_id)] |= rec
        
        # visited = defaultdict(lambda: 0)
        # for model_name, ids in ids_grouped.items():
        #     Model = self.env[model_name] if model_name in self.env else None
        #     if Model is None:
        #         continue

        #     print(model_name, ids)
        #     exist = []
        #     visited[model_name] = visited[model_name] + 1
        #     for res in Model.browse(ids):
        #         exist.append((res.id, res.display_name))

        #     for id, display_name in exist:
        #         for rec in grouped[(rec.model_name, id)]:
        #             rec.current_res_name = display_name

    @api.model
    def record_event(self, record, message, tag_ids=None, metadata=None):
        """Registra un evento

        :param record: El record involucrado
        :param message: El mensaje
        :type message: str
        :param tag_ids: Arreglo de `fields.Command`. Defaults to None.
        :type tag_ids: `iterable`
        :param metadata: Metadata. Defaults to None.
        :type metadata: `dict`
        """
        if AUDITLOG_IS_DISABLED:
            return None

        user_id = self.env.user.id
        model_name = None
        model_model = None
        model_id = None
        res_id = None
        res_name = None
        if record:
            model_name = record._name
            model_model = self.env['ir.model'].search([('model', '=', model_name)], limit=1)
            model_id = model_model.id
            res_id = record._origin.id
            res_name = record.display_name if res_id else f"[{model_model.name}] no almacenado"

        tag_ids = [
            fields.Command.link(self.env.ref(t).id) if type(t) == 'str' else t
            for t in tag_ids
        ] if tag_ids else None

        with self.pool.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {'recording_fiscal_event': True})

            http_request_model = env["auditlog.http.request"]
            http_session_model = env["auditlog.http.session"]
            http_session_id = http_session_model.current_http_session()
            http_request_id = http_request_model.current_http_request()

            event = env[self._name].create({
                'user_id': user_id,
                "http_request_id": http_request_id,
                "http_session_id": http_session_id,
                'tag_ids': tag_ids,
                'model_id': model_id,
                'model_name': model_name,
                'res_id': res_id,
                'res_name': res_name,
                'message': message,
                'metadata': metadata if type(metadata) == 'dict' else None,
            })

        return event

    @api.model
    def autovacuum(self, days=365*5):
        to_delete = self.search([('name', '<', dt.datetime.now() - dt.timedelta(days=-abs(days)))])
        to_delete.unlink()

    def action_record_view(self):
        self.ensure_one()

        return False
        return {
            # "name": "Balances de productos",
            "type": "ir.actions.act_window",
            "res_model": self.model_name,
            "view_mode": "tree,form",
            "domain": [("id", "=", self.res_id)],
            "context": {"create": 0, "edit": 0, "delete": 0},
        }
