/** @odoo-module **/

import { formatMonetary } from "@web/views/fields/formatters";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { registry } from "@web/core/registry";
import { TaxTotalsComponent } from "@account/components/tax_totals/tax_totals";
import { toRaw, onWillRender } from "@odoo/owl";

/**
 * Foreign-currency tax totals widget (Odoo 18).
 *
 * Reads extras injected by l10n_ve_accountant.account.tax._get_tax_totals_summary
 * (foreign_* keys) and renders them with the company foreign currency.
 */
export class TaxTotalsComponents extends TaxTotalsComponent {
    setup() {
        super.setup();
        onWillRender(() => this.formatForeignData(this.props));
    }

    get foreignCurrencyId() {
        const fc = this.props.record.data.foreign_currency_id;
        return fc && fc[0];
    }

    formatForeignMonetary(value) {
        return formatMonetary(value, { currencyId: this.foreignCurrencyId });
    }

    formatForeignData(props) {
        let totals = JSON.parse(
            JSON.stringify(toRaw(props.record.data[this.props.name] || null))
        );
        if (!totals) {
            this.totals = totals;
            return;
        }
        // Ensure foreign_subtotals is always a list for the template.
        if (!Array.isArray(totals.foreign_subtotals)) {
            totals.foreign_subtotals = [];
        }
        this.totals = totals;
    }

    formatData(props) {
        super.formatData(props);
        this.formatForeignData(props);
    }
}

TaxTotalsComponents.template = "l10n_ve_accountant.TaxForeignTotalsField";
TaxTotalsComponents.props = {
    ...standardFieldProps,
};

export const taxTotalsComponent = {
    component: TaxTotalsComponents,
};

const fieldsRegistry = registry.category("fields");
if (!fieldsRegistry.contains("account-tax-foreign-totals-field")) {
    fieldsRegistry.add("account-tax-foreign-totals-field", taxTotalsComponent);
}
