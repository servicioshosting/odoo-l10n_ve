import logging


from odoo.upgrade import util

_logger = logging.getLogger(__name__)


def migrate(cr, version):

    fields = [
        ('account.move', 'correlative', 'l10n_ve_control_number'),
        ('account.move', 'l10n_ve_document_type_internal_type', 'l10n_ve_doc_type_internal_type'),
    ]
    for model, old, new in fields:
        try:
            _logger.info("Renaming field %s to %s", model + '.' + old, model + '.' + new)
            util.rename_field(cr, model, old, new)
        except:
            pass
