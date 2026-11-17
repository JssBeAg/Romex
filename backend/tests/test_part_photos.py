"""Optional photo of a spare part: processing, permissions, replacing, removing and cleanup."""

import os
import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from PIL import Image

from audit.models import AuditLog
from fleet.models import SparePart

from .base import ApiClient, ApiTestCase
from .test_photos import make_image

TEMP_MEDIA = tempfile.mkdtemp(prefix="romex-test-part-media-")


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class SparePartPhotoTest(ApiTestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA, ignore_errors=True)

    def setUp(self):
        super().setUp()
        self.part = self.make_part("Filtro de prueba", stock=3)
        self.pid = self.part["id"]

    def url(self):
        return f"/api/refacciones/{self.pid}/foto/"

    def upload(self, file, client=None, query=""):
        return (client or self.g).post(self.url() + query, {"photo": file})

    def stored(self):
        return SparePart.objects.get(pk=self.pid).photo

    def detail(self):
        return self.g.get_json(f"/api/refacciones/{self.pid}/").json()["spare_part"]

    # -- upload and processing ------------------------------------------------------------
    def test_part_has_no_photo_at_first(self):
        self.assertIsNone(self.part["photo_url"])
        self.assertEqual(self.g.get(self.url()).status_code, 404)

    def test_upload_keeps_proportions_and_shrinks_large_images(self):
        r = self.upload(make_image(size=(2000, 1000)))
        self.assertEqual(r.status_code, 200, r.content)
        part = r.json()["spare_part"]
        self.assertRegex(part["photo_url"], rf"^refacciones/{self.pid}/foto/\?v=[0-9a-f]{{32}}$")
        with Image.open(self.stored().path) as image:
            self.assertEqual(image.format, "JPEG")
            self.assertEqual(image.size, (800, 400))  # not cropped to a square

    def test_small_images_are_not_enlarged(self):
        self.upload(make_image(size=(300, 200)))
        with Image.open(self.stored().path) as image:
            self.assertEqual(image.size, (300, 200))

    def test_response_keeps_the_stock_data(self):
        part = self.upload(make_image()).json()["spare_part"]
        self.assertEqual(part["stock"], 3)
        self.assertEqual(part["name"], "Filtro de prueba")

    def test_png_with_transparency_and_webp_are_accepted(self):
        self.assertEqual(self.upload(make_image("PNG", mode="RGBA", color=(0, 0, 0, 0), name="a.png")).status_code, 200)
        self.assertEqual(self.upload(make_image("WEBP", name="a.webp")).status_code, 200)

    def test_metadata_is_dropped_and_the_name_is_random(self):
        exif = Image.Exif()
        exif[0x010F] = "CamaraSecreta"
        exif[0x8825] = {1: "N", 2: (25.0, 40.0, 0.0)}
        self.assertEqual(self.upload(make_image(exif=exif.tobytes(), name="../../mi pieza.jpg")).status_code, 200)
        with open(self.stored().path, "rb") as handle:
            self.assertNotIn(b"CamaraSecreta", handle.read())
        self.assertRegex(os.path.basename(self.stored().name), r"^[0-9a-f]{32}\.jpg$")
        self.assertTrue(self.stored().name.startswith("refacciones/"))

    # -- what is refused ------------------------------------------------------------------
    def test_not_an_image_other_formats_heavy_and_missing_are_refused(self):
        fake = self.upload(SimpleUploadedFile("foto.jpg", b"esto no es una imagen", content_type="image/jpeg"))
        self.assertEqual(fake.status_code, 400)
        self.assertIn("no es una imagen válida", fake.json()["errors"]["photo"][0])
        gif = self.upload(make_image("GIF", name="a.gif"))
        self.assertIn("JPG, PNG o WebP", gif.json()["errors"]["photo"][0])
        big = SimpleUploadedFile("g.jpg", b"\xff\xd8" + b"0" * (5 * 1024 * 1024 + 10), content_type="image/jpeg")
        self.assertIn("5 MB", self.upload(big).json()["errors"]["photo"][0])
        self.assertEqual(self.g.post(self.url(), {}).status_code, 400)
        self.assertFalse(self.stored())

    def test_validation_only_does_not_save(self):
        self.assertEqual(self.upload(make_image(), query="?validar=1").json()["errors"], {})
        self.assertFalse(self.stored())

    def test_unknown_part(self):
        self.assertEqual(self.g.post("/api/refacciones/999999/foto/", {"photo": make_image()}).status_code, 404)
        self.assertEqual(self.g.get("/api/refacciones/999999/foto/").status_code, 404)

    # -- permissions ----------------------------------------------------------------------
    def test_only_the_manager_can_see_upload_or_remove(self):
        self.upload(make_image())
        for client in (self.o, self.m):
            self.assertEqual(client.get(self.url()).status_code, 403)
            self.assertEqual(self.upload(make_image(), client=client).status_code, 403)
            self.assertEqual(client.delete(self.url()).status_code, 403)
        anon = ApiClient()
        self.assertEqual(anon.get(self.url()).status_code, 401)
        self.assertEqual(self.upload(make_image(), client=anon).status_code, 401)
        self.assertTrue(self.stored())

    def test_manager_gets_the_image_with_safe_headers(self):
        self.upload(make_image())
        r = self.g.get(self.url())
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r["Content-Type"], "image/jpeg")
        self.assertEqual(r["X-Content-Type-Options"], "nosniff")
        self.assertIn("private", r["Cache-Control"])
        self.assertEqual(b"".join(r.streaming_content)[:2], b"\xff\xd8")

    def test_list_and_detail_carry_the_photo_address(self):
        other = self.make_part("Sin foto")
        self.upload(make_image())
        rows = self.g.get_json("/api/refacciones/", page_size=100).json()["spare_parts"]
        by_id = {p["id"]: p for p in rows}
        self.assertIsNotNone(by_id[self.pid]["photo_url"])
        self.assertIsNone(by_id[other["id"]]["photo_url"])
        self.assertIsNotNone(self.detail()["photo_url"])

    # -- replacing, removing, editing, deleting --------------------------------------------
    def test_replacing_deletes_the_old_file_and_changes_the_address(self):
        self.upload(make_image())
        old, first_url = self.stored().path, self.detail()["photo_url"]
        self.upload(make_image(color=(0, 0, 200)))
        self.assertFalse(os.path.exists(old))
        self.assertTrue(os.path.isfile(self.stored().path))
        self.assertNotEqual(first_url, self.detail()["photo_url"])

    def test_removing_deletes_the_file(self):
        self.upload(make_image())
        path = self.stored().path
        r = self.g.delete(self.url())
        self.assertEqual(r.status_code, 200)
        self.assertIsNone(r.json()["spare_part"]["photo_url"])
        self.assertFalse(os.path.exists(path))
        self.assertEqual(self.g.get(self.url()).status_code, 404)
        self.assertEqual(self.g.delete(self.url()).status_code, 200)  # harmless twice

    def test_editing_the_part_keeps_the_photo(self):
        self.upload(make_image())
        before = self.stored().name
        d = self.detail()
        r = self.g.put_json(f"/api/refacciones/{self.pid}/", {
            "name": "Filtro renombrado", "description": d["description"], "unit_price": "",
            "min_stock": 1, "is_active": True,
        })
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(self.stored().name, before)
        self.assertEqual(r.json()["spare_part"]["photo_url"], d["photo_url"])

    def test_deleting_the_part_deletes_the_file(self):
        fresh = self.make_part("Para borrar")
        url = f"/api/refacciones/{fresh['id']}/foto/"
        self.g.post(url, {"photo": make_image()})
        path = SparePart.objects.get(pk=fresh["id"]).photo.path
        self.assertTrue(os.path.isfile(path))
        self.assertEqual(self.g.delete(f"/api/refacciones/{fresh['id']}/").status_code, 200)
        self.assertFalse(os.path.exists(path))

    def test_changes_are_audited_without_the_file_content(self):
        self.upload(make_image())
        entry = AuditLog.objects.filter(action=AuditLog.UPDATE, table_name="refacciones").order_by("-id").first()
        self.assertIsNotNone(entry)
        self.assertIn("Fotografía", entry.changes)

    def test_admin_panel_does_not_offer_the_raw_upload(self):
        from django.contrib import admin

        self.assertIn("photo", admin.site._registry[SparePart].exclude)
