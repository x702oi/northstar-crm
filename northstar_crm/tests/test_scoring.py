from types import SimpleNamespace
from unittest.mock import patch

from frappe.tests import UnitTestCase

from northstar_crm.services.scoring import calculate_lead_score, classify_lead_score


class TestLeadScoring(UnitTestCase):
    def test_score_is_transparent_and_bounded(self):
        lead = SimpleNamespace(
            status="Qualified",
            estimated_value=300000,
            decision_authority="Decision Maker",
            business_need="Replace fragmented customer systems",
            target_close_date="2026-12-31",
            engagement_score=10,
            last_activity_on=None,
        )

        score, factors = calculate_lead_score(lead)

        self.assertEqual(score, 87)
        self.assertEqual(score, sum(factors.values()))
        self.assertEqual(factors["budget"], 20)

    @patch("northstar_crm.services.scoring.frappe.db.get_single_value")
    def test_rating_uses_configured_thresholds(self, get_single_value):
        get_single_value.side_effect = lambda _doctype, field: {
            "warm_lead_score": 35,
            "hot_lead_score": 75,
        }[field]

        self.assertEqual(classify_lead_score(20), "Cold")
        self.assertEqual(classify_lead_score(50), "Warm")
        self.assertEqual(classify_lead_score(80), "Hot")
