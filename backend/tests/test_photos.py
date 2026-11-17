import os
import re
import shutil
import tempfile
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from PIL import Image

from accounts.models import User
from audit.models import AuditLog

from .base import ApiClient, ApiTestCase

TEMP_MEDIA = tempfile.mkdtemp(prefix="romex-test-media-")


def make_image(fmt="JPEG", size=(300, 200), color=(200, 30, 30), exif=None, mode="RGB", name="foto.jpg"):
    image = Image.new(mode, size, color)
    out = BytesIO()
    kwargs = {}
    if exif is not None:
        kwargs["exif"] = exif
    image.save(out, format=fmt, **kwargs)
    types = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp", "GIF": "image/gif"}
    return SimpleUploadedFile(name, out.getvalue(), content_type=types[fmt])


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class WorkerPhotoTest(ApiTestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA, ignore_errors=True)

    def url(self, user=None):
        return f"/api/trabajadores/{(user or self.operator).pk}/foto/"

    def upload(self, file, user=None, client=None, query=""):
        return (client or self.g).post(self.url(user) + query, {"photo": file})

    def stored(self, user=None):
        return User.objects.get(pk=(user or self.operator).pk).photo

    # -- upload and processing ------------------------------------------------------------
    def test_worker_has_no_photo_at_first(self):
        data = self.g.get_json(f"/api/trabajadores/{self.operator.pk}/").json()["worker"]
        self.assertIsNone(data["photo_url"])
        self.assertEqual(self.g.get(self.url()).status_code, 404)

    def test_upload_stores_a_square_jpeg_and_returns_the_worker(self):
        r = self.upload(make_image(size=(400, 200)))
        self.assertEqual(r.status_code, 200, r.content)
        worker = r.json()["worker"]
        self.assertRegex(worker["photo_url"], rf"^trabajadores/{self.operator.pk}/foto/\?v=[0-9a-f]{{32}}$")
        photo = self.stored()
        with Image.open(photo.path) as image:
            self.assertEqual(image.format, "JPEG")
            self.assertEqual(image.size, (512, 512))

    def test_png_with_transparency_and_webp_are_accepted(self):
        self.assertEqual(self.upload(make_image("PNG", mode="RGBA", color=(0, 0, 0, 0), name="a.png")).status_code, 200)
        self.assertEqual(self.upload(make_image("WEBP", name="a.webp")).status_code, 200)

    def test_metadata_is_dropped(self):
        exif = Image.Exif()
        exif[0x010F] = "CamaraSecreta"  # camera make
        exif[0x8825] = {1: "N", 2: (25.0, 40.0, 0.0)}  # GPS block
        r = self.upload(make_image(exif=exif.tobytes()))
        self.assertEqual(r.status_code, 200)
        with open(self.stored().path, "rb") as handle:
            raw = handle.read()
        self.assertNotIn(b"CamaraSecreta", raw)
        with Image.open(self.stored().path) as image:
            self.assertEqual(len(image.getexif()), 0)

    def test_random_stored_name_does_not_use_the_original(self):
        self.upload(make_image(name="../../mi foto privada.jpg"))
        self.assertRegex(os.path.basename(self.stored().name), r"^[0-9a-f]{32}\.jpg$")
        self.assertTrue(self.stored().name.startswith("trabajadores/"))

    # -- what is refused ------------------------------------------------------------------
    def test_not_an_image_is_refused_even_if_named_jpg(self):
        r = self.upload(SimpleUploadedFile("foto.jpg", b"esto no es una imagen", content_type="image/jpeg"))
        self.assertEqual(r.status_code, 400)
        self.assertIn("no es una imagen válida", r.json()["errors"]["photo"][0])
        self.assertFalse(self.stored())

    def test_other_formats_are_refused(self):
        r = self.upload(make_image("GIF", name="a.gif"))
        self.assertEqual(r.status_code, 400)
        self.assertIn("JPG, PNG o WebP", r.json()["errors"]["photo"][0])

    def test_too_heavy_is_refused(self):
        big = SimpleUploadedFile("grande.jpg", b"\xff\xd8" + b"0" * (5 * 1024 * 1024 + 10), content_type="image/jpeg")
        r = self.upload(big)
        self.assertEqual(r.status_code, 400)
        self.assertIn("5 MB", r.json()["errors"]["photo"][0])

    def test_missing_file_is_refused(self):
        r = self.g.post(self.url(), {})
        self.assertEqual(r.status_code, 400)
        self.assertIn("photo", r.json()["errors"])

    def test_validation_only_does_not_save(self):
        r = self.upload(make_image(), query="?validar=1")
        self.assertEqual(r.json()["errors"], {})
        self.assertFalse(self.stored())
        bad = self.upload(SimpleUploadedFile("x.jpg", b"no", content_type="image/jpeg"), query="?validar=1")
        self.assertIn("photo", bad.json()["errors"])

    def test_unknown_worker(self):
        self.assertEqual(self.g.post("/api/trabajadores/999999/foto/", {"photo": make_image()}).status_code, 404)

    # -- permissions ----------------------------------------------------------------------
    def test_only_the_manager_changes_photos(self):
        for client in (self.o, self.m):
            self.assertEqual(self.upload(make_image(), client=client).status_code, 403)
            self.assertEqual(client.delete(self.url()).status_code, 403)
        self.assertEqual(self.upload(make_image(), client=ApiClient()).status_code, 401)
        self.assertFalse(self.stored())

    def test_who_can_see_a_photo(self):
        self.upload(make_image())
        r = self.g.get(self.url())
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r["Content-Type"], "image/jpeg")
        self.assertEqual(r["X-Content-Type-Options"], "nosniff")
        self.assertIn("private", r["Cache-Control"])
        self.assertEqual(b"".join(r.streaming_content)[:2], b"\xff\xd8")
        self.assertEqual(self.o.get(self.url()).status_code, 200)  # their own
        self.assertEqual(self.client_for(self.operator2).get(self.url()).status_code, 403)  # someone else's
        self.assertEqual(self.m.get(self.url()).status_code, 403)
        self.assertEqual(ApiClient().get(self.url()).status_code, 401)

    def test_me_and_worker_list_carry_the_photo_address(self):
        self.upload(make_image())
        me = self.o.get("/api/auth/me/").json()["user"]
        self.assertRegex(me["photo_url"], r"^trabajadores/\d+/foto/\?v=")
        self.assertIsNone(self.m.get("/api/auth/me/").json()["user"]["photo_url"])
        rows = self.g.get_json("/api/trabajadores/", page_size=100).json()["workers"]
        by_id = {w["enrollment_id"]: w for w in rows}
        self.assertIsNotNone(by_id["O1"]["photo_url"])
        self.assertIsNone(by_id["O2"]["photo_url"])

    # -- replacing and removing -----------------------------------------------------------
    def test_replacing_deletes_the_old_file(self):
        self.upload(make_image())
        old = self.stored().path
        self.assertTrue(os.path.isfile(old))
        first_url = self.g.get_json(f"/api/trabajadores/{self.operator.pk}/").json()["worker"]["photo_url"]
        self.upload(make_image(color=(0, 0, 200)))
        new = self.stored().path
        self.assertNotEqual(old, new)
        self.assertFalse(os.path.exists(old))
        self.assertTrue(os.path.isfile(new))
        self.assertNotEqual(first_url, self.g.get_json(f"/api/trabajadores/{self.operator.pk}/").json()["worker"]["photo_url"])

    def test_removing_deletes_the_file_and_goes_back_to_no_photo(self):
        self.upload(make_image())
        path = self.stored().path
        r = self.g.delete(self.url())
        self.assertEqual(r.status_code, 200)
        self.assertIsNone(r.json()["worker"]["photo_url"])
        self.assertFalse(os.path.exists(path))
        self.assertEqual(self.g.get(self.url()).status_code, 404)
        # Removing again is harmless
        self.assertEqual(self.g.delete(self.url()).status_code, 200)

    def test_editing_the_worker_keeps_the_photo(self):
        self.upload(make_image())
        before = self.stored().name
        detail = self.g.get_json(f"/api/trabajadores/{self.operator.pk}/").json()["worker"]
        payload = {
            "enrollment_id": detail["enrollment_id"], "first_name": "Cambiado", "paternal_surname": detail["paternal_surname"],
            "maternal_surname": detail["maternal_surname"], "email": detail["email"], "phone_code_id": detail["phone_code"]["id"], "phone_number": detail["phone_number"],
            "sex_id": detail["sex"]["id"], "role_id": detail["role"]["id"], "is_active": True, "password": "",
            "address": {"state": "Coahuila de Zaragoza", "municipality": "Saltillo", "neighborhood": "Centro", "street": "Calle Uno", "exterior_number": "1", "interior_number": ""},
        }
        r = self.g.put_json(f"/api/trabajadores/{self.operator.pk}/", payload)
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(self.stored().name, before)

    def test_deleting_a_worker_deletes_the_photo_file(self):
        from accounts.models import PhoneCode, Sex

        roles = {r["label"]: r["id"] for r in self.g.get("/api/trabajadores/catalogos/").json()["roles"]}
        created = self.g.post_json("/api/trabajadores/", {
            "enrollment_id": "TMP1", "first_name": "Tmp", "paternal_surname": "P", "maternal_surname": "M",
            "email": "t@example.com", "phone_code_id": PhoneCode.objects.get(iso="MX").pk, "phone_number": "8441112233", "sex_id": Sex.objects.first().pk,
            "role_id": roles["Operador"], "is_active": True, "password": "Temporal12345x",
            "address": {"state": "Coahuila de Zaragoza", "municipality": "Saltillo", "neighborhood": "Centro", "street": "Calle Uno", "exterior_number": "5", "interior_number": ""},
        })
        self.assertEqual(created.status_code, 201, created.content)
        worker_id = created.json()["worker"]["id"]
        self.g.post(f"/api/trabajadores/{worker_id}/foto/", {"photo": make_image()})
        path = User.objects.get(pk=worker_id).photo.path
        self.assertTrue(os.path.isfile(path))
        self.assertEqual(self.g.delete(f"/api/trabajadores/{worker_id}/").status_code, 200)
        self.assertFalse(os.path.exists(path))

    def test_photo_changes_are_audited_without_the_image(self):
        self.upload(make_image())
        entry = AuditLog.objects.filter(action=AuditLog.UPDATE, table_name="usuarios").order_by("-id").first()
        self.assertIsNotNone(entry)
        self.assertEqual(entry.user_enrollment_id, "G1")
        self.assertTrue(re.search(r"trabajadores/", str(entry.changes)))
        self.assertLess(len(str(entry.changes)), 500)
