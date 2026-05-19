import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class AccountJournal(models.Model):
    _inherit = "account.journal"

    l10n_ve_document_series = fields.Char("Serie de documentos", help='El prefijo de la serie de documentos de la sucursal/punto correspondiente', default=None, size=10)

    l10n_ve_invoice_first_document_number = fields.Integer("Número de la primera factura")
    l10n_ve_credit_note_first_document_number = fields.Integer("Número de la primera nota de crédito")
    l10n_ve_debit_note_first_document_number = fields.Integer("Número de la primera  nota de débito")

    @api.onchange('company_id', 'type', 'l10n_ve_document_series')
    def _onchange_company(self):
        self.l10n_latam_use_documents = self.country_code == 'VE' and \
            (self.type in ['sale', 'purchase'] and self.l10n_latam_company_use_documents)

    @api.constrains('l10n_ve_document_series')
    def _check_document_series(self):
        if self.filtered(lambda j: j.l10n_ve_document_series and not j.l10n_ve_document_series.isalnum()):
            raise ValidationError(_('La serie de documentos debe ser alfanumérica'))

    @api.onchange('type', 'l10n_latam_use_documents')
    def _onchange_journal_type(self):
        if self.type != 'sale':
            self.l10n_ve_document_series = False
            self.l10n_ve_invoice_first_document_number = False
            self.l10n_ve_credit_note_first_document_number = False
            self.l10n_ve_debit_note_first_document_number = False
        else:
            self.l10n_ve_invoice_first_document_number = self.l10n_ve_invoice_first_document_number or 1
            self.l10n_ve_credit_note_first_document_number = self.l10n_ve_credit_note_first_document_number or 1
            self.l10n_ve_debit_note_first_document_number = self.l10n_ve_debit_note_first_document_number or 1
