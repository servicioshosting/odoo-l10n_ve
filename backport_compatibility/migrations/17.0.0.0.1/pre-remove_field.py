import logging
from odoo.upgrade import util

_logger = logging.getLogger(__name__)

def migrate(cr, version):
    
    field_to_remove = []

    for field, model in field_to_remove:
        _logger.info(f"[pre_remove_fields] removiendo el campo {field} en {model}")
        util.remove_field(cr, model, field, True)

        _logger.info(f"[pre_remove_fields] se elimino el campo {field} en {model}")

        
    



