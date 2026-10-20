from odoo import api, models
from odoo.tools.misc import formatLang

import logging

_logger = logging.getLogger(__name__)


class AccountTax(models.Model):
    _inherit = "account.tax"

    @api.model
    def _get_tax_totals_summary(self, base_lines, currency, company, cash_rounding=None):
        """Extend Odoo 18 tax totals with foreign-currency + discount extras.

        Replaces the Odoo 17 ``_prepare_tax_totals`` override. Return shape follows
        ``_get_tax_totals_summary`` (base_amount_currency, subtotals[].tax_groups, …)
        plus Servitepuy keys used by the foreign tax-totals widget / PDF reports.
        """
        res = super()._get_tax_totals_summary(
            base_lines, currency, company, cash_rounding=cash_rounding
        )
        # Legacy 17 key aliases used by reports / detailed_amounts.
        res["amount_untaxed"] = res.get("base_amount_currency", 0.0)
        res["amount_total"] = res.get("total_amount_currency", 0.0)
        res["formatted_amount_untaxed"] = formatLang(
            self.env, res["amount_untaxed"], currency_obj=currency
        )
        res["formatted_amount_total"] = formatLang(
            self.env, res["amount_total"], currency_obj=currency
        )

        foreign_currency = company.currency_foreign_id
        if not foreign_currency:
            # Soft: company not fully configured yet (chart install, etc.)
            return res

        has_discount = any(
            not currency.is_zero(line.get("discount") or 0.0) for line in base_lines
        )
        res_without_discount = res
        if has_discount:
            base_without_discount = self._l10n_ve_clone_base_lines(
                base_lines, force_discount=0.0
            )
            self._add_tax_details_in_base_lines(base_without_discount, company)
            self._round_base_lines_tax_details(base_without_discount, company)
            res_without_discount = super()._get_tax_totals_summary(
                base_without_discount, currency, company, cash_rounding=cash_rounding
            )

        foreign_base_lines = self._l10n_ve_prepare_foreign_base_lines(
            base_lines, foreign_currency
        )
        self._add_tax_details_in_base_lines(foreign_base_lines, company)
        self._round_base_lines_tax_details(foreign_base_lines, company)
        foreign_taxes = super()._get_tax_totals_summary(
            foreign_base_lines, foreign_currency, company, cash_rounding=cash_rounding
        )

        foreign_taxes_without_discount = foreign_taxes
        if has_discount:
            foreign_without_discount = self._l10n_ve_prepare_foreign_base_lines(
                base_lines, foreign_currency, force_discount=0.0
            )
            self._add_tax_details_in_base_lines(foreign_without_discount, company)
            self._round_base_lines_tax_details(foreign_without_discount, company)
            foreign_taxes_without_discount = super()._get_tax_totals_summary(
                foreign_without_discount,
                foreign_currency,
                company,
                cash_rounding=cash_rounding,
            )

        # --- Foreign extras (widget + reports) ---
        res["foreign_subtotals"] = foreign_taxes.get("subtotals", [])
        res["foreign_amount_untaxed"] = foreign_taxes.get("base_amount_currency", 0.0)
        res["foreign_amount_total"] = foreign_taxes.get("total_amount_currency", 0.0)
        res["foreign_formatted_amount_untaxed"] = formatLang(
            self.env, res["foreign_amount_untaxed"], currency_obj=foreign_currency
        )
        res["foreign_formatted_amount_total"] = formatLang(
            self.env, res["foreign_amount_total"], currency_obj=foreign_currency
        )

        res["show_discount"] = company.show_discount_on_moves

        res["subtotal"] = res_without_discount.get("base_amount_currency", 0.0)
        res["formatted_subtotal"] = formatLang(
            self.env, res["subtotal"], currency_obj=currency
        )
        res["foreign_subtotal"] = foreign_taxes_without_discount.get(
            "base_amount_currency", 0.0
        )
        res["foreign_formatted_subtotal"] = formatLang(
            self.env, res["foreign_subtotal"], currency_obj=foreign_currency
        )

        res["discount_amount"] = res.get("base_amount_currency", 0.0) - res["subtotal"]
        res["formatted_discount_amount"] = formatLang(
            self.env, res["discount_amount"], currency_obj=currency
        )
        res["foreign_discount_amount"] = (
            foreign_taxes.get("base_amount_currency", 0.0)
            - foreign_taxes_without_discount.get("base_amount_currency", 0.0)
        )
        res["foreign_formatted_discount_amount"] = formatLang(
            self.env, res["foreign_discount_amount"], currency_obj=foreign_currency
        )

        # Odoo 17 report aliases (free-form / legacy QWeb)
        self._l10n_ve_enrich_subtotals_legacy(res.get("subtotals") or [], currency)
        self._l10n_ve_enrich_subtotals_legacy(
            res.get("foreign_subtotals") or [], foreign_currency
        )
        res["groups_by_subtotal"] = self._l10n_ve_groups_by_subtotal(
            res.get("subtotals") or []
        )
        res["groups_by_foreign_subtotal"] = self._l10n_ve_groups_by_subtotal(
            res.get("foreign_subtotals") or []
        )
        res["display_tax_base"] = not res.get("same_tax_base", True)
        return res

    @api.model
    def _l10n_ve_enrich_subtotals_legacy(self, subtotals, currency):
        """Add formatted_amount / tax_group_* aliases expected by VE QWeb reports."""
        for subtotal in subtotals:
            amount = subtotal.get("base_amount_currency", 0.0)
            subtotal["formatted_amount"] = formatLang(
                self.env, amount, currency_obj=currency
            )
            for group in subtotal.get("tax_groups") or []:
                group.setdefault("tax_group_name", group.get("group_name"))
                # Odoo 17 used tax_group_id; Odoo 18 tax_groups expose `id`.
                group.setdefault("tax_group_id", group.get("id"))
                tax_amt = group.get("tax_amount_currency", 0.0)
                base_amt = group.get("base_amount_currency", 0.0)
                group["tax_group_amount"] = tax_amt
                group["tax_group_base_amount"] = base_amt
                group["formatted_tax_group_amount"] = formatLang(
                    self.env, tax_amt, currency_obj=currency
                )
                group["formatted_tax_group_base_amount"] = formatLang(
                    self.env, base_amt, currency_obj=currency
                )

    @api.model
    def _l10n_ve_groups_by_subtotal(self, subtotals):
        """Rebuild Odoo 17 groups_by_subtotal mapping from 18 subtotals."""
        result = {}
        for subtotal in subtotals:
            result[subtotal.get("name")] = list(subtotal.get("tax_groups") or [])
        return result

    @api.model
    def _l10n_ve_clone_base_lines(self, base_lines, force_discount=None):
        """Shallow-clone base lines and strip prior tax details for recompute."""
        cloned = []
        for line in base_lines:
            new_line = {k: v for k, v in line.items() if not k.startswith("tax_details")}
            new_line = dict(new_line)
            if force_discount is not None:
                new_line["discount"] = force_discount
            # drop cached tax computation blobs if present
            for key in (
                "tax_details",
                "raw_total_excluded_currency",
                "raw_total_excluded",
            ):
                new_line.pop(key, None)
            # Odoo 18 indexes these keys directly (KeyError if missing).
            new_line.setdefault("manual_tax_amounts", None)
            new_line.setdefault("manual_total_excluded_currency", None)
            new_line.setdefault("manual_total_excluded", None)
            new_line.setdefault("filter_tax_function", None)
            new_line.setdefault("special_mode", False)
            cloned.append(new_line)
        return cloned

    @api.model
    def _l10n_ve_prepare_foreign_base_lines(
        self, base_lines, foreign_currency, force_discount=None
    ):
        """Rebuild base lines priced in the company foreign currency."""
        foreign_base_lines = self._l10n_ve_clone_base_lines(
            base_lines, force_discount=force_discount
        )
        for base_line in foreign_base_lines:
            record = base_line.get("record")
            base_line["currency_id"] = foreign_currency
            base_line["rate"] = 1.0
            if record is not None and not isinstance(record, dict):
                if "foreign_price" in record._fields:
                    base_line["price_unit"] = record.foreign_price
                # quantity / taxes already on the base line
            # Keep keys present (do not pop): core does base_line['manual_tax_amounts'].
            # Clear values so VEF manual amounts are not reused on the foreign recompute.
            base_line["manual_tax_amounts"] = None
            base_line["manual_total_excluded_currency"] = None
            base_line["manual_total_excluded"] = None
        return foreign_base_lines
