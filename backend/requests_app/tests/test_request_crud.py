from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from requests_app.models import Category, ServiceRequest, WorkOrder
from requests_app.services import service_request_assign


class ServiceRequestCrudTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.owner = User.objects.create_user("owner", password="pass12345")
        self.other = User.objects.create_user("other", password="pass12345")
        self.category = Category.objects.create(name="Facilities")
        self.item = ServiceRequest.objects.create(
            requester=self.owner,
            category=self.category,
            title="Projector does not display",
            description="The projector reports no HDMI signal.",
            location="Room B12",
            priority="MEDIUM",
        )

    def test_list_requires_login(self):
        response = self.client.get(reverse("requests:list"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)

    def test_owner_can_open_detail(self):
        self.client.force_login(self.owner)
        response = self.client.get(reverse("requests:detail", args=[self.item.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.item.title)

    def test_other_requester_receives_404(self):
        self.client.force_login(self.other)
        response = self.client.get(reverse("requests:detail", args=[self.item.id]))
        self.assertEqual(response.status_code, 404)

    def test_valid_post_creates_request_for_logged_in_user(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("requests:create"),
            {
                "category": self.category.id,
                "title": "Air conditioner leaks water",
                "description": "Water drips near the laboratory entrance.",
                "location": "Software Laboratory",
                "priority": "HIGH",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            ServiceRequest.objects.filter(
                requester=self.owner, title="Air conditioner leaks water"
            ).exists()
        )

    def test_invalid_post_does_not_create_request(self):
        self.client.force_login(self.owner)
        before = ServiceRequest.objects.count()
        response = self.client.post(
            reverse("requests:create"),
            {
                "category": self.category.id,
                "title": "Short",
                "description": "",
                "location": "",
                "priority": "HIGH",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ServiceRequest.objects.count(), before)
        self.assertContains(response, "Use at least 8 characters.")

    def test_non_staff_assignment_returns_403_and_creates_no_work_order(self):
        self.client.force_login(self.owner)
        staff = get_user_model().objects.create_user(
            "tech1", password="pass12345", is_staff=True
        )
        response = self.client.post(
            reverse("requests:assign", args=[self.item.id]),
            {"technician": staff.id},
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(WorkOrder.objects.count(), 0)

    def test_staff_assignment_creates_work_order_and_sets_assigned(self):
        staff = get_user_model().objects.create_user(
            "tech1", password="pass12345", is_staff=True
        )
        self.client.force_login(staff)
        response = self.client.post(
            reverse("requests:assign", args=[self.item.id]),
            {"technician": staff.id},
        )
        self.assertEqual(response.status_code, 302)
        self.item.refresh_from_db()
        self.assertEqual(self.item.status, ServiceRequest.Status.ASSIGNED)
        self.assertEqual(WorkOrder.objects.filter(service_request=self.item).count(), 1)

    def test_resolution_without_assignment_leaves_request_unchanged(self):
        staff = get_user_model().objects.create_user(
            "tech1", password="pass12345", is_staff=True
        )
        self.client.force_login(staff)
        response = self.client.post(
            reverse("requests:resolve", args=[self.item.id]),
            {"work_notes": "Attempted resolution without assignment."},
        )
        self.assertEqual(response.status_code, 302)
        self.item.refresh_from_db()
        self.assertEqual(self.item.status, ServiceRequest.Status.OPEN)
        self.assertIsNone(self.item.resolved_at)

    def test_assigned_technician_resolution_changes_both_models(self):
        tech = get_user_model().objects.create_user(
            "tech1", password="pass12345", is_staff=True
        )
        work_order = service_request_assign(
            item=self.item, technician=tech, actor=tech
        )
        self.client.force_login(tech)
        response = self.client.post(
            reverse("requests:resolve", args=[self.item.id]),
            {"work_notes": "Replaced faulty HDMI cable and verified signal."},
        )
        self.assertEqual(response.status_code, 302)
        self.item.refresh_from_db()
        work_order.refresh_from_db()
        self.assertEqual(self.item.status, ServiceRequest.Status.RESOLVED)
        self.assertIsNotNone(self.item.resolved_at)
        self.assertEqual(
            work_order.work_notes, "Replaced faulty HDMI cable and verified signal."
        )
        self.assertIsNotNone(work_order.completed_at)

    def test_filtered_pagination_preserves_q_and_status(self):
        for i in range(12):
            ServiceRequest.objects.create(
                requester=self.owner,
                category=self.category,
                title=f"Lab network outage #{i}",
                description="Switch port down.",
                location="ICT Lab",
                priority="HIGH",
                status=ServiceRequest.Status.OPEN,
            )
        self.client.force_login(self.owner)
        response = self.client.get(
            reverse("requests:list"),
            {"q": "network", "status": "OPEN", "page": 2},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["query"], "network")
        self.assertEqual(response.context["selected_status"], "OPEN")
        self.assertContains(response, "q=network")
        self.assertContains(response, "status=OPEN")