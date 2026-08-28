import logging
from odoo.upgrade import util
from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)

def migrate(cr, version):

    env = api.Environment(cr, SUPERUSER_ID, {})
    
    modules_to_remove = [
        'l10n_ve_contact_extensions',
        'l10n_ve_location_extensions',
        'l10n_ve_withholding_extensions',
        'l10n_ve_base'
    ]

    for old_module in modules_to_remove:        
        _logger.info(f"[backport compatibility] Removiendo {old_module}...")
        util.remove_module(env.cr, old_module)
        # util.remove_module(env.cr, old_module)
        env.cr.commit()


   