// Simplified Invoice Page
// Minimal invoice creation UI for micro-enterprise shop owners
// Exposes only: party, items, amount, GST rate, payment mode

frappe.pages['simplified-invoice'].on_page_load = function (wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: __('New Sale (Simplified)'),
        single_column: true
    });

    // Build the simplified form
    let $form = $(`
        <div class="simplified-invoice-container">
            <div class="simplified-invoice-form">
                <!-- Header -->
                <div class="form-header">
                    <h3>Create a New Sale</h3>
                    <p class="text-muted">Only essential fields — the system handles the rest automatically.</p>
                </div>

                <!-- Customer Section -->
                <div class="form-section">
                    <label class="section-label">Customer Details</label>
                    <div class="row">
                        <div class="col-sm-8">
                            <div class="frappe-control" data-fieldname="customer">
                                <label class="control-label">Customer Name *</label>
                                <div class="control-input-wrapper">
                                    <select class="form-control customer-select" id="customer_select">
                                        <option value="">Select a customer...</option>
                                    </select>
                                </div>
                            </div>
                        </div>
                        <div class="col-sm-4">
                            <div class="frappe-control" data-fieldname="gstin">
                                <label class="control-label">GSTIN</label>
                                <div class="control-input-wrapper">
                                    <input type="text" class="form-control" id="customer_gstin" readonly placeholder="Auto-filled">
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Items Section -->
                <div class="form-section">
                    <label class="section-label">Items</label>
                    <div class="items-table-wrapper">
                        <table class="table table-bordered items-table" id="items_table">
                            <thead>
                                <tr>
                                    <th style="width: 35%">Item</th>
                                    <th style="width: 10%">Qty</th>
                                    <th style="width: 15%">Rate (₹)</th>
                                    <th style="width: 10%">GST %</th>
                                    <th style="width: 15%">Amount (₹)</th>
                                    <th style="width: 5%"></th>
                                </tr>
                            </thead>
                            <tbody id="items_body">
                                <tr class="item-row">
                                    <td>
                                        <select class="form-control item-select" id="item_select_0">
                                            <option value="">Select item...</option>
                                        </select>
                                    </td>
                                    <td><input type="number" class="form-control item-qty" value="1" min="1"></td>
                                    <td><input type="number" class="form-control item-rate" value="0" min="0" step="0.01"></td>
                                    <td>
                                        <select class="form-control item-gst">
                                            <option value="">Auto</option>
                                            <option value="0">0%</option>
                                            <option value="5">5%</option>
                                            <option value="12">12%</option>
                                            <option value="18">18%</option>
                                            <option value="28">28%</option>
                                        </select>
                                    </td>
                                    <td><span class="item-amount">₹0.00</span></td>
                                    <td><button class="btn btn-danger btn-xs remove-item" disabled>×</button></td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                    <button class="btn btn-default btn-xs add-item-btn">
                        + Add Another Item
                    </button>
                </div>

                <!-- Totals -->
                <div class="form-section totals-section">
                    <div class="row">
                        <div class="col-sm-6">
                            <div class="frappe-control">
                                <label class="control-label">Payment Mode *</label>
                                <div class="control-input-wrapper">
                                    <select class="form-control" id="payment_mode">
                                        <option value="Cash">Cash</option>
                                        <option value="Bank">Bank Transfer</option>
                                        <option value="UPI" selected>UPI</option>
                                        <option value="Credit">Credit (On Account)</option>
                                    </select>
                                </div>
                            </div>
                        </div>
                        <div class="col-sm-6 text-right">
                            <div class="totals-display">
                                <div class="total-row">
                                    <span class="total-label">Net Total:</span>
                                    <span class="total-value" id="net_total">₹0.00</span>
                                </div>
                                <div class="total-row">
                                    <span class="total-label">GST:</span>
                                    <span class="total-value" id="gst_total">₹0.00</span>
                                </div>
                                <div class="total-row grand-total">
                                    <span class="total-label">Grand Total:</span>
                                    <span class="total-value" id="grand_total">₹0.00</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Action Buttons -->
                <div class="form-section actions-section text-right">
                    <button class="btn btn-default" id="reset_btn">Reset</button>
                    <button class="btn btn-primary" id="submit_btn">
                        <span class="submit-text">Create Invoice & Submit</span>
                        <span class="submit-spinner" style="display:none;">
                            <i class="fa fa-spinner fa-spin"></i> Submitting...
                        </span>
                    </button>
                </div>

                <!-- Result Display -->
                <div class="form-section result-section" style="display:none;">
                    <div class="alert alert-success" id="success_message"></div>
                </div>
            </div>
        </div>
    `);

    $(wrapper).find('.page-content').append($form);

    // Load customers and items into dropdowns
    load_customers();
    load_items();
    setup_event_handlers(page);
};

