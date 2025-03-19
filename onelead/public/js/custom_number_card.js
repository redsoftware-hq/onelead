frappe.require("/assets/frappe/js/frappe/widgets/number_card_widget.js", function () {
    class CustomNumberCardWidget extends NumberCardWidget {
        render_stats() {
            if (this.card_doc.type !== "Document Type" || !this.card_doc.show_percentage_stats) {
                return;
            }

            let caret_html = "";
            let color_class = "";

            return this.get_percentage_stats().then(() => {
                if (!this.percentage_stat || isNaN(this.percentage_stat)) {
                    return;
                }

                let is_error_or_unconfigured = ["Today's Error Leads", "Today's Unconfigured Leads"].includes(this.card_doc.label);

                if (this.percentage_stat > 0) {
                    caret_html = `<span class="indicator-pill-round ${is_error_or_unconfigured ? 'red' : 'green'}">
                            ${frappe.utils.icon("arrow-up-right", "xs")}
                        </span>`;
                    color_class = is_error_or_unconfigured ? "red-stat" : "green-stat";
                } else {
                    caret_html = `<span class="indicator-pill-round ${is_error_or_unconfigured ? 'green' : 'red'}">
                            ${frappe.utils.icon("arrow-down-right", "xs")}
                        </span>`;
                    color_class = is_error_or_unconfigured ? "green-stat" : "red-stat";
                }

                const stats_qualifier_map = {
                    Daily: __("since yesterday"),
                    Weekly: __("since last week"),
                    Monthly: __("since last month"),
                    Yearly: __("since last year"),
                };
                const stats_qualifier = stats_qualifier_map[this.card_doc.stats_time_interval];

                let stat = (() => {
                    const parts = this.percentage_stat.split(" ");
                    const symbol = parts[1] || "";
                    return Math.abs(parts[0]) + " " + symbol;
                })();

                if (isNaN(stat)) return;

                $(this.body).find(".widget-content").append(`<div class="card-stats ${color_class}">
                    <span class="percentage-stat-area">
                        ${caret_html} ${stat} % ${stats_qualifier}
                    </span>
                </div>`);
            });
        }
    }

    // Ensure frappe.widgets exists before registering
    frappe.widgets = frappe.widgets || {};
    frappe.widgets.CustomNumberCardWidget = CustomNumberCardWidget;
});
