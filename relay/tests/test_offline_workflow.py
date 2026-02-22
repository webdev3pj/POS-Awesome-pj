import unittest

from relay.app import create_app


class OfflineWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.client = self.app.test_client()

    def _open_session(self, cashier_user_id, device_id="DEVICE-A"):
        resp = self.client.post(
            "/relay/session/open",
            json={
                "pos_profile_id": "POS-MAIN",
                "cashier_user_id": cashier_user_id,
                "device_id": device_id,
            },
        )
        self.assertEqual(resp.status_code, 200)
        payload = resp.get_json() or {}
        self.assertTrue(payload.get("ok"))
        return payload["session"]["session_id"]

    def _create_token(self, token_id="TKN001"):
        resp = self.client.post(
            "/relay/token/create",
            json={
                "token_id": token_id,
                "pos_profile_id": "POS-MAIN",
                "cashier_user_id": "sa@example.com",
                "customer_id": "CUST-001",
                "customer_name": "Customer One",
                "items": [
                    {
                        "item_code": "ITEM-001",
                        "item_name": "Item One",
                        "qty": 2,
                        "uom": "Nos",
                        "rate": 10,
                        "amount": 20,
                    }
                ],
            },
        )
        self.assertEqual(resp.status_code, 200)
        payload = resp.get_json() or {}
        self.assertTrue(payload.get("ok"))
        return payload["token"]["token_id"]

    def _commit(self, token_id, idem, cashier_user_id, session_id, device_id="DEVICE-A"):
        return self.client.post(
            "/relay/commit-invoice",
            json={
                "token_id": token_id,
                "idempotency_key": idem,
                "pos_profile_id": "POS-MAIN",
                "cashier_user_id": cashier_user_id,
                "cashier_session_id": session_id,
                "device_id": device_id,
                "invoice": {
                    "name": f"DRAFT-{idem}",
                    "customer": "CUST-001",
                    "customer_name": "Customer One",
                    "net_total": 20,
                    "grand_total": 20,
                    "items": [
                        {
                            "item_code": "ITEM-001",
                            "item_name": "Item One",
                            "qty": 2,
                            "uom": "Nos",
                            "rate": 10,
                            "amount": 20,
                        }
                    ],
                },
                "data": {"paid_change": 0, "credit_change": 0},
            },
        )

    def test_acceptance_1_multi_stage_flow(self):
        session_id = self._open_session("cashier1@example.com", "DEVICE-B")
        token_id = self._create_token("TKN-A1")

        commit_resp = self._commit(token_id, "IDEMP-A1", "cashier1@example.com", session_id, "DEVICE-B")
        self.assertEqual(commit_resp.status_code, 200)
        commit_payload = commit_resp.get_json() or {}
        self.assertTrue(commit_payload.get("ok"))
        local_sale_ref = commit_payload.get("local_sale_ref")
        self.assertTrue(local_sale_ref)

        queue_resp = self.client.get("/relay/pick-queue")
        self.assertEqual(queue_resp.status_code, 200)
        queue_payload = queue_resp.get_json() or {}
        self.assertGreaterEqual(queue_payload.get("count", 0), 1)

        pick_resp = self.client.post(
            "/relay/pick/update",
            json={
                "local_sale_ref": local_sale_ref,
                "picking_status": "PICKED_READY_FOR_RELEASE",
                "picker_user_id": "picker1@example.com",
            },
        )
        self.assertEqual(pick_resp.status_code, 200)
        self.assertTrue((pick_resp.get_json() or {}).get("ok"))

        release_resp = self.client.post(
            "/relay/dispatch/release",
            json={
                "local_sale_ref": local_sale_ref,
                "dispatcher_user_id": "gate1@example.com",
            },
        )
        self.assertEqual(release_resp.status_code, 200)
        release_payload = release_resp.get_json() or {}
        self.assertTrue(release_payload.get("ok"))
        self.assertEqual(release_payload.get("dispatch_status"), "RELEASED")

    def test_acceptance_2_multi_cashier_same_profile(self):
        s1 = self._open_session("cashier-a@example.com", "DEVICE-1")
        s2 = self._open_session("cashier-b@example.com", "DEVICE-2")
        self.assertNotEqual(s1, s2)

        t1 = self._create_token("TKN-B1")
        t2 = self._create_token("TKN-B2")

        r1 = self._commit(t1, "IDEMP-B1", "cashier-a@example.com", s1, "DEVICE-1")
        r2 = self._commit(t2, "IDEMP-B2", "cashier-b@example.com", s2, "DEVICE-2")
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r2.status_code, 200)

        q = self.client.get("/relay/pick-queue")
        payload = q.get_json() or {}
        refs = {row.get("local_sale_ref") for row in payload.get("rows") or []}
        self.assertIn((r1.get_json() or {}).get("local_sale_ref"), refs)
        self.assertIn((r2.get_json() or {}).get("local_sale_ref"), refs)

    def test_acceptance_3_double_pay_prevention(self):
        s1 = self._open_session("cashier-1@example.com", "DEVICE-X")
        s2 = self._open_session("cashier-2@example.com", "DEVICE-Y")
        token_id = self._create_token("TKN-C1")

        first = self._commit(token_id, "IDEMP-C1", "cashier-1@example.com", s1, "DEVICE-X")
        self.assertEqual(first.status_code, 200)

        second = self._commit(token_id, "IDEMP-C2", "cashier-2@example.com", s2, "DEVICE-Y")
        self.assertEqual(second.status_code, 409)
        payload = second.get_json() or {}
        self.assertEqual(payload.get("code"), "TOKEN_ALREADY_PAID")

    def test_acceptance_4_idempotency_replay(self):
        session_id = self._open_session("cashier-replay@example.com", "DEVICE-R")
        token_id = self._create_token("TKN-D1")

        idem = "IDEMP-D1"
        first = self._commit(token_id, idem, "cashier-replay@example.com", session_id, "DEVICE-R")
        self.assertEqual(first.status_code, 200)
        first_payload = first.get_json() or {}

        second = self._commit(token_id, idem, "cashier-replay@example.com", session_id, "DEVICE-R")
        self.assertEqual(second.status_code, 200)
        second_payload = second.get_json() or {}

        self.assertTrue(second_payload.get("idempotent_replay"))
        self.assertEqual(first_payload.get("local_sale_ref"), second_payload.get("local_sale_ref"))

    def test_acceptance_5_outbox_sync_queue_presence(self):
        session_id = self._open_session("cashier-sync@example.com", "DEVICE-S")
        token_id = self._create_token("TKN-E1")
        commit = self._commit(token_id, "IDEMP-E1", "cashier-sync@example.com", session_id, "DEVICE-S")
        self.assertEqual(commit.status_code, 200)

        outbox = self.client.get("/api/outbox")
        self.assertEqual(outbox.status_code, 200)
        payload = outbox.get_json() or {}
        rows = payload.get("rows") or []
        self.assertTrue(any((row.get("event_type") == "SALE_COMMITTED") for row in rows))


if __name__ == "__main__":
    unittest.main()

