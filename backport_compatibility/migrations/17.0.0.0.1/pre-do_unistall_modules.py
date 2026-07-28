import logging
from odoo.upgrade import util
from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)


def migrate(cr, version):

    env = api.Environment(cr, SUPERUSER_ID, {})

    modules_to_uninstall = [
        'l10n_ve_stock',
        'l10n_ve_stock_account',
        'l10n_ve_stock_purchase',
        'l10n_ve_stock_reports',
        'l10n_ve_pos_mf',
    ]

    for old_module in modules_to_uninstall:
        # if not util.module_installed(env.cr, old_module):
        #     _logger.info(f"[backport compatibility] {old_module} no esta instalado...")
        #     continue
        
        _logger.info(f"[backport compatibility] Desinstalando {old_module}...")
        util.uninstall_module(env.cr, old_module)
        # util.remove_module(env.cr, old_module)
        env.cr.commit()

        if util.module_installed(env.cr, old_module):
            _logger.warning(f"[backport compatibility] {old_module} NO se pudo desinstalar completamente")
        else:
            _logger.info(f"[backport compatibility] {old_module} desinstalado correctamente")
