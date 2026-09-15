import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, nowdate


class TestCRMFlow(IntegrationTestCase):
    def setUp(self):
        super().setUp()
        self.stage = self._stage()
        self.organization = frappe.get_doc(
            {
                "doctype": "CRM Organization",
                "organization_name": f"_Test Northstar {frappe.generate_hash(length=8)}",
                "account_manager": frappe.session.user,
                "lifecycle_stage": "Prospect",
                "currency": "SAR",
            }
        ).insert(ignore_permissions=True)

    def _stage(self):
        name = frappe.db.get_value("CRM Pipeline Stage", {"stage_name": "_Test Discovery"}, "name")
        if name:
            return frappe.get_doc("CRM Pipeline Stage", name)
        return frappe.get_doc(
            {
                "doctype": "CRM Pipeline Stage",
                "stage_name": "_Test Discovery",
                "sequence": 35,
                "probability": 40,
                "color": "#5FE0C1",
            }
        ).insert(ignore_permissions=True)

    def _opportunity(self):
        return frappe.get_doc(
            {
                "doctype": "CRM Opportunity",
                "opportunity_name": "_Test CRM Opportunity",
                "organization": self.organization.name,
                "pipeline_stage": self.stage.name,
                "currency": "SAR",
                "amount": 100000,
                "expected_close_date": add_days(nowdate(), 30),
                "opportunity_owner": frappe.session.user,
                "status": "Open",
            }
        ).insert(ignore_permissions=True)

    def test_opportunity_derives_forecast_and_stage_history(self):
        opportunity = self._opportunity()

        self.assertEqual(opportunity.probability, 40)
        self.assertEqual(opportunity.weighted_amount, 40000)
        self.assertTrue(
            frappe.db.exists(
                "CRM Stage History",
                {"opportunity": opportunity.name, "to_stage": self.stage.name},
            )
        )

    def test_discounted_quote_enters_approval_gate(self):
        opportunity = self._opportunity()
        quote = frappe.get_doc(
            {
                "doctype": "CRM Quote",
                "quote_title": "_Test Commercial Proposal",
                "opportunity": opportunity.name,
                "organization": self.organization.name,
                "valid_until": add_days(nowdate(), 14),
                "currency": "SAR",
                "items": [
                    {
                        "service_name": "CRM implementation",
                        "quantity": 1,
                        "rate": 100000,
                        "discount_percent": 15,
                    }
                ],
            }
        ).insert(ignore_permissions=True)

        self.assertEqual(quote.approval_status, "Pending")
        self.assertEqual(quote.grand_total, 97750)
        self.assertTrue(quote.approval_signature)
