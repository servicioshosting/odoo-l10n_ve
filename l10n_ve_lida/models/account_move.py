import logging

from odoo import fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    l10n_ve_document_series = fields.Char("Serie de documentos", related='journal_id.l10n_ve_document_series', store=True, index=True)

    def _l10n_ve_get_formatted_sequence(self, number=0):
        serie = self.l10n_ve_document_series or ''
        return "%s %s%08d" % (self.l10n_latam_document_type_id.doc_code_prefix, serie, number)

    def _get_starting_sequence(self):
        """ If use documents then will create a new starting sequence using the document type code prefix and the
        journal document number with a 8 padding number """
        if self.journal_id.l10n_latam_use_documents and self.company_id.account_fiscal_country_id.code == "VE":
            if self.l10n_latam_document_type_id:
                return self._l10n_ve_get_formatted_sequence()
        return super()._get_starting_sequence()

    def _get_last_sequence(self, relaxed=False, with_prefix=None):
        last_sequence = super(AccountMove, self)._get_last_sequence(relaxed, with_prefix)
        # _logger.warning("_get_last_sequence(relaxed=%s, with_prefix=%s): %s", relaxed, with_prefix, last_sequence)
        # raise UserError("_get_last_sequence(relaxed=%s, with_prefix=%s): %s" % (relaxed, with_prefix, last_sequence))

        if not last_sequence:
            set_seq = 0
            if self.l10n_latam_document_type_id.internal_type == 'invoice':
                set_seq = int(self.journal_id.l10n_ve_invoice_first_document_number)
            elif self.l10n_latam_document_type_id.internal_type == 'credit_note':
                set_seq = int(self.journal_id.l10n_ve_credit_note_first_document_number)
            elif self.l10n_latam_document_type_id.internal_type == 'debit_note':
                set_seq = int(self.journal_id.l10n_ve_debit_note_first_document_number)

            set_seq = set_seq-1

            if set_seq > 0:
                return self._l10n_ve_get_formatted_sequence(set_seq)

        return last_sequence

    def _get_last_sequence_domain(self, relaxed=False):
        where_string, param = super(AccountMove, self)._get_last_sequence_domain(relaxed)
        if self.company_id.account_fiscal_country_id.code == "VE" and self.l10n_latam_use_documents:
            has_document_series = self.l10n_ve_document_series and len(self.l10n_ve_document_series) > 0
            where_string = where_string.replace(
                'journal_id = %(journal_id)s', 
                'journal_id in (%(available_journal_ids)s)'
            )
            if has_document_series:
                where_string += ' AND l10n_ve_document_series = %(l10n_ve_document_series)s'
            else:
                where_string += ' AND l10n_ve_document_series is NULL'
                
            where_string += ' AND company_id = %(company_id)s AND l10n_latam_document_type_id = %(l10n_latam_document_type_id)s'

            param['available_journal_ids'] = ",".join(map(str, self.env['account.journal'].search([('type', '=', self.journal_id.type)]).ids))
            param['l10n_ve_document_series'] = self.l10n_ve_document_series or None
            param['company_id'] = self.company_id.id or False
            param['l10n_latam_document_type_id'] = self.l10n_latam_document_type_id.id or 0
            # _logger.warning("_get_last_sequence_domain: %s", {'where': where_string, 'param': param})
        return where_string, param

    def button_draft(self):
        """
        Limpia el número de documento al volver un documento a borrador
        """
        res = super(AccountMove, self).button_draft()
        for move in self.filtered(lambda x: not x.posted_before):
            move.l10n_latam_document_number = False
        return res

    def button_cancel(self):
        """
        Limpia el número de documento al cancelar el movimiento para evitar que se ruede la numeración
        """
        not_posted = self.filtered(lambda x: not x.posted_before and x.l10n_latam_document_number)
        if not_posted:
            not_posted.write({'l10n_latam_document_number': False})

        res = super(AccountMove, self).button_cancel()
        return res
