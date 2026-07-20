import csv
import os
import xml.etree.ElementTree as et
from datetime import datetime
from io import BytesIO, StringIO

import xlsxwriter
from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.tools import date_utils


class AccountWithholdingReport(models.TransientModel):
    _name = "account.withholding.report"
    _description = "Reporte de retenciones"
    _order = "period desc"
    _sql_constraints = [
        # ("unique_company_period", "UNIQUE(company_id,name)", "No puede generar más de un reporte de retenciones de ISLR para un período"),
    ]
    _check_company_auto = True

    name = fields.Char("Reporte", store=True, compute="_compute_period")
    period = fields.Char("Período", store=True, compute="_compute_period")
    company_id = fields.Many2one(
        "res.company",
        string="Empresa",
        required=True,
        readonly=True,
        default=lambda self: self.env.company,
    )
    year = fields.Integer("Año", required=True)
    month = fields.Selection([
        ('1', 'Enero'),
        ('2', 'Febrero'),
        ('3', 'Marzo'),
        ('4', 'Abril'),
        ('5', 'Mayo'),
        ('6', 'Junio'),
        ('7', 'Julio'),
        ('8', 'Agosto'),
        ('9', 'Septiembre'),
        ('10', 'Octubre'),
        ('11', 'Noviembre'),
        ('12', 'Diciembre'),
    ], "Mes", required=True)
    quincena = fields.Selection([
        ("01_quincena", "1era Quincena"),
        ("02_quincena", "2da Quincena"),
    ], "Tipo de retención", required=True, default='iva')
    # Lease como "Tipo de (impuesto de la) retención"
    tax_type = fields.Selection([
        ("iva", "IVA"),
        ("islr", "ISLR"),
    ], "Tipo de retención", required=True, default='iva')
    download_format = fields.Selection([
        ("excel", "excel"),
        ("seniat", "SENIAT "),
    ], "Formato de descarga", default=None)

    date_start = fields.Date("Inicio del período", store=True, compute="_compute_period")
    date_end = fields.Date("Fin del período", store=True, compute="_compute_period")

    withholdings_ids = fields.Many2many("account.retention", string="Retenciones")
    line_ids = fields.One2many("account.withholding.report.line", "report_id", string="Detalles")

    # xml_file = fields.Binary("XML report")
    # xlsx_file = fields.Binary("Excel report")

    # Related fields
    company_currency_id = fields.Many2one(string="Moneda", related="company_id.currency_id")
    company_vat = fields.Char(related="company_id.partner_id.l10n_ve_vat")

    def default_get(self, fields_list):
        vals = super().default_get(fields_list)
        last_month = date_utils.subtract(date_utils.start_of(fields.Datetime.today(), "month"), date_utils.relativedelta(months=1))

        if 'year' in fields_list:
            vals['year'] = last_month.year
        if 'month' in fields_list:
            vals['month'] = str(last_month.month)

        return vals

    @api.depends("year", "month", "tax_type", "quincena")
    def _compute_period(self):
        today = fields.Datetime.today()

        tax_type_strings = dict(self._fields['tax_type'].selection)
        quincena_strings = dict(self._fields['quincena'].selection)

        for rec in self:
            year = int(rec.year or today.year)
            month = int(rec.month or today.month)
            rec.period = "{:0>4d}{:0>2d}".format(year, month)
            rec.name = "Retenciones de {} {} {}".format(
                tax_type_strings.get(rec.tax_type), 
                rec.period, 
                quincena_strings.get(rec.quincena)
            )

            if rec.quincena == '01_quincena':
                rec.date_start = date_utils.start_of(datetime(year, month, 1), 'month')
                rec.date_end = date_utils.end_of(datetime(year, month, 15), 'day')
            else:
                rec.date_start = date_utils.start_of(datetime(year, month, 16), 'day')
                rec.date_end = date_utils.end_of(datetime(year, month, 1), 'month')

    @api.onchange("year", "month")
    def _onchange_period(self):
        for rec in self:
            rec._sync_lines()

    @api.constrains("year", "month")
    def _constrains_period(self):
        for rec in self:
            rec._sync_lines()

    def _sync_lines(self):
        for rec in self:
            if not rec.year or not rec.month:
                rec.withholdings_ids = False
                rec.line_ids = False
                continue

            rec.update(self._compute_lines(rec.tax_type, rec.year, rec.month, rec.company_id))

    @api.model
    def _compute_lines(self, tax_type, year, month, company):
        date_start = date_utils.start_of(datetime(int(year), int(month), 1), 'month')
        date_end = date_utils.end_of(date_start, 'month')

        search_domain = [
            ("type", "=", "in_invoice"),
            ("type_retention", "=", tax_type),
            ("state", "=", "emitted"),
            ("date_accounting", ">=", date_start),
            ("date_accounting", "<=", date_end),
            ("company_id", "=", company.id)
        ]

        withholdings_ids = self.env['account.retention'].search(search_domain)
        line_ids = [Command.clear()]
        if withholdings_ids:
            line_ids.extend(
                Command.create({
                    'withholding_id': w.retention_id._origin.id,
                    'withholding_line_id': w._origin.id,
                })
                for w in withholdings_ids.mapped('retention_line_ids')
            )
        return {
            'line_ids': line_ids,
            'withholdings_ids': [Command.set(withholdings_ids.ids)],
        }

    # @api.model_create_multi
    # def create(self, vals_list):
    #     # for vals in vals_list:
    #     #     vals.update(self._compute_lines(vals['year'], vals['month'], self.env.company))
    #     records = super().create(vals_list)

    #     return records

    def action_download_xlsx(self):
        self.ensure_one()
        self.download_format = 'excel'
        self.flush_recordset()

        return {
            "type": "ir.actions.act_url",
            "url": "/web/seniat/download_withholding_report?id=%s" % (self.id, ),
            "target": "self",
        }

    def action_download_seniat(self):
        self.ensure_one()
        self.download_format = 'seniat'
        self.flush_recordset()

        return {
            "type": "ir.actions.act_url",
            "url": "/web/seniat/download_withholding_report?id=%s" % (self.id, ),
            "target": "self",
        }

    def _make_islr_xlsx_report(self):
        self.ensure_one()
        if self.tax_type != 'islr':
            raise UserError("Este reporte no es de retenciones de ISLR")
        self.company_id._with_locked_records(self)

        buffer = BytesIO()
        workbook = xlsxwriter.Workbook(buffer, {"in_memory": True})
        merge_format = workbook.add_format(
            {"bold": 1, "border": 1, "align": "center", "valign": "vcenter", "fg_color": "gray"}
        )
        company_vat = self.company_vat
        range_month = self.period

        name = "Retenciones de ISLR"
        worksheet = workbook.add_worksheet(name)
        worksheet.set_column("A:Z", 20)
        worksheet.merge_range("A1:F1", name, merge_format)
        worksheet.write("G1", "Rif Agente:")
        worksheet.write("H1", company_vat)
        worksheet.write("G2", "Periodo")
        worksheet.write("H2", range_month)
        # worksheet.merge_range("A2:B2", "Ruta de descarga:", merge_format)
        # worksheet.write("C2", "C:/Users/Public/")

        columns = [
            {"header": r}
            for r in [
                "ID Sec",
                "RIF Retenido",
                "Número factura",
                "Control Número",
                "Fecha Operación",
                "Código Concepto",
                "Monto Operación",
                "Porcentaje de retención",
            ]
        ]
        rows = [
            [  # "ID Sec",
                idx + 1,
                # "RIF Retenido",
                line.partner_vat,
                # "Número factura",
                line.doc_number,
                # "Control Número",
                line.doc_control_number,
                # "Fecha Operación",
                line.withholding_date.strftime("%d/%m/%Y"),
                # "Código Concepto",
                line.concept_code,
                # "Monto Operación",
                line.document_amount_untaxed,
                # "Porcentaje de retención",
                line.withholding_percentage,
            ]
            for idx, line in enumerate(self.line_ids)
            # for line in self.line_ids
        ]

        worksheet.write("I1", len(rows))
        currency_format = workbook.add_format({"num_format": "#,###0.00"})
        date_format = workbook.add_format()
        date_format.set_num_format("d-mmm-yy")  # Format string.
        col3 = len(columns) - 1
        col2 = len(rows) + 4
        for record in columns[6:8]:
            record.update({"format": currency_format})
        cells = xlsxwriter.utility.xl_range(3, 0, col2, col3)
        worksheet.add_table(cells, {"data": rows, "total_row": False, "columns": columns})
        # # macro
        # url = os.path.dirname(os.path.abspath(__file__))

        # workbook.add_vba_project(url + "/vbaProject.bin")
        # worksheet.insert_button(
        #     "I2", {"macro": "MakeXML", "caption": "Generar XML", "width": 120, "height": 30}
        # )

        workbook.close()
        return buffer.getvalue()

    def _make_islr_xml_report(self):
        self.ensure_one()
        if self.tax_type != 'islr':
            raise UserError("Este reporte no es de retenciones de ISLR")

        self.company_id._with_locked_records(self)

        root = et.Element("RelacionRetencionesISLR", {
            "RifAgente": self.company_vat,
            "Periodo": self.period,
        })
        for line in self.line_ids:
            detalle = et.SubElement(root, "DetalleRetencion")
            rif = et.SubElement(detalle, "RifRetenido")
            rif.text = line.partner_vat

            doc_num = et.SubElement(detalle, "NumeroFactura")
            doc_num.text = line.doc_number

            doc_corr = et.SubElement(detalle, "NumeroControl")
            doc_corr.text = line.doc_control_number

            fecha = et.SubElement(detalle, "FechaOperacion")
            fecha.text = line.withholding_date.strftime("%d/%m/%Y")

            concepto = et.SubElement(detalle, "CodigoConcepto")
            concepto.text = str(line.concept_code).rjust(3, "0")

            monto = et.SubElement(detalle, "MontoOperacion")
            monto.text = "{0:.2f}".format(line.document_amount_untaxed)

            porc = et.SubElement(detalle, "PorcentajeRetencion")
            porc.text = "{0:.0f}".format(line.withholding_percentage)

        et.indent(root)

        return et.tostring(root, encoding='iso8859-1', xml_declaration=True)
    
    def _make_iva_xlsx_report(self):
        self.ensure_one()
        if self.tax_type != 'iva':
            raise UserError("Este reporte no es de retenciones de IVA")
        self.company_id._with_locked_records(self)

        buffer = BytesIO()
        workbook = xlsxwriter.Workbook(buffer, {"in_memory": True})
        merge_format = workbook.add_format(
            {"bold": 1, "border": 1, "align": "center", "valign": "vcenter", "fg_color": "gray"}
        )
        company_vat = self.company_vat
        range_month = self.period

        name = "Retenciones de IVA"
        worksheet = workbook.add_worksheet(name)
        worksheet.set_column("A:Z", 20)
        worksheet.merge_range("A1:F1", name, merge_format)
        worksheet.write("G1", "Rif Agente:")
        worksheet.write("H1", company_vat)
        worksheet.write("G2", "Periodo")
        worksheet.write("H2", range_month)
        # worksheet.merge_range("A2:B2", "Ruta de descarga:", merge_format)
        # worksheet.write("C2", "C:/Users/Public/")

        def get_doc_type(line):
            if line.document_id.l10n_ve_doc_type_internal_type == 'invoice':
                return '01'
            elif line.document_id.l10n_ve_doc_type_internal_type == 'debit_note':
                return '02'
            elif line.document_id.l10n_ve_doc_type_internal_type == 'credit_note':
                return '03'
            else:
                raise ValueError(_("Tipo de documento no reconocido %s", line.document_id.l10n_ve_doc_type_internal_type))

        columns = [
            {"header": r}
            for r in [
                "ID Sec",
                "RIF Retenido",
                "Fecha Operación",
                "Nro documento",
                "Nro control",
                "Tipo documento",
                "Doc. Afectado",
                "Total",
                "Base",
                "Exento",
                "Alícuota",
                "IVA",
                "Nro Retención",
                "% Retenido",
                "Retenido",
            ]
        ]
        rows = [
            [  # "ID Sec",
                idx + 1,
                # "RIF Retenido",
                line.partner_vat,
                # "Fecha Operación",
                line.withholding_date.strftime("%d/%m/%Y"),
                # Nro documento
                line.doc_number,
                # Nro control
                line.document_control_number,
                # Tipo documento
                get_doc_type(line),
                # Doc. Afectado
                line.document_id.affected_invoice_number if line.document_id.affected_invoice_number else "",
                # Total
                line.document_amount_total,
                # Base
                line.document_amount_untaxed,
                # Exento
                line._get_iva_exempt_amount(),
                # Alícuota
                line.withholding_aliquot,
                # IVA
                line.document_tax_amount,
                # Nro Retención
                line.withholding_number,
                # % Retenido
                line.withholding_percentage,
                # Retenido
                line.withholding_amount,
            ]
            for idx, line in enumerate(self.line_ids)
            # for line in self.line_ids
        ]

        worksheet.write("I1", len(rows))
        currency_format = workbook.add_format({"num_format": "#,###0.00"})
        date_format = workbook.add_format()
        date_format.set_num_format("d-mmm-yy")  # Format string.
        col3 = len(columns) - 1
        col2 = len(rows) + 4
        for i in [7,8,9,10,11,13,14]:
            record = columns[i]
            record.update({"format": currency_format})
        cells = xlsxwriter.utility.xl_range(3, 0, col2, col3)
        worksheet.add_table(cells, {"data": rows, "total_row": False, "columns": columns})
        # # macro
        # url = os.path.dirname(os.path.abspath(__file__))

        # workbook.add_vba_project(url + "/vbaProject.bin")
        # worksheet.insert_button(
        #     "I2", {"macro": "MakeXML", "caption": "Generar XML", "width": 120, "height": 30}
        # )

        workbook.close()
        return buffer.getvalue()

    def _make_iva_txt_report(self):
        self.ensure_one()
        if self.tax_type != 'iva':
            raise UserError("Este reporte no es de retenciones de IVA")

        self.company_id._with_locked_records(self)
        buffer = StringIO()
        writer = csv.writer(buffer, delimiter="\t", quoting=csv.QUOTE_NONE)

        self.line_ids.fetch([
            'document_id', 
        ])

        def get_doc_type(line):
            if line.document_id.l10n_ve_doc_type_internal_type == 'invoice':
                return '01'
            elif line.document_id.l10n_ve_doc_type_internal_type == 'debit_note':
                return '02'
            elif line.document_id.l10n_ve_doc_type_internal_type == 'credit_note':
                return '03'
            else:
                raise ValueError(_("Tipo de documento no reconocido %s", line.document_id.l10n_ve_doc_type_internal_type))
            
        amount_fmt = "{:.2f}"
        writer.writerows((
            [
                # RIF del agente de retención
                self.company_vat,
                # Período impositivo
                self.period,
                # Fecha de factura
                line.document_id.invoice_date.strftime("%Y-%m-%d"),
                # Tipo de operación
                "C",
                # Tipo de documento
                get_doc_type(line),
                # RIF de proveedor
                line.partner_vat,
                # Número de documento
                line.doc_number,
                # Número de control
                line.document_control_number,
                # Monto total del documento
                amount_fmt.format(line.document_amount_total),
                # Base imponible
                amount_fmt.format(line.document_amount_untaxed),
                # Monto del Iva Retenido
                amount_fmt.format(line.withholding_amount),
                # Número del documento afectado
                line.document_id.affected_invoice_number if line.document_id.affected_invoice_number else "0",
                # Número de comprobante de retención
                line.withholding_number,
                # Monto exento del IVA
                amount_fmt.format(line._get_iva_exempt_amount()),
                # Alícuota
                amount_fmt.format(line.withholding_aliquot),
                # Número de Expediente
                "0",
            ]
            for line in self.line_ids
        ))
        buffer.flush()
        buffer.seek(0)

        return buffer.read()


