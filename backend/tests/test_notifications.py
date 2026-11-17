from notifications.models import Notification

from .base import ApiTestCase


class NotificationsApiTest(ApiTestCase):
    def setUp(self):
        super().setUp()
        for i in range(3):
            Notification.objects.create(user=self.operator, kind=Notification.REPORT_STATUS, message=f"Aviso {i}")
        Notification.objects.create(user=self.manager, kind=Notification.LOW_STOCK, message="Del gerente")

    def test_only_own_notifications(self):
        data = self.o.get_json("/api/notificaciones/").json()
        self.assertEqual(len(data["notifications"]), 3)
        self.assertEqual(data["unread"], 3)

    def test_summary_counts_unread(self):
        self.assertEqual(self.o.get("/api/notificaciones/resumen/").json()["unread"], 3)
        self.assertEqual(self.g.get("/api/notificaciones/resumen/").json()["unread"], 1)

    def test_mark_some_then_all_as_read(self):
        first = Notification.objects.filter(user=self.operator).first()
        self.o.post_json("/api/notificaciones/leer/", {"ids": [first.pk]})
        self.assertEqual(self.o.get("/api/notificaciones/resumen/").json()["unread"], 2)
        self.o.post_json("/api/notificaciones/leer/", {})
        self.assertEqual(self.o.get("/api/notificaciones/resumen/").json()["unread"], 0)

    def test_cannot_mark_someone_elses(self):
        theirs = Notification.objects.get(user=self.manager)
        self.o.post_json("/api/notificaciones/leer/", {"ids": [theirs.pk]})
        theirs.refresh_from_db()
        self.assertFalse(theirs.is_read)

    def test_unread_filter_and_clear_read(self):
        self.o.post_json("/api/notificaciones/leer/", {})
        self.assertEqual(len(self.o.get_json("/api/notificaciones/", unread=1).json()["notifications"]), 0)
        self.o.post_json("/api/notificaciones/limpiar/")
        self.assertEqual(Notification.objects.filter(user=self.operator).count(), 0)
        self.assertEqual(Notification.objects.filter(user=self.manager).count(), 1)

    def test_unread_notification_is_not_repeated_with_the_same_key(self):
        from notifications.service import notify

        for _ in range(3):
            notify([self.operator], Notification.LOW_STOCK, "x", key="k1", skip_actor=False)
        self.assertEqual(Notification.objects.filter(user=self.operator, key="k1").count(), 1)

    def test_requires_login(self):
        from .base import ApiClient

        self.assertIn(ApiClient().get("/api/notificaciones/").status_code, (401, 403))
