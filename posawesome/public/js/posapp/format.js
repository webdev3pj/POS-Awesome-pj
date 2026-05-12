export default {
    data () {
        return {
            float_precision: 2,
            currency_precision: 2
        };
    },
    methods: {
        flt (value, precision, number_format, rounding_method) {
            if (!precision && precision != 0) {
                precision = this.currency_precision || 2;
            }
            if (!rounding_method) {
                rounding_method = "Banker's Rounding (legacy)";
            }
            return flt(value, precision, number_format, rounding_method);
        },
        normalizeFixedPrecisionNumber(value, precision = 2, no_negative = false, fallback = 0) {
            const safePrecision = Number.isInteger(precision) && precision >= 0 ? precision : 2;
            let numeric = parseFloat(value);
            if (isNaN(numeric)) {
                numeric = fallback == null ? 0 : fallback;
            }
            if (no_negative && numeric < 0) {
                numeric = numeric * -1;
            }
            const factor = Math.pow(10, safePrecision);
            const rounded =
                Math.round((Number(numeric) + Number.EPSILON) * factor) / factor;
            return Number(rounded.toFixed(safePrecision));
        },
        formtCurrency (value, precision) {
            const format = get_number_format(this.pos_profile?.currency);
            value = format_number(
                value,
                format,
                precision || this.currency_precision || 2
            );
            return value;
        },
        formtFloat (value, precision) {
            const format = get_number_format(this.pos_profile.currency);
            value = format_number(value, format, precision || this.float_precision || 2);
            return value;
        },
        setFormatedCurrency (el, field_name, precision, no_negative = false, $event) {
            let value = 0;
            try {
                const normalized = this.normalizeFixedPrecisionNumber(
                    $event,
                    precision == null ? this.currency_precision || 2 : precision,
                    no_negative
                );
                value = this.formtCurrency(
                    normalized,
                    precision == null ? this.currency_precision || 2 : precision
                );
            } catch (e) {
                console.error(e);
                value = 0;
            }
            // check if el is an object
            if (typeof el === "object") {
                el[field_name] = value;
            }
            else {
                this[field_name] = value;
            }


            return value;
        },
        setFormatedFloat (el, field_name, precision, no_negative = false, $event) {
            let value = 0;
            try {
                const normalized = this.normalizeFixedPrecisionNumber(
                    $event,
                    precision == null ? this.float_precision || 2 : precision,
                    no_negative
                );
                value = this.formtFloat(
                    normalized,
                    precision == null ? this.float_precision || 2 : precision
                );
            } catch (e) {
                console.error(e);
                value = 0;
            }
            // check if el is an object
            if (typeof el === "object") {
                el[field_name] = value;
            }
            else {
                this[field_name] = value;
            }
            return value;
        },
        currencySymbol (currency) {
            return get_currency_symbol(currency);
        },
        isNumber (value) {
            const pattern = /^-?(\d+|\d{1,3}(\.\d{3})*)(,\d+)?$/;
            return pattern.test(value) || "invalid number";

        }
    },
    mounted () {
        this.float_precision =
            frappe.defaults.get_default('float_precision') || 2;
        this.currency_precision =
            frappe.defaults.get_default('currency_precision') || 2;
    }
};
