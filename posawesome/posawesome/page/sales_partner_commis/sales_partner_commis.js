frappe.pages['sales-partner-commis'].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Sales Partner Commission',
		single_column: true
	});

	$(page.body).addClass("page-layout-main-section");

	// ✅ Check if user has Sales Commission Admin role
	const is_admin = frappe.user_roles.includes("Sales Commission Admin");

	// Add filters
	const filters = [
		{
			fieldname: "sales_partner",
			label: __("Sales Partner"),
			fieldtype: "Link",
			options: "Sales Partner",
			reqd: is_admin ? 0 : 1,   // required only if NOT admin
		},
		{
			fieldname: "payment_status",
			label: __("Payment Status"),
			fieldtype: "Select",
			options: ["Pending", "Paid"],
			default: "Pending"
		}
	];

	const filter_group = $('<div class="row"></div>').appendTo(page.body);
	filters.forEach((filter) => {
		const field_wrapper = $('<div class="col-md-3"></div>').appendTo(filter_group);
		const field = frappe.ui.form.make_control({
			df: filter,
			parent: field_wrapper,
			render_input: true
		});
		field.refresh();
		page[filter.fieldname] = field;
	});

	// Set default value for Payment Status manually
	setTimeout(() => {
		if (page.payment_status) {
			page.payment_status.set_value("Pending");
		}
	}, 100);

	// Buttons
	const button_group = $(`
		<div class="form-group row mt-4">
			<div class="col-sm-12 text-right">
				<button class="btn btn-outline-danger border border-danger clear-btn btn-md px-5 mr-2" id="clear_btn_spc">Clear</button>
				<button class="btn btn-primary search-btn btn-md px-5 mr-2" id="search_btn_spc">Search</button>
				<button class="btn btn-outline-success btn-md px-5" id="export_btn_spc">
					<i class="fa fa-file-excel-o mr-2"></i> Export
				</button>
			</div>
		</div>
	`).appendTo(page.body);

	// Result container
	const result_container = $('<div class="result-container-spc mt-4"></div>').appendTo(page.body);

	let all_commission_data = [];

	// Load commission data
	function load_commission_data(sales_partner = "", payment_status = "Pending") {
		result_container.empty().html('Loading...');
		frappe.call({
			method: "posawesome.posawesome.page.sales_partner_commis.sales_partner_commis.get_commission_data",
			args: {
				sales_partner: sales_partner,
				payment_status: payment_status
			},
			callback: function (r) {
				if (r.message && r.message.length > 0) {
					all_commission_data = r.message.map(row => ({
						...row,
						commission: typeof row.commission === "object" ? row.commission.parsedValue || row.commission.source : row.commission
					}));

					result_container.empty();

					// Build table header dynamically
					let headerHTML = `
						<tr>
							<th>Sr No.</th>
							<th>
								<input type="checkbox" id="select_all_rows_spc" title="Select All" />
								<label for="select_all_rows_spc" class="ml-1">Select</label>
							</th>
							<th>Sales Partner</th>
							<th>Commission</th>
							<th>Mode of Payment</th>
							<th>Reference Sales Invoice</th>
					`;

					if (payment_status === "Paid") {
						headerHTML += `
							<th>BPO Name</th>
							<th>BPO Date/Time</th>
						`;
					}

					headerHTML += `</tr>`;

					const table = $(`
						<table class="table table-bordered">
							<thead class="thead-light">
								${headerHTML}
							</thead>
							<tbody></tbody>
						</table>
					`).appendTo(result_container);

					const tbody = table.find("tbody");

					all_commission_data.forEach((row, index) => {
						const sr_no = index + 1;
						let trHTML = `
							<td>${sr_no}</td>
							<td><input type="checkbox" class="select-row" data-index="${index}"></td>
							<td>${row.sales_partner || ''}</td>
							<td>${row.commission || ''}</td>
							<td>${row.mode_of_payment || ''}</td>
							<td>${row.reference_sales_invoice || ''}</td>
						`;

						if (payment_status === "Paid") {
							trHTML += `
								<td>${row.bpo_name || ''}</td>
								<td>${row.bpo_datetime || ''}</td>
							`;
						}

						tbody.append(`<tr>${trHTML}</tr>`);
					});

					// Handle "Select All"
					$('#select_all_rows_spc').on('change', function () {
						const checked = $(this).is(':checked');
						$('.select-row').prop('checked', checked);
					});

					result_container.on('change', '.select-row', function () {
						const total = $('.select-row').length;
						const checked = $('.select-row:checked').length;
						$('#select_all_rows_spc').prop('checked', total === checked);
					});

					if (payment_status === "Pending") {
						const bulkButtonRow = $(`
							<div class="text-right mt-3">
								<button class="btn btn-success" id="bulk_payout_btn_spc">
									<i class="fa fa-money-bill-wave mr-2"></i> Bulk Payout
								</button>
							</div>
						`);
						result_container.append(bulkButtonRow);

						$('#bulk_payout_btn_spc').on('click', function () {
							const selectedIndexes = $('.select-row:checked').map(function () {
								return $(this).data('index');
							}).get();

							if (selectedIndexes.length === 0) {
								frappe.msgprint(__('Please select at least one record to proceed with bulk payout.'));
								return;
							}

							const selectedData = selectedIndexes.map(index => all_commission_data[index]);
							window.selected_commission_rows = selectedData;

							frappe.confirm(
								__('Are you sure you want to create a Bulk Payout for the selected records?'),
								function () {
									frappe.call({
										method: "posawesome.posawesome.page.sales_partner_commis.sales_partner_commis.create_bulk_payout",
										args: {
											data: selectedData
										},
										callback: function (r) {
											if (r.message) {
												const docname = r.message;
												const link = frappe.utils.get_form_link('Sales Partner Commission Bulk Pay Out', docname);
												frappe.msgprint({
													title: __('Bulk Payout Created'),
													indicator: 'green',
													message: __('Sales Partner Commission Bulk Pay Out created: {0}', [link])
												});
											}
										}
									});
								},
								function () {
									frappe.msgprint(__('Bulk Payout creation was cancelled.'));
								}
							);
						});
					}
				} else {
					result_container.html(`<h5 class="text-muted text-center mt-3">No Data Found</h5>`);
				}
			}
		});
	}
	// Search button
	$('#search_btn_spc').on('click', function () {
		const sales_partner = page.sales_partner.get_value();
		const payment_status = page.payment_status.get_value();

		// ✅ Only enforce required if NOT admin
		if (!is_admin && !sales_partner) {
			frappe.msgprint({
				title: __('Missing Required Field'),
				message: __('Please select a Sales Partner to search.'),
				indicator: 'red'
			});
			return;
		}

		load_commission_data(sales_partner, payment_status);
	});

	// Clear button
	$('#clear_btn_spc').on('click', function () {
		result_container.empty();
		all_commission_data = [];
		window.selected_commission_rows = [];
		page.sales_partner.set_value('');
		page.payment_status.set_value("Pending");
	});

	// ✅ Export button (Excel via SheetJS)
	$('#export_btn_spc').on('click', function () {
		if (!all_commission_data.length) {
			frappe.msgprint(__('No data available to export. Please search first.'));
			return;
		}

		// Dynamically prepare rows
		const payment_status = page.payment_status.get_value();
		let headers = ["Sales Partner", "Commission", "Mode of Payment", "Reference Sales Invoice"];
		if (payment_status === "Paid") {
			headers.push("BPO Name", "BPO Date/Time");
		}

		const rows = all_commission_data.map((row, index) => {
			const baseRow = [
				row.sales_partner || "",
				row.commission || "",
				row.mode_of_payment || "",
				row.reference_sales_invoice || ""
			];
			if (payment_status === "Paid") {
				baseRow.push(row.bpo_name || "", row.bpo_datetime || "");
			}
			return baseRow;
		});

		// Build worksheet
		const worksheet_data = [headers, ...rows];
		const ws = XLSX.utils.aoa_to_sheet(worksheet_data);

		// Build workbook
		const wb = XLSX.utils.book_new();
		XLSX.utils.book_append_sheet(wb, ws, "Commission Data");

		// Export to file
		const filename = `Sales_partner_commission_export_${payment_status}.xlsx`;
		XLSX.writeFile(wb, filename);
	});

	// Style override
	$(`<style>
		input[data-fieldname="sales_partner"],
		select[data-fieldname="payment_status"] {
			border: 1px solid #ccc !important;
			background-color: #fff !important;
			color: #000 !important;
			box-shadow: none !important;
			font-weight: 500 !important;
			border-radius: 6px;
			padding: 8px 12px;
			font-size: 14px;
		}

		input[data-fieldname="sales_partner"]::placeholder {
			color: #999 !important;
			opacity: 1 !important;
		}

		.table td, .table th {
			padding: 6px 8px !important;
			font-size: 13px;
			vertical-align: middle;
		}
	</style>`).appendTo("head");

	// ✅ Load SheetJS dynamically (if not already loaded)
	if (typeof XLSX === "undefined") {
		const script = document.createElement("script");
		script.src = "https://cdnjs.cloudflare.com/ajax/libs/xlsx/0.18.5/xlsx.full.min.js";
		document.head.appendChild(script);
	}
};
