from odoo import SUPERUSER_ID, api

from . import controllers
from . import models
from . import wizard
from . import report

def setup_accounts(env):
    env = api.Environment(env.cr, SUPERUSER_ID, {})

    if env.company.chart_template != 've_lida':
        return

    AccountChartTemplate = env['account.chart.template']

    vals = {}
    if not env.company.iva_supplier_retention_journal_id:
        acc = AccountChartTemplate.ref('lida_withholding_iva_suppliers', raise_if_not_found=False)
        vals['iva_supplier_retention_journal_id'] = acc and acc.id
    if not env.company.iva_customer_retention_journal_id:
        acc = AccountChartTemplate.ref('lida_withholding_iva_customers', raise_if_not_found=False)
        vals['iva_customer_retention_journal_id'] = acc and acc.id
    if not env.company.islr_supplier_retention_journal_id:
        acc = AccountChartTemplate.ref('lida_withholding_islr_suppliers', raise_if_not_found=False)
        vals['islr_supplier_retention_journal_id'] = acc and acc.id
    if not env.company.islr_customer_retention_journal_id:
        acc = AccountChartTemplate.ref('lida_withholding_islr_customers', raise_if_not_found=False)
        vals['islr_customer_retention_journal_id'] = acc and acc.id

    env.company.write(vals)
    return


import logging
from odoo.upgrade import util
from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)

def merge(env):
    env = api.Environment(env.cr, SUPERUSER_ID, {})

    modules_to_merge = [
        { "old": "l10n_ve_payment_extension", "into": "l10n_ve_withholding" },
    ]

    for module in modules_to_merge: 
        if not util.module_installed(env.cr, module["old"]):
            _logger.info(f'[backport_compatibility] {module['old']} no esta instalado...')
            continue
        
        _logger.info(f"Merging {module['old']} modules into {module['into']}")
        util.merge_module(cr=env.cr, old=module['old'], into=module['into'], update_dependers=True)
        _logger.info(f"{module['old']} modules uninstalled")