function load_customers() {
    frappe.call({
        method: 'frappe.client.get_list',
        args: {
            doctype: 'Customer',
            fields: ['name', 'customer_name', 'gstin'],
            limit_page_length: 100,
            order_by: 'name asc'
        },
        callback: function (r) {
            if (r.message) {
                let $select = $('#customer_select');
                r.message.forEach(function (c) {
                    let label = c.customer_name || c.name;
                    if (c.gstin) label += ' (' + c.gstin + ')';
                    $select.append(`<option value="${c.name}">${label}</option>`);
                });
            }
        }
    });
}

function load_items() {
    frappe.call({
        method: 'frappe.client.get_list',
        args: {
            doctype: 'Item',
            fields: ['name', 'item_name', 'gst_hsn_code', 'gst_rate'],
            filters: { 'disabled': 0, 'has_variants': 0 },
            limit_page_length: 200,
            order_by: 'name asc'
        },
        callback: function (r) {
            if (r.message) {
                $('.item-select').each(function () {
                    let $select = $(this);
                    r.message.forEach(function (item) {
                        let label = item.item_name || item.name;
                        if (item.gst_hsn_code) label += ' [HSN: ' + item.gst_hsn_code + ']';
                        $select.append(`<option value="${item.name}" 
                            data-rate="${item.gst_rate || ''}" 
                            data-hsn="${item.gst_hsn_code || ''}">${label}</option>`);
                    });
                });
            }
        }
    });
}

function setup_event_handlers(page) {
    // Customer selection → auto-fill GSTIN
    $(document).on('change', '#customer_select', function () {
        let customer = $(this).val();
        if (customer) {
            frappe.call({
                method: 'frappe.client.get',
                args: {
                    doctype: 'Customer',
                    name: customer
                },
                callback: function (r) {
                    if (r.message) {
                        $('#customer_gstin').val(r.message.gstin || 'Not registered');
                    }
                }
            });
        } else {
            $('#customer_gstin').val('');
        }
    });

    // Add item row
    $(document).on('click', '.add-item-btn', function () {
        let $tbody = $('#items_body');
        let rowCount = $tbody.find('.item-row').length;
        let $newRow = $tbody.find('.item-row:first').clone();
        
        $newRow.find('input, select').each(function () {
            let oldId = $(this).attr('id');
            if (oldId) {
                $(this).attr('id', oldId.replace(/\d+$/, rowCount));
            }
            if ($(this).is('input')) {
                if ($(this).hasClass('item-qty')) $(this).val(1);
                else if ($(this).hasClass('item-rate')) $(this).val(0);
            } else if ($(this).is('select')) {
                $(this).val('');
            }
        });
        $newRow.find('.item-amount').text('₹0.00');
        $newRow.find('.remove-item').prop('disabled', false);
        
        $tbody.append($newRow);
        
        // Load items into the new select
        load_items_into_select($newRow.find('.item-select'));
    });

    // Remove item row
    $(document).on('click', '.remove-item', function () {
        let $rows = $('#items_body').find('.item-row');
        if ($rows.length > 1) {
            $(this).closest('.item-row').remove();
            calculate_totals();
        }
    });

    // Item selection → auto-fill rate and GST
    $(document).on('change', '.item-select', function () {
        let $row = $(this).closest('.item-row');
        let $selected = $(this).find('option:selected');
        let rate = $selected.data('rate');
        let hsn = $selected.data('hsn');
        
        if (rate) {
            $row.find('.item-gst').val(rate);
        }
        calculate_totals();
    });

    // Recalculate on qty/rate/gst change
    $(document).on('input', '.item-qty, .item-rate', calculate_totals);
    $(document).on('change', '.item-gst', calculate_totals);

    // Reset button
    $(document).on('click', '#reset_btn', function () {
        reset_form();
    });

    // Submit button
    $(document).on('click', '#submit_btn', function () {
        submit_invoice(page);
    });
}

function load_items_into_select($select) {
    frappe.call({
        method: 'frappe.client.get_list',
        args: {
            doctype: 'Item',
            fields: ['name', 'item_name', 'gst_hsn_code', 'gst_rate'],
            filters: { 'disabled': 0, 'has_variants': 0 },
            limit_page_length: 200
        },
        callback: function (r) {
            if (r.message) {
                $select.empty().append('<option value="">Select item...</option>');
                r.message.forEach(function (item) {
                    let label = item.item_name || item.name;
                    if (item.gst_hsn_code) label += ' [HSN: ' + item.gst_hsn_code + ']';
                    $select.append(`<option value="${item.name}"
                        data-rate="${item.gst_rate || ''}"
                        data-hsn="${item.gst_hsn_code || ''}">${label}</option>`);
                });
            }
        }
    });
}

