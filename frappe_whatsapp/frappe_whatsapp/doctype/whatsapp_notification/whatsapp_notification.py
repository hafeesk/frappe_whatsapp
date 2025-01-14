"""Notification."""

import json
import frappe
from frappe.model.document import Document
from frappe.utils.safe_exec import get_safe_globals
from frappe.integrations.utils import make_post_request


class WhatsAppNotification(Document):
    """Notification."""
    def validate(self):

        if not any(field.fieldname == self.field_name for field in frappe.get_doc("DocType", self.reference_doctype).fields): # noqa
            frappe.throw(f"Field name {self.field_name} does not exists")


    def execute_doc(self, doc: Document):
        """Specific to Document Event triggered Server Scripts."""
        if self.disabled:
            return

        doc_data = doc.as_dict()
        if self.condition:
            # check if condition satisfies
            if not frappe.safe_eval(
                self.condition, get_safe_globals(), dict(doc=doc_data)
            ):
                return

        settings = frappe.get_doc(
            "WhatsApp Settings", "WhatsApp Settings",
        )
        token = settings.get_password("token")

        headers = {
            "authorization": f"Bearer {token}",
            "content-type": "application/json"
        }

        language_code = frappe.db.get_value(
            "WhatsApp Templates", self.template,
            fieldname='language_code'
        )

        if language_code:
            data = {
                "messaging_product": "whatsapp",
                "to": doc_data[self.field_name],
                "type": "template",
                "template": {
                    "name": self.template,
                    "language": {
                        "code": language_code
                    },
                    "components":[]
                }
            }

            # Pass parameter values
            if self.fields:
                parameters = []
                for field in self.fields:
                    parameters.append(
                    {
                        "type": "text",
                        "text": doc_data[field.field_name]
                    })

                data['template']["components"] = [{
                    "type": "body",
                    "parameters": parameters
                }]

            response = make_post_request(
                f"{settings.url}/{settings.version}/{settings.phone_id}/messages",
                headers=headers, data=json.dumps(data)
            )

            frappe.get_doc({
                "doctype": "WhatsApp Notification Log",
                "template": self.template,
                "meta_data": response
            }).insert(ignore_permissions=True)
