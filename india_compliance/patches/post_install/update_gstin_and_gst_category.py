import click

import frappe


def execute():
    update_pan_for_company()
    update_na_gstin()
    update_gstin_and_gst_category()


def update_pan_for_company():
    # Updated pan_details with pan for consisitency in company
    if not frappe.db.has_column("Company", "pan_details"):
        return

    company = frappe.qb.DocType("Company")
    frappe.qb.update(company).set(company.pan, company.pan_details).where(
        company.pan_details.notin(("", None))
    ).run()


def update_na_gstin():
    for doctype in ("Address", "Customer", "Supplier"):
        frappe.db.set_value(doctype, {"gstin": "NA"}, "gstin", "")


def update_gstin_and_gst_category():
    """
    Bulk Update GST Category for Overseas in Address.
    Set GSTIN in Party where the GSTIN is same across all Addresses.
    Set GST Category in Address.
    """

    # bulk update GST Category for Overseas
    frappe.db.set_value(
        "Address",
        {
            "gst_category": ("in", ("", None, "Unregistered")),
            "country": ("!=", "India"),
        },
        "gst_category",
        "Overseas",
    )

    # get all Addresses with linked party
    all_addresses = frappe.get_all(
        "Address",
        fields=(
            "name",
            "gstin",
            "gst_category",
            "`tabDynamic Link`.link_doctype",
            "`tabDynamic Link`.link_name",
        ),
        filters={
            "link_doctype": ("!=", ""),
            "link_name": ("!=", ""),
        },
    )

    # party-wise addresses
    address_map = {}
    for address in all_addresses:
        address_map.setdefault((address.link_doctype, address.link_name), []).append(
            address
        )

    new_gstins = {}
    new_gst_categories = {}
    print_warning = False

    for doctype in ("Customer", "Supplier", "Company"):
        for party in frappe.get_all(doctype, fields=("name", "gstin", "gst_category")):
            address_list = address_map.get((doctype, party.name))
            if not address_list:
                continue

            # in case user has custom gstin field in party
            default_gstin = party.gstin

            if not default_gstin and (
                gstins := {address.gstin for address in address_list}
            ):
                # update gstin in party only where there is one gstin per party
                if len(gstins) == 1:
                    default_gstin = next(iter(gstins))
                    new_gstins.setdefault((doctype, default_gstin), []).append(
                        party.name
                    )
                else:
                    print_warning = True

            for address in address_list:
                # User may have already set GST category in Address
                if address.gst_category != "Unregistered":
                    continue

                # update GST Category in Address from party
                gst_category = party.gst_category

                # GST category may be incorrect, set to empty
                if address.gstin and address.gstin != default_gstin:
                    gst_category = ""
                    print_warning = True

                new_gst_categories.setdefault((doctype, gst_category), []).append(
                    party.name
                )

    for (doctype, gstin), docnames in new_gstins.items():
        frappe.db.set_value(doctype, {"name": ("in", docnames)}, "gstin", gstin)

    for (doctype, gst_category), docnames in new_gst_categories.items():
        frappe.db.set_value(
            doctype, {"name": ("in", docnames)}, "gst_category", gst_category
        )

    if print_warning:
        click.secho(
            "We have identified multiple GSTINs for a few parties and couldn't set"
            " newly created fields automatically for these. Please check for parties"
            " without GSTINs or addresses without GST Category and set approporiate"
            " values.\n",
            fg="yellow",
        )
