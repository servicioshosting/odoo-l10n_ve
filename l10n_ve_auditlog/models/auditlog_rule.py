# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


ACCOUNT_MOVE_FIELD_WHITELIST = set([
    'amount_residual',
    'amount_total',
    'company_currency_id',
    'company_id',
    'country_code',
    'currency_id',
    'date',
    'debit_origin_id',
    'foreign_rate',
    'free_form_copy_number',
    'igtf_amount',
    'igtf_base_amount',
    'igtf_percentage_fraction',
    'invoice_date',
    'invoice_date_due',
    'invoice_origin',
    'invoice_user_id',
    'is_contingency',
    'journal_id',
    'l10n_latam_document_number',
    'l10n_ve_control_number',
    'l10n_ve_doc_datetime',
    'l10n_ve_doc_type_internal_type',
    'l10n_ve_was_reversed',
    'manually_set_rate',
    'move_type',
    'name',
    'note_reason',
    'partner_id',
    'reversed_entry_id',
    'state',
    # 'tax_totals',
    'vat',
])
ACCOUNT_RETENTION_FIELD_WHITELIST = set([
    # 'name'
    # 'activity_ids'
    # 'base_currency_is_vef'
    'code'
    'company_currency_id'
    'company_id'
    # 'create_date'
    # 'create_uid'
    'date'
    'date_accounting'
    # 'foreign_currency_id'
    # 'foreign_total_invoice_amount'
    # 'foreign_total_iva_amount'
    # 'foreign_total_retention_amount'
    # 'id'
    'l10n_ve_control_number'
    # 'message_follower_ids'
    # 'message_ids'
    'name'
    'number'
    # 'original_lines_per_invoice_counter'
    'partner_id'
    # 'payment_ids'
    # 'retention_line_ids'
    'state'
    'total_invoice_amount'
    'total_iva_amount'
    'total_retention_amount'
    'type'
    'type_retention'
])


class AuditlogRule(models.Model):
    _inherit = 'auditlog.rule'

    def get_auditlog_fields(self, model):
        res = super().get_auditlog_fields(model)
        if model._name == 'account.move':
            res += ['name', 'amount_total']
        elif model._name == 'account.retention':
            res += []

        return res

    def _create_log_line_on_create(self, log_vals, fields_list, new_values, fields_to_exclude):
        return super()._create_log_line_on_create(log_vals, self._l10n_ve_filter_field_list(log_vals, fields_list), new_values, fields_to_exclude)

    def _create_log_line_on_read(self, log_vals, fields_list, read_values, fields_to_exclude):
        return super()._create_log_line_on_read(log_vals, self._l10n_ve_filter_field_list(log_vals, fields_list), read_values, fields_to_exclude)

    def _create_log_line_on_write(self, log_vals, fields_list, old_values, new_values, fields_to_exclude):
        return super()._create_log_line_on_write(log_vals, self._l10n_ve_filter_field_list(log_vals, fields_list), old_values, new_values, fields_to_exclude)

    def _l10n_ve_filter_field_list(self, log_vals, fields_list):
        """Filtra los campos y los modelos apropiadamente.

        Es importante que esta función se implemente de manera tal que no necesite heredar ninguno de los otros paquetes de la localización, dado que todos van a depender de esta."""
        reverse_model_map = {model_id: model_name for model_name, model_id in self.pool._auditlog_model_cache.items()}
        if reverse_model_map[log_vals['model_id']] == 'account.move':
            fields_set = set(fields_list)
            fields_set = fields_set - (fields_set-ACCOUNT_MOVE_FIELD_WHITELIST)
            return list(fields_set)
        elif reverse_model_map[log_vals['model_id']] == 'account.retention':
            fields_set = set(fields_list)
            fields_set = fields_set - (fields_set-ACCOUNT_RETENTION_FIELD_WHITELIST)
            return list(fields_set)

        return fields_list
