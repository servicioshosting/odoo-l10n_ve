from datetime import date, datetime

from odoo import http


class DownloadWithholdingReport(http.Controller):
    @http.route("/web/seniat/download_withholding_report", type="http", auth="user", methods=['get'])
    def download_withholding_report(self, id):
        withholdings_report = http.request.env["account.withholding.report"].browse([int(id)])

        if not withholdings_report:
            return http.request.make_response("", 400)

        company_vat = withholdings_report.company_id.partner_id.l10n_ve_vat

        file = None
        filename = None
        content_type = None

        if withholdings_report.download_format == 'excel':
            if withholdings_report.tax_type == 'islr':
                file = withholdings_report._make_islr_xlsx_report()
                filename = f"Reporte_Retenciones_ISLR_{company_vat}_{withholdings_report.period}.xlsx"
            elif withholdings_report.tax_type == 'iva':
                file = withholdings_report._make_iva_xlsx_report()
                filename = f"Reporte_Retenciones_IVA_{company_vat}_{withholdings_report.period}.xlsx"
            content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        else:
            if withholdings_report.tax_type == 'islr':
                file = withholdings_report._make_islr_xml_report()
                filename = f"XML_RelacionRetencionesISLR_{withholdings_report.period}.xml"
                content_type = "text/xml"
            elif withholdings_report.tax_type == 'iva':
                file = withholdings_report._make_iva_txt_report()
                filename = f"TXT_RelacionRetencionesIVA_{withholdings_report.period}.txt"
                content_type = "text/csv"

        return http.request.make_response(
            file,
            headers=[
                ("Content-Type", content_type),
                ("Content-Length", len(file)),
                ("Content-Disposition", f"attachment; filename={filename};"),
            ],
        )
