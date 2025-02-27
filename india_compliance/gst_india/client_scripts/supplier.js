{% include "india_compliance/gst_india/client_scripts/party.js" %}

const DOCTYPE = "Supplier";

validate_pan(DOCTYPE);
validate_gstin(DOCTYPE);
update_gstin_in_other_documents(DOCTYPE);
show_overseas_disabled_warning(DOCTYPE);

frappe.ui.form.on(DOCTYPE, {
    gstin(frm) {
        if (!frm.doc.is_transporter || !frm.doc.gstin || frm.doc.gstin.length < 15) return;
        frm.set_value("gst_transporter_id", frm.doc.gstin);
    }
})
