// GST Filing Assistant Workspace - Custom JS
// Adds micro-interactions and real-time updates for the shop owner

frappe.workspace.on("after_render", function (workspace) {
    if (workspace.name !== "GST Filing Assistant") return;
    
    // Update the "Days to Deadline" card with real-time calculation
    update_deadline_counter(workspace);
    
    // Auto-refresh readiness score every 60 seconds
    setInterval(function () {
        update_deadline_counter(workspace);
    }, 60000);
});

function update_deadline_counter(workspace) {
    frappe.call({
        method: "frappe.client.get_list",
        args: {
            doctype: "GST Filing Checklist",
            fields: ["due_date", "status", "name"],
            filters: {
                status: ["!=", "Completed"]
            },
            limit_page_length: 1,
            order_by: "due_date asc"
        },
        callback: function (r) {
            if (r.message && r.message.length > 0) {
                let dueDate = frappe.datetime.str_to_obj(r.message[0].due_date);
                let today = frappe.datetime.get_today();
                let daysLeft = frappe.datetime.get_diff(dueDate, today);
                
                // Find and update the deadline number card
                let $deadlineCard = workspace.$wrapper.find('.number-card:contains("Days to Filing Deadline")');
                if ($deadlineCard.length > 0) {
                    let displayText = daysLeft >= 0 ? daysLeft + " days" : "OVERDUE";
                    $deadlineCard.find('.number-card-value').text(displayText);
                    
                    // Color coding
                    if (daysLeft < 0) {
                        $deadlineCard.css('border-left', '4px solid #e74c3c');
                    } else if (daysLeft <= 3) {
                        $deadlineCard.css('border-left', '4px solid #f39c12');
                    } else {
                        $deadlineCard.css('border-left', '4px solid #27ae60');
                    }
                }
            }
        }
    });
}