class AccountWithholdingReportLine(models.TransientModel):
    _name = "account.withholding.report.line"
    _description = "Línea de reporte de retenciones"
    _order = "withholding_date asc"
    _check_company_auto = True
    _rec_name = 'document_number'

    report_id = fields.Many2one("account.withholding.report", "Reporte")
    withholding_id = fields.Many2one("account.retention", "Retención")
    withholding_line_id = fields.Many2one("account.retention.line", "Retención línea")
    tax_type = fields.Selection(related="report_id.tax_type")
    company_currency_id = fields.Many2one(related="report_id.company_currency_id")

    # Document
    document_id = fields.Many2one("account.move", "Documento", related="withholding_line_id.move_id", store=True, readonly=True)
    document_type = fields.Selection(related="document_id.l10n_ve_doc_type_internal_type", store=True, readonly=True)
    document_amount_total = fields.Float("Total", help="Total", related="withholding_line_id.invoice_total", store=True, readonly=True)
    document_amount_untaxed = fields.Float("Base", help="Base imponible", related="withholding_line_id.invoice_amount", store=True, readonly=True)
    document_tax_amount = fields.Float("IVA", help="Monto de IVA", related="withholding_line_id.iva_amount", store=True, readonly=True)
    # Contribuyente
    partner_id = fields.Many2one("res.partner", "Contribuyente", related="document_id.partner_id", store=True, readonly=True)
    partner_vat = fields.Char("RIF/CI", related="document_id.partner_id.l10n_ve_vat", store=True, readonly=True)
    # Withholding
    concept_code = fields.Char("Código concepto", related="withholding_line_id.code", store=True, readonly=True)
    withholding_number = fields.Char("Nro. comp.", related="withholding_id.number", store=True, readonly=True)
    withholding_date = fields.Date("Fecha", related="withholding_id.date_accounting", store=True, readonly=True)
    withholding_aliquot = fields.Float("Alícuota", related="withholding_line_id.aliquot",  store=True, readonly=True, 
                                       help="Alícuota del IVA retenida")
    withholding_aliquot_f = fields.Float("Alícuota F", compute="_compute_withholding_aliquot_f")
    withholding_percentage = fields.Float("% Ret.", compute="_compute_withholding_percentage", store=True, readonly=True)
    withholding_amount_subtract = fields.Float("Sustraendo", related="withholding_line_id.related_amount_subtract_fees", store=True, readonly=True)
    withholding_amount = fields.Float("Retenido", related="withholding_line_id.retention_amount", store=True, readonly=True)

    # visual only
    document_number = fields.Char("Nro. documento", related="document_id.l10n_latam_document_number")
    document_control_number = fields.Char("Nro. control", related="document_id.correlative")
    partner_vat_is_valid = fields.Boolean(compute="_compute_partner_vat_is_valid")

    # technical fields
    doc_number = fields.Char(size=10, store=True, compute="_compute_document_number")
    doc_control_number = fields.Char(size=10, store=True, compute="_compute_document_number")

    @api.depends('document_id.l10n_latam_document_number', 'document_id.correlative')
    def _compute_document_number(self):
        for rec in self:
            if not rec.document_id:
                rec.doc_number = ""
                rec.doc_control_number = ""
                continue

            doc_number = str(rec.document_id.l10n_latam_document_number).replace('-', '')
            if len(doc_number) > 10:
                doc_number = doc_number[-10:]
            doc_control_number = str(rec.document_id.correlative).replace('-', '')
            if len(doc_control_number) > 10:
                doc_control_number = doc_control_number[-10:]
            rec.doc_number = doc_number
            rec.doc_control_number = doc_control_number

    @api.depends('tax_type', 'withholding_line_id.related_percentage_fees', 'withholding_line_id.aliquot')
    def _compute_withholding_percentage(self):
        for rec in self:
            if not rec.tax_type:
                continue

            if rec.tax_type == 'islr':
                rec.withholding_percentage = rec.withholding_line_id.related_percentage_fees
            elif rec.tax_type == 'iva': 
                rec.withholding_percentage = rec.withholding_line_id.related_percentage_tax_base
            else:
                raise UserError(_("No se reconoce el tipo de retención [%s]", rec.tax_type)) 
            
    @api.depends('withholding_aliquot')
    def _compute_withholding_aliquot_f(self):
        for rec in self:
            rec.withholding_aliquot_f = rec.withholding_aliquot * 0.01

    @api.depends("partner_vat")
    def _compute_partner_vat_is_valid(self):
        for rec in self:
            rec.partner_vat_is_valid = rec.partner_vat and len(rec.partner_vat) == 10

    def _get_iva_exempt_amount(self):
        self.ensure_one()
        return sum(
            self.document_id.invoice_line_ids.filtered(lambda l: l.tax_ids.amount == 0).mapped(
                "price_subtotal"
            )
        )

        
