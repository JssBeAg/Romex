from notifications.models import Notification

from .base import ApiTestCase, today


class InventoryTest(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.unit = self.make_unit("I-1")

    def preventive(self, parts, **over):
        data = {
            "service_type_id": 1, "unit_id": self.unit["id"], "service_mileage": "1200", "total_cost": "50",
            "date": today(), "operator_ids": [], "spare_parts": parts,
        }
        data.update(over)
        return self.m.post_json("/api/mantenimientos/", data)

    def stock(self, part_id):
        return self.g.get_json(f"/api/refacciones/{part_id}/").json()["spare_part"]["stock"]

    def test_initial_stock_and_validations(self):
        part = self.make_part("Filtro A", stock=5, min_stock=3)
        self.assertEqual(part["stock"], 5)
        self.assertFalse(part["low_stock"])
        r = self.g.post_json("/api/refacciones/", {"name": "filtro a"})
        self.assertEqual(r.status_code, 400)  # duplicated name, ignoring case
        r = self.g.post_json("/api/refacciones/", {"name": "", "unit_price": "-1", "min_stock": "x"})
        self.assertEqual(r.status_code, 400)

    def test_maintenance_discounts_and_deleting_it_returns_the_pieces(self):
        part = self.make_part("Filtro B", stock=10)
        r = self.preventive([{"id": part["id"], "quantity": 4}])
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(self.stock(part["id"]), 6)
        mid = r.json()["maintenance"]["id"]
        self.assertEqual(self.m.delete(f"/api/mantenimientos/{mid}/").status_code, 200)
        self.assertEqual(self.stock(part["id"]), 10)

    def test_cannot_use_more_than_there_is(self):
        part = self.make_part("Filtro C", stock=2)
        self.assertEqual(self.preventive([{"id": part["id"], "quantity": 3}]).status_code, 400)
        self.assertEqual(self.stock(part["id"]), 2)
        none = self.make_part("Sin existencias")
        self.assertEqual(self.preventive([{"id": none["id"], "quantity": 1}]).status_code, 400)

    def test_bad_part_lists_are_refused(self):
        part = self.make_part("Filtro D", stock=9)
        dup = [{"id": part["id"], "quantity": 1}, {"id": part["id"], "quantity": 1}]
        self.assertEqual(self.preventive(dup).status_code, 400)
        self.assertEqual(self.preventive([{"id": part["id"], "quantity": 0}]).status_code, 400)
        self.assertEqual(self.preventive("x").status_code, 400)

    def test_low_stock_rule_and_notification(self):
        part = self.make_part("Balata", stock=6, min_stock=5)
        with self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(self.preventive([{"id": part["id"], "quantity": 2}]).status_code, 201)
        detail = self.g.get_json(f"/api/refacciones/{part['id']}/").json()["spare_part"]
        self.assertTrue(detail["low_stock"])
        self.assertTrue(Notification.objects.filter(user=self.manager, kind=Notification.LOW_STOCK).exists())
        low = self.g.get_json("/api/refacciones/", low=1).json()
        self.assertIn("Balata", [p["name"] for p in low["spare_parts"]])

    def test_minimum_zero_never_warns(self):
        part = self.make_part("Tornillo", stock=1, min_stock=0)
        self.preventive([{"id": part["id"], "quantity": 1}])
        self.assertFalse(self.g.get_json(f"/api/refacciones/{part['id']}/").json()["spare_part"]["low_stock"])

    def test_movements_entry_and_adjustment(self):
        part = self.make_part("Aceite", stock=3)
        url = f"/api/refacciones/{part['id']}/movimientos/"
        r = self.g.post_json(url, {"movement_type": "entrada", "quantity": 7, "date": today()})
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(self.stock(part["id"]), 10)
        # An adjustment needs a note and cannot take off more than there is
        self.assertEqual(self.g.post_json(url, {"movement_type": "ajuste", "quantity": -2, "date": today()}).status_code, 400)
        ok = self.g.post_json(url, {"movement_type": "ajuste", "quantity": -4, "date": today(), "note": "Conteo"})
        self.assertEqual(ok.status_code, 201, ok.content)
        self.assertEqual(self.stock(part["id"]), 6)
        too_much = self.g.post_json(url, {"movement_type": "ajuste", "quantity": -50, "date": today(), "note": "x"})
        self.assertEqual(too_much.status_code, 400)

    def test_part_in_use_cannot_be_deleted_but_can_be_deactivated(self):
        part = self.make_part("Usada", stock=3)
        self.preventive([{"id": part["id"], "quantity": 1}])
        self.assertEqual(self.g.delete(f"/api/refacciones/{part['id']}/").status_code, 409)
        self.g.put_json(f"/api/refacciones/{part['id']}/", {"name": "Usada", "unit_price": "10", "min_stock": 0, "is_active": False})
        r = self.preventive([{"id": part["id"], "quantity": 1}])
        self.assertEqual(r.status_code, 400)

    def test_unused_part_can_be_deleted(self):
        part = self.make_part("Nunca usada")
        self.assertEqual(self.g.delete(f"/api/refacciones/{part['id']}/").status_code, 200)

    def test_kardex_pdf(self):
        r = self.g.get_json(f"/api/kardex/{self.unit['id']}/", format="pdf")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.content.startswith(b"%PDF"))
