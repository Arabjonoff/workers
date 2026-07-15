from datetime import date, timedelta

from django.contrib.auth.models import User
from django.test import TestCase, Client
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from main.models import (
    Company, AdminProfile, WorkerProfile, WorkCategory, Storage, Client as ClientModel,
)
from main.cronjobs import check_subscriptions


def make_tenant(name, username):
    company = Company.objects.create(name=name, start_date=date.today())
    user = User.objects.create(username=username, is_staff=True)
    user.set_password('pass12345')
    user.save()
    admin = AdminProfile.objects.create(user=user, company=company)
    return company, admin, user


class TenantIsolationTestCase(TestCase):
    def setUp(self):
        self.company_a, self.admin_a, self.user_a = make_tenant('Company A', 'admin_a')
        self.company_b, self.admin_b, self.user_b = make_tenant('Company B', 'admin_b')

        self.category_a = WorkCategory.objects.create(name='Cat A', admin=self.admin_a, price=1000, type='dona')
        self.category_b = WorkCategory.objects.create(name='Cat B', admin=self.admin_b, price=2000, type='dona')

        worker_user_a = User.objects.create(username='worker_a')
        worker_user_a.set_password('pass12345')
        worker_user_a.save()
        self.worker_a = WorkerProfile.objects.create(
            user=worker_user_a, admin=self.admin_a, phone=901111111, birth='2000-01-01', address='x'
        )

        worker_user_b = User.objects.create(username='worker_b')
        worker_user_b.set_password('pass12345')
        worker_user_b.save()
        self.worker_b = WorkerProfile.objects.create(
            user=worker_user_b, admin=self.admin_b, phone=902222222, birth='2000-01-01', address='y'
        )

        self.storage_a = Storage.objects.create(company=self.company_a, name='Storage A', type=1)
        self.client_a = ClientModel.objects.create(company=self.company_a, name='Client A', type=1)

        self.token_a = Token.objects.get(user=self.user_a).key
        self.token_b = Token.objects.get(user=self.user_b).key

    # ---- Dashboard IDOR checks ----

    def test_worker_detail_blocks_cross_tenant(self):
        c = Client()
        c.login(username='admin_a', password='pass12345')
        resp = c.get(f'/usta/worker/{self.worker_b.id}/')
        self.assertEqual(resp.status_code, 404)

    def test_works_list_delete_blocks_cross_tenant(self):
        c = Client()
        c.login(username='admin_a', password='pass12345')
        c.get(f'/usta/works/?id={self.category_b.id}')
        self.category_b.refresh_from_db()
        self.assertFalse(self.category_b.deleted)

    def test_works_list_edit_blocks_cross_tenant(self):
        c = Client()
        c.login(username='admin_a', password='pass12345')
        c.post('/usta/works/', {'id': self.category_b.id, 'name': 'hacked', 'price': 1})
        self.category_b.refresh_from_db()
        self.assertEqual(self.category_b.name, 'Cat B')

    # ---- API isolation checks ----

    def _api_client(self, token):
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION=f'Token {token}')
        return c

    def test_workers_viewset_list_only_own_tenant(self):
        c = self._api_client(self.token_a)
        resp = c.get('/api/v1/workers/')
        self.assertEqual(resp.status_code, 200)
        ids = [w['id'] for w in resp.data]
        self.assertIn(self.worker_a.id, ids)
        self.assertNotIn(self.worker_b.id, ids)

    def test_workers_viewset_retrieve_blocks_cross_tenant(self):
        c = self._api_client(self.token_a)
        resp = c.get(f'/api/v1/workers/{self.worker_b.id}/')
        self.assertEqual(resp.status_code, 404)

    def test_works_viewset_list_only_own_tenant(self):
        c = self._api_client(self.token_a)
        resp = c.get('/api/v1/works/')
        self.assertEqual(resp.status_code, 200)
        ids = [w['id'] for w in resp.data]
        self.assertIn(self.category_a.id, ids)
        self.assertNotIn(self.category_b.id, ids)

    def test_storage_viewset_list_only_own_tenant(self):
        c = self._api_client(self.token_a)
        resp = c.get('/api/v1/storage/')
        ids = [s['id'] for s in resp.data]
        self.assertIn(self.storage_a.id, ids)

    def test_workers_edit_cannot_hijack_other_tenant_worker(self):
        """Regression: WorkersViewSet.edit used to let Admin A steal Admin B's worker."""
        c = self._api_client(self.token_a)
        resp = c.post(f'/api/v1/workers/edit/?id={self.worker_b.id}', {
            'phone': '999999999', 'first_name': 'x', 'last_name': 'y',
            'birth': '2000-01-01', 'address': 'z', 'home_phone': '', 'works': [],
        }, format='json')
        self.worker_b.refresh_from_db()
        self.assertEqual(self.worker_b.admin_id, self.admin_b.id)

    def test_reset_password_blocks_cross_tenant(self):
        """Regression: reset_password used to allow account takeover of any tenant's worker."""
        c = self._api_client(self.token_a)
        old_password_hash = self.worker_b.user.password
        c.post(f'/api/v1/workers/{self.worker_b.id}/reset_password/', {'password': 'hacked123'}, format='json')
        self.worker_b.user.refresh_from_db()
        self.assertEqual(self.worker_b.user.password, old_password_hash)

    def test_unauthenticated_request_rejected(self):
        c = APIClient()
        resp = c.get('/api/v1/workers/')
        self.assertIn(resp.status_code, (401, 403))


class SubscriptionEnforcementTestCase(TestCase):
    def setUp(self):
        self.company, self.admin, self.user = make_tenant('Expiring Co', 'admin_exp')
        self.token = Token.objects.get(user=self.user).key

    def test_expired_subscription_blocks_dashboard_and_api(self):
        self.company.end_date = date.today() - timedelta(days=1)
        self.company.save()
        check_subscriptions()
        self.company.refresh_from_db()
        self.assertFalse(self.company.is_active)

        c = Client()
        c.login(username='admin_exp', password='pass12345')
        resp = c.get('/usta/')
        self.assertIn(resp.status_code, (302,))
        self.assertIn('blocked=1', resp.url)

        api = APIClient()
        api.credentials(HTTP_AUTHORIZATION=f'Token {self.token}')
        api_resp = api.get('/api/v1/workers/')
        self.assertEqual(api_resp.status_code, 403)

    def test_renewal_restores_access(self):
        self.company.end_date = date.today() - timedelta(days=1)
        self.company.is_active = False
        self.company.save()

        self.company.end_date = date.today() + timedelta(days=30)
        self.company.is_active = True
        self.company.save()

        api = APIClient()
        api.credentials(HTTP_AUTHORIZATION=f'Token {self.token}')
        resp = api.get('/api/v1/workers/')
        self.assertEqual(resp.status_code, 200)
