from audit.models import AuditLog

from .base import ApiTestCase


class ListingTest(ApiTestCase):
    """Pagination, sorting, search and PDF, shown on the spare parts list (30 parts come with the app)."""

    URL = "/api/refacciones/"

    def test_pagination_defaults(self):
        data = self.g.get_json(self.URL).json()
        pg = data["pagination"]
        self.assertEqual(pg["page"], 1)
        self.assertEqual(pg["page_size"], 20)
        self.assertEqual(len(data["spare_parts"]), 20)
        self.assertGreaterEqual(pg["total"], 30)
        self.assertEqual(pg["pages"], -(-pg["total"] // 20))

    def test_second_page_has_the_rest(self):
        total = self.g.get_json(self.URL).json()["pagination"]["total"]
        data = self.g.get_json(self.URL, page=2).json()
        self.assertEqual(len(data["spare_parts"]), total - 20)

    def test_page_out_of_range_returns_last(self):
        data = self.g.get_json(self.URL, page=999).json()
        self.assertEqual(data["pagination"]["page"], data["pagination"]["pages"])

    def test_page_size_is_capped(self):
        data = self.g.get_json(self.URL, page_size=5000).json()
        self.assertEqual(data["pagination"]["page_size"], 100)
        data = self.g.get_json(self.URL, page_size=5).json()
        self.assertEqual(len(data["spare_parts"]), 5)

    def test_bad_page_values_do_not_fail(self):
        r = self.g.get_json(self.URL, page="x", page_size="y")
        self.assertEqual(r.status_code, 200)

    def test_sort_ascending_and_descending(self):
        # Plain ASCII names, so the result does not depend on the database collation
        for name in ("Ccc zorro", "Aaa zorro", "Bbb zorro"):
            self.make_part(name)
        asc = [p["name"] for p in self.g.get_json(self.URL, q="zorro", order="name").json()["spare_parts"]]
        desc = [p["name"] for p in self.g.get_json(self.URL, q="zorro", order="-name").json()["spare_parts"]]
        self.assertEqual(asc, ["Aaa zorro", "Bbb zorro", "Ccc zorro"])
        self.assertEqual(desc, ["Ccc zorro", "Bbb zorro", "Aaa zorro"])

    def test_unknown_sort_column_is_ignored(self):
        self.assertEqual(self.g.get_json(self.URL, order="password").status_code, 200)

    def test_search(self):
        self.make_part("Pieza Rarísima Única")
        data = self.g.get_json(self.URL, q="rarísima").json()
        self.assertEqual(data["pagination"]["total"], 1)
        self.assertEqual(self.g.get_json(self.URL, q="zzzzzz").json()["pagination"]["total"], 0)

    def test_status_filter(self):
        part = self.make_part("Pieza vieja")
        self.g.put_json(
            f"/api/refacciones/{part['id']}/",
            {"name": part["name"], "unit_price": "10", "min_stock": 0, "is_active": False},
        )
        inactive = self.g.get_json(self.URL, status="inactive").json()
        self.assertEqual([p["name"] for p in inactive["spare_parts"]], ["Pieza vieja"])

    def test_pdf_of_a_list(self):
        r = self.g.get_json(self.URL, format="pdf", q="a")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r["Content-Type"], "application/pdf")
        self.assertTrue(r.content.startswith(b"%PDF"))
        self.assertIn(".pdf", r["Content-Disposition"])

    def test_pdf_export_is_audited(self):
        self.g.get_json(self.URL, format="pdf")
        self.assertTrue(AuditLog.objects.filter(action=AuditLog.EXPORT).exists())

    def test_pdf_ignores_pagination(self):
        small = self.g.get_json(self.URL, format="pdf", page_size=1)
        full = self.g.get_json(self.URL, format="pdf")
        self.assertEqual(len(small.content) > 0, True)
        self.assertGreater(len(full.content), 0)


class PdfPermissionsTest(ApiTestCase):
    LISTS = ["unidades", "trabajadores", "refacciones", "bitacora", "preventivo/vencimientos", "mantenimientos", "diagnosticos", "reportes-fallas", "checklists"]

    def test_every_list_can_export_for_the_manager(self):
        for name in self.LISTS:
            r = self.g.get_json(f"/api/{name}/", format="pdf")
            self.assertEqual(r.status_code, 200, name)
            self.assertTrue(r.content.startswith(b"%PDF"), name)

    def test_operator_cannot_export_manager_lists(self):
        for name in ("trabajadores", "bitacora", "unidades", "refacciones", "preventivo/vencimientos"):
            r = self.o.get_json(f"/api/{name}/", format="pdf")
            self.assertIn(r.status_code, (403, 404), name)

    def test_anonymous_cannot_export(self):
        from .base import ApiClient

        r = ApiClient().get("/api/unidades/", {"format": "pdf"})
        self.assertIn(r.status_code, (401, 403))
