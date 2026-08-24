import logging
from odoo.upgrade import util
from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)

def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    modules_to_merge = [
        { "old": "l10n_ve_location_extensions", "into": "l10n_ve_location" },
    ]

    for module in modules_to_merge: 
        if not util.module_installed(env.cr, module["old"]):
            _logger.info(f'[backport_compatibility] {module['old']} no esta instalado...')
            continue
        
        _logger.info(f"Merging {module['old']} modules into {module['into']}")
        util.merge_module(cr=env.cr, old=module['old'], into=module['into'], update_dependers=True)
        _logger.info(f"{module['old']} modules uninstalled")
    ...