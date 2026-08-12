from datetime import date

from django.test import TestCase
from django.urls import reverse

from Appointments.models import Appointment
from Clients.models import Client
from Users.models import User


def make_nutri(email, is_staff=False):
    return User.objects.create_user(
        username=email,
        email=email,
        password='x',
        first_name='Test',
        last_name='User',
        is_staff=is_staff,
    )


def make_client(user, first_name):
    return Client.objects.create(
        user=user,
        email=f'{first_name.lower()}@example.com',
        first_name=first_name,
        last_name='Apellido',
        birth_date=date(1990, 1, 1),
        gender='Male',
        height=180,
        weight='80.00',
        dni='00000000A',
        phone_number='600000000',
        phone_number_2='',
        address='',
        postal_code='',
        city='',
        activity_level='Moderada',
    )


class ClientIsolationTests(TestCase):

    def setUp(self):
        self.nutri1 = make_nutri('nutri1@example.com')
        self.nutri2 = make_nutri('nutri2@example.com')
        self.admin = make_nutri('admin@example.com', is_staff=True)
        self.client1 = make_client(self.nutri1, 'Cliente1')
        self.client2 = make_client(self.nutri2, 'Cliente2')

    def test_list_active_clients_is_scoped_per_nutricionista(self):
        self.client.force_login(self.nutri1)
        response = self.client.get(reverse('list_active_clients'))
        visible_ids = {c.id for c in response.context['clients']}
        self.assertEqual(visible_ids, {self.client1.id})

        self.client.force_login(self.nutri2)
        response = self.client.get(reverse('list_active_clients'))
        visible_ids = {c.id for c in response.context['clients']}
        self.assertEqual(visible_ids, {self.client2.id})

    def test_admin_sees_all_clients(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('list_active_clients'))
        visible_ids = {c.id for c in response.context['clients']}
        self.assertEqual(visible_ids, {self.client1.id, self.client2.id})

    def test_client_detail_of_other_nutricionista_is_not_found(self):
        self.client.force_login(self.nutri1)
        response = self.client.get(reverse('client_detail', args=[self.client2.id]))
        self.assertEqual(response.status_code, 404)

        response = self.client.get(reverse('client_detail', args=[self.client1.id]))
        self.assertEqual(response.status_code, 200)

    def test_admin_can_open_any_client_detail(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('client_detail', args=[self.client1.id]))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse('client_detail', args=[self.client2.id]))
        self.assertEqual(response.status_code, 200)


class AppointmentIsolationTests(TestCase):

    def setUp(self):
        self.nutri1 = make_nutri('nutri1@example.com')
        self.nutri2 = make_nutri('nutri2@example.com')
        self.client1 = make_client(self.nutri1, 'Cliente1')
        self.client2 = make_client(self.nutri2, 'Cliente2')
        self.appointment1 = Appointment.objects.create(
            user=self.nutri1,
            client=self.client1,
            status='Pendiente',
            start_date='2026-09-01T10:00:00Z',
            end_date='2026-09-01T10:30:00Z',
        )
        self.appointment2 = Appointment.objects.create(
            user=self.nutri2,
            client=self.client2,
            status='Pendiente',
            start_date='2026-09-01T11:00:00Z',
            end_date='2026-09-01T11:30:00Z',
        )

    def test_update_appointment_of_other_nutricionista_is_rejected(self):
        self.client.force_login(self.nutri1)
        response = self.client.post(
            reverse('update_appointment', args=[self.appointment2.id]),
            {
                'client_id': self.client2.id,
                'start_date': '2026-09-02T10:00:00',
                'duration_minutes': '30',
                'motive': 'Intento de edicion ajena',
            },
        )
        self.appointment2.refresh_from_db()
        self.assertEqual(self.appointment2.motive, 'Consulta inicial')
        self.assertRedirects(response, reverse('appointments'))

    def test_own_appointment_can_be_updated(self):
        self.client.force_login(self.nutri1)
        response = self.client.post(
            reverse('update_appointment', args=[self.appointment1.id]),
            {
                'client_id': self.client1.id,
                'start_date': '2026-09-02T10:00:00',
                'duration_minutes': '30',
                'motive': 'Edicion propia',
            },
        )
        self.appointment1.refresh_from_db()
        self.assertEqual(self.appointment1.motive, 'Edicion propia')