function calculate_totals() {
    let netTotal = 0;
    let gstTotal = 0;

    $('.item-row').each(function () {
        let qty = parseFloat($(this).find('.item-qty').val()) || 0;
        let rate = parseFloat($(this).find('.item-rate').val()) || 0;
        let gstPct = parseFloat($(this).find('.item-gst').val()) || 0;
        let amount = qty * rate;
        let gst = amount * gstPct / 100;

        netTotal += amount;
        gstTotal += gst;
        $(this).find('.item-amount').text('₹' + amount.toFixed(2));
    });

    let grandTotal = netTotal + gstTotal;

    $('#net_total').text('₹' + netTotal.toFixed(2));
    $('#gst_total').text('₹' + gstTotal.toFixed(2));
    $('#grand_total').text('₹' + grandTotal.toFixed(2));
}

function reset_form() {
    $('#customer_select').val('');
    $('#customer_gstin').val('');
    $('#items_body').empty();
    
    // Add one empty row
    let $row = $(`
        <tr class="item-row">
            <td>
                <select class="form-control item-select">
                    <option value="">Select item...</option>
                </select>
            </td>
            <td><input type="number" class="form-control item-qty" value="1" min="1"></td>
            <td><input type="number" class="form-control item-rate" value="0" min="0" step="0.01"></td>
            <td>
                <select class="form-control item-gst">
                    <option value="">Auto</option>
                    <option value="0">0%</option>
                    <option value="5">5%</option>
                    <option value="12">12%</option>
                    <option value="18">18%</option>
                    <option value="28">28%</option>
                </select>
            </td>
            <td><span class="item-amount">₹0.00</span></td>
            <td><button class="btn btn-danger btn-xs remove-item" disabled>×</button></td>
        </tr>
    `);
    $('#items_body').append($row);
    load_items_into_select($row.find('.item-select'));
    
    $('#payment_mode').val('UPI');
    calculate_totals();
    $('.result-section').hide();
    $('.submit-text').show();
    $('.submit-spinner').hide();
    $('#submit_btn').prop('disabled', false);
}

function submit_invoice(page) {
    let customer = $('#customer_select').val();
    if (!customer) {
        frappe.msgprint({ title: __('Error'), message: __('Please select a customer.'), indicator: 'red' });
        return;
    }

    let items = [];
    let hasItems = false;
    $('.item-row').each(function () {
        let itemCode = $(this).find('.item-select').val();
        let qty = parseFloat($(this).find('.item-qty').val()) || 1;
        let rate = parseFloat($(this).find('.item-rate').val()) || 0;
        let gst = $(this).find('.item-gst').val();
        
        if (itemCode && rate > 0) {
            hasItems = true;
            items.push({
                item_code: itemCode,
                qty: qty,
                rate: rate,
                gst_rate: gst || null
            });
        }
    });

    if (!hasItems) {
        frappe.msgprint({ title: __('Error'), message: __('Please add at least one item with a rate.'), indicator: 'red' });
        return;
    }

    let paymentMode = $('#payment_mode').val();

    // Show loading
    $('.submit-text').hide();
    $('.submit-spinner').show();
    $('#submit_btn').prop('disabled', true);

    frappe.call({
        method: "micro_gst_assist.api.create_simple_invoice",
        args: {
            party: customer,
            items: items,
            payment_mode: paymentMode
        },
        callback: function (r) {
            $('.submit-spinner').hide();
            $('.submit-text').show();
            $('#submit_btn').prop('disabled', false);

            if (r.message) {
                let invoiceName = r.message;
                $('.result-section').show();
                $('#success_message').html(`
                    <strong>✓ Invoice Created Successfully!</strong><br>
                    Invoice <a href="/app/sales-invoice/${invoiceName}" target="_blank">${invoiceName}</a>
                    has been created and ${paymentMode === 'Credit' ? 'saved as draft' : 'submitted'}.
                `);
                
                // Auto-reset after 3 seconds
                setTimeout(reset_form, 3000);
            }
        },
        error: function (err) {
            $('.submit-spinner').hide();
            $('.submit-text').show();
            $('#submit_btn').prop('disabled', false);
            
            frappe.msgprint({
                title: __('Error'),
                message: err.message || __('Failed to create invoice. Please check your data and try again.'),
                indicator: 'red'
            });
        }
    });
}
