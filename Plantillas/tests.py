import json
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from Dishes.models import Dish, DishProduct
from Menus.generator.meal_structure import get_meal_structure
from Plantillas.models import Template, TemplateIntake
from Products.models import Product
from Users.models import User


def make_nutri(email):
    return User.objects.create_user(username=email, email=email, password='x', first_name='T', last_name='U')


def make_product(name, kcal, prot, fat, carb):
    return Product.objects.create(
        food_name=name, food_name_spanish=name, food_name_eng=name, origin_db='test',
        ed_porc=100, kcal_100g=kcal, prot_g=prot, ch_g=carb, fat_g=fat,
    )


def make_dish(name, dish_type, product, quantity=200, user=None):
    dish = Dish.objects.create(name=name, recipe_elaboration='', language='es', dish_type=dish_type, user=user)
    DishProduct.objects.create(dish=dish, product=product, quantity=quantity)
    return dish


def make_template(user, name='Plantilla', daily_kcal=2000, duration=2, active=True):
    return Template.objects.create(
        user=user, name=name, daily_kcal=daily_kcal, duration=duration, active=active,
    )


class CreateTemplateViewTests(TestCase):

    def setUp(self):
        self.nutri = make_nutri('plantilla_nutri1@example.com')

    def _valid_payload(self, **overrides):
        payload = {
            'name': 'Plantilla semanal',
            'daily_kcal': '2000',
            'duration': '3',
            'include_comida': 'on',
            'platos_comida': '1',
        }
        payload.update(overrides)
        return payload

    def test_valid_post_creates_template_and_intake_skeleton(self):
        self.client.force_login(self.nutri)
        response = self.client.post(reverse('create_template'), self._valid_payload())

        template = Template.objects.get(user=self.nutri)
        self.assertRedirects(response, reverse('template_detail', args=[template.id]))
        self.assertEqual(template.name, 'Plantilla semanal')
        self.assertEqual(template.daily_kcal, 2000)
        self.assertEqual(template.duration, 3)
        self.assertTrue(template.active)

        items = list(TemplateIntake.objects.filter(template=template))
        # 3 dias x 1 toma (solo 'main' de comida: sin entrante ni postre en el payload)
        self.assertEqual(len(items), 3)
        for item in items:
            self.assertIsNone(item.dish_id)
            self.assertFalse(item.is_free_meal)
            self.assertEqual(item.quantity, 0)
            self.assertEqual(item.kcal, Decimal('0'))

    def test_post_without_name_creates_nothing(self):
        self.client.force_login(self.nutri)
        response = self.client.post(reverse('create_template'), self._valid_payload(name=''))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Template.objects.exists())

    def test_post_without_intakes_selected_creates_nothing(self):
        self.client.force_login(self.nutri)
        response = self.client.post(reverse('create_template'), self._valid_payload(include_comida=''))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Template.objects.exists())

    def test_post_with_zero_duration_creates_nothing(self):
        self.client.force_login(self.nutri)
        response = self.client.post(reverse('create_template'), self._valid_payload(duration='0'))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Template.objects.exists())

    def test_post_with_negative_daily_kcal_creates_nothing(self):
        self.client.force_login(self.nutri)
        response = self.client.post(reverse('create_template'), self._valid_payload(daily_kcal='-100'))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Template.objects.exists())

    def test_post_with_non_numeric_duration_creates_nothing(self):
        self.client.force_login(self.nutri)
        response = self.client.post(reverse('create_template'), self._valid_payload(duration='abc'))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Template.objects.exists())

    def test_duration_and_daily_kcal_above_upper_bound_are_rejected(self):
        # Hallazgo [Low] corregido: create_template ahora rechaza
        # daily_kcal > 10000 y duration > 90 en vez de aceptar cualquier
        # valor positivo.
        self.client.force_login(self.nutri)
        response = self.client.post(reverse('create_template'), self._valid_payload(
            duration='400', daily_kcal='999999999',
        ))
        self.assertEqual(response.status_code, 200)
        # daily_kcal se valida antes que duration (elif), asi que con ambos
        # valores fuera de rango el mensaje mostrado es el de kcal.
        self.assertContains(response, 'Indica unas kcal diarias válidas (entre 1 y 10000).')
        self.assertFalse(Template.objects.exists())
        self.assertFalse(TemplateIntake.objects.exists())

    def test_duration_above_upper_bound_alone_is_rejected(self):
        self.client.force_login(self.nutri)
        response = self.client.post(reverse('create_template'), self._valid_payload(duration='91'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Indica una duración en días válida (entre 1 y 90 días).')
        self.assertFalse(Template.objects.exists())
        self.assertFalse(TemplateIntake.objects.exists())

    def test_duration_and_daily_kcal_at_upper_bound_are_accepted(self):
        # Los limites son inclusive (> 10000 / > 90 rechazan, no >=), asi que
        # los valores frontera deben aceptarse.
        self.client.force_login(self.nutri)
        response = self.client.post(reverse('create_template'), self._valid_payload(
            duration='90', daily_kcal='10000',
        ))
        self.assertEqual(response.status_code, 302)
        template = Template.objects.get(user=self.nutri)
        self.assertEqual(template.duration, 90)
        self.assertEqual(template.daily_kcal, 10000)
        self.assertEqual(TemplateIntake.objects.filter(template=template).count(), 90)


class TemplateDetailViewTests(TestCase):

    def setUp(self):
        self.nutri = make_nutri('tpl_detail1@example.com')
        self.other_nutri = make_nutri('tpl_detail2@example.com')
        self.template = make_template(self.nutri)
        _, groups = get_meal_structure()
        self.main_intake = groups['comida']['main']
        TemplateIntake.objects.create(
            template=self.template, dish=None, intake=self.main_intake,
            quantity=0, kcal=Decimal('0'), menu_day=0, intake_alias='Plato principal - Comida',
        )

    def test_owner_can_view_detail(self):
        self.client.force_login(self.nutri)
        response = self.client.get(reverse('template_detail', args=[self.template.id]))
        self.assertEqual(response.status_code, 200)

    def test_other_nutri_gets_404(self):
        self.client.force_login(self.other_nutri)
        response = self.client.get(reverse('template_detail', args=[self.template.id]))
        self.assertEqual(response.status_code, 404)

    def test_nonexistent_template_returns_404(self):
        self.client.force_login(self.nutri)
        response = self.client.get(reverse('template_detail', args=[999999]))
        self.assertEqual(response.status_code, 404)


class DeactivatedTemplateAccessTests(TestCase):
    """Hallazgo [Medium] de la revision de codigo, ya corregido:
    edit_template_intake y copy_template_intake ahora resuelven la plantilla
    con scoped_queryset(Template.objects.filter(active=True), ...), igual
    que edit_template/deactivate_template/etc, por lo que una plantilla
    desactivada devuelve 404 en esos dos endpoints. template_detail sigue
    sin filtrar por active a proposito (comportamiento intencional, no
    tocado por la correccion) y sigue devolviendo 200."""

    def setUp(self):
        self.nutri = make_nutri('tpl_inactive1@example.com')
        self.template = make_template(self.nutri, active=False)
        _, groups = get_meal_structure()
        self.main_intake = groups['comida']['main']
        self.p_main = make_product('Pollo', kcal=200, prot=30, fat=5, carb=0)
        self.dish_main = make_dish('Pollo asado', Dish.DishType.MAIN, self.p_main)
        self.item = TemplateIntake.objects.create(
            template=self.template, dish=None, intake=self.main_intake,
            quantity=0, kcal=Decimal('0'), menu_day=0, intake_alias='Plato principal - Comida',
        )
        self.other_item = TemplateIntake.objects.create(
            template=self.template, dish=None, intake=self.main_intake,
            quantity=0, kcal=Decimal('0'), menu_day=1, intake_alias='Plato principal - Comida',
        )

    def test_template_detail_still_accessible_when_inactive(self):
        self.client.force_login(self.nutri)
        response = self.client.get(reverse('template_detail', args=[self.template.id]))
        # CONFIRMADO: template_detail no filtra por active, por lo que una
        # plantilla desactivada sigue siendo visible (200, no 404).
        self.assertEqual(response.status_code, 200)

    def test_edit_template_intake_get_returns_404_when_inactive(self):
        self.client.force_login(self.nutri)
        url = reverse('edit_template_intake', args=[self.template.id, self.item.id])
        response = self.client.get(url)
        # CORREGIDO: el GET de edit_template_intake ahora devuelve 404 para
        # una plantilla desactivada (scoped_queryset filtra active=True).
        self.assertEqual(response.status_code, 404)

    def test_edit_template_intake_post_returns_404_and_does_not_write_when_inactive(self):
        self.client.force_login(self.nutri)
        url = reverse('edit_template_intake', args=[self.template.id, self.item.id])
        response = self.client.post(
            url, data=json.dumps({'dish_id': self.dish_main.id, 'quantity': 100}),
            content_type='application/json',
        )
        # CORREGIDO: el POST ya no persiste ningun cambio en una celda de
        # una plantilla desactivada; responde 404 antes de tocar el item.
        self.assertEqual(response.status_code, 404)
        self.item.refresh_from_db()
        self.assertIsNone(self.item.dish_id)
        self.assertEqual(self.item.quantity, 0)

    def test_copy_template_intake_returns_404_when_inactive(self):
        self.item.dish = self.dish_main
        self.item.quantity = 100
        self.item.kcal = Decimal('200.00')
        self.item.save(update_fields=['dish', 'quantity', 'kcal'])

        self.client.force_login(self.nutri)
        url = reverse('copy_template_intake', args=[self.template.id, self.item.id])
        response = self.client.get(url)
        # CORREGIDO: copy_template_intake ahora devuelve 404 para una
        # plantilla desactivada.
        self.assertEqual(response.status_code, 404)


class EditTemplateViewTests(TestCase):

    def setUp(self):
        self.nutri = make_nutri('tpl_edit1@example.com')
        self.other_nutri = make_nutri('tpl_edit2@example.com')
        self.template = make_template(self.nutri, name='Original', daily_kcal=1800)

    def test_owner_can_edit_name_and_kcal(self):
        self.client.force_login(self.nutri)
        response = self.client.post(reverse('edit_template', args=[self.template.id]), {
            'name': 'Nuevo nombre', 'daily_kcal': '2200',
        })
        self.assertRedirects(response, reverse('list_templates'))
        self.template.refresh_from_db()
        self.assertEqual(self.template.name, 'Nuevo nombre')
        self.assertEqual(self.template.daily_kcal, 2200)

    def test_other_nutri_cannot_edit(self):
        self.client.force_login(self.other_nutri)
        response = self.client.post(reverse('edit_template', args=[self.template.id]), {
            'name': 'Hackeado', 'daily_kcal': '1',
        })
        self.assertEqual(response.status_code, 404)
        self.template.refresh_from_db()
        self.assertEqual(self.template.name, 'Original')

    def test_edit_deactivated_template_returns_404(self):
        self.template.active = False
        self.template.save(update_fields=['active'])
        self.client.force_login(self.nutri)
        response = self.client.post(reverse('edit_template', args=[self.template.id]), {
            'name': 'X', 'daily_kcal': '2000',
        })
        self.assertEqual(response.status_code, 404)

    def test_get_not_allowed(self):
        self.client.force_login(self.nutri)
        response = self.client.get(reverse('edit_template', args=[self.template.id]))
        self.assertEqual(response.status_code, 405)

    def test_daily_kcal_above_upper_bound_is_rejected(self):
        self.client.force_login(self.nutri)
        response = self.client.post(reverse('edit_template', args=[self.template.id]), {
            'name': 'Original', 'daily_kcal': '10001',
        })
        self.assertRedirects(response, reverse('list_templates'))
        self.template.refresh_from_db()
        self.assertEqual(self.template.daily_kcal, 1800)

    def test_daily_kcal_zero_or_negative_is_rejected(self):
        self.client.force_login(self.nutri)
        response = self.client.post(reverse('edit_template', args=[self.template.id]), {
            'name': 'Original', 'daily_kcal': '0',
        })
        self.assertRedirects(response, reverse('list_templates'))
        self.template.refresh_from_db()
        self.assertEqual(self.template.daily_kcal, 1800)

    def test_daily_kcal_at_upper_bound_is_accepted(self):
        self.client.force_login(self.nutri)
        response = self.client.post(reverse('edit_template', args=[self.template.id]), {
            'name': 'Original', 'daily_kcal': '10000',
        })
        self.assertRedirects(response, reverse('list_templates'))
        self.template.refresh_from_db()
        self.assertEqual(self.template.daily_kcal, 10000)


class EditTemplateIntakeViewTests(TestCase):

    def setUp(self):
        self.nutri = make_nutri('tpl_item1@example.com')
        self.template = make_template(self.nutri, duration=2)

        self.p_main = make_product('Pollo', kcal=200, prot=30, fat=5, carb=0)
        self.p_main_alt = make_product('Ternera', kcal=250, prot=28, fat=15, carb=0)
        self.dish_main = make_dish('Pollo asado', Dish.DishType.MAIN, self.p_main)
        self.dish_main_alt = make_dish('Ternera asada', Dish.DishType.MAIN, self.p_main_alt)

        _, groups = get_meal_structure()
        self.main_intake = groups['comida']['main']

        self.item = TemplateIntake.objects.create(
            template=self.template, dish=None, intake=self.main_intake,
            quantity=0, kcal=Decimal('0'), menu_day=0, intake_alias='Plato principal - Comida',
        )

    def _url(self, item=None):
        item = item or self.item
        return reverse('edit_template_intake', args=[self.template.id, item.id])

    def test_get_returns_options_without_client_exclusions(self):
        # Una plantilla no tiene cliente asociado: no debe haber exclusiones
        # de producto/grupo como las que si aplica Menus._dish_options_for_intake.
        self.client.force_login(self.nutri)
        response = self.client.get(self._url())
        self.assertEqual(response.status_code, 200)
        data = response.json()
        option_ids = {opt['id'] for opt in data['options']}
        self.assertIn(self.dish_main.id, option_ids)
        self.assertIn(self.dish_main_alt.id, option_ids)

    def test_post_assigns_dish_and_recalculates_kcal(self):
        self.client.force_login(self.nutri)
        response = self.client.post(
            self._url(), data=json.dumps({'dish_id': self.dish_main.id, 'quantity': 150}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertAlmostEqual(data['kcal'], 300.0)  # 200 kcal/100g * 150g

        self.item.refresh_from_db()
        self.assertEqual(self.item.dish_id, self.dish_main.id)
        self.assertEqual(self.item.quantity, 150)
        self.assertEqual(self.item.kcal, Decimal('300.00'))
        self.assertFalse(self.item.is_free_meal)

    def test_post_marks_free_meal(self):
        self.client.force_login(self.nutri)
        response = self.client.post(
            self._url(), data=json.dumps({'is_free_meal': True}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsNone(data['dish_id'])
        self.assertTrue(data['is_free_meal'])

        self.item.refresh_from_db()
        self.assertIsNone(self.item.dish_id)
        self.assertEqual(self.item.quantity, 0)
        self.assertEqual(self.item.kcal, Decimal('0'))
        self.assertTrue(self.item.is_free_meal)

    def test_post_rejects_invalid_dish(self):
        self.client.force_login(self.nutri)
        response = self.client.post(
            self._url(), data=json.dumps({'dish_id': 999999, 'quantity': 100}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)

    def test_other_nutri_gets_404(self):
        other_nutri = make_nutri('tpl_item2@example.com')
        self.client.force_login(other_nutri)
        response = self.client.get(self._url())
        self.assertEqual(response.status_code, 404)

    def test_item_from_different_template_returns_404(self):
        other_template = make_template(self.nutri, name='Otra')
        other_item = TemplateIntake.objects.create(
            template=other_template, dish=None, intake=self.main_intake,
            quantity=0, kcal=Decimal('0'), menu_day=0, intake_alias='Plato principal - Comida',
        )
        self.client.force_login(self.nutri)
        url = reverse('edit_template_intake', args=[self.template.id, other_item.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)


class CopyTemplateIntakeViewTests(TestCase):

    def setUp(self):
        self.nutri = make_nutri('tpl_copy1@example.com')
        self.template = make_template(self.nutri, duration=2)
        self.p_main = make_product('Pollo', kcal=200, prot=30, fat=5, carb=0)
        self.dish_main = make_dish('Pollo asado', Dish.DishType.MAIN, self.p_main)

        _, groups = get_meal_structure()
        self.main_comida = groups['comida']['main']
        self.main_cena = groups['cena']['main']

        self.item = TemplateIntake.objects.create(
            template=self.template, dish=self.dish_main, intake=self.main_comida,
            quantity=100, kcal=Decimal('200.00'), menu_day=0, intake_alias='Plato principal - Comida',
        )

    def _url(self, item=None):
        item = item or self.item
        return reverse('copy_template_intake', args=[self.template.id, item.id])

    def test_sibling_with_same_role_is_target_and_source_excluded(self):
        sibling_main = TemplateIntake.objects.create(
            template=self.template, dish=self.dish_main, intake=self.main_cena,
            quantity=120, kcal=Decimal('240.00'), menu_day=0, intake_alias='Plato principal - Cena',
        )
        self.client.force_login(self.nutri)
        response = self.client.get(self._url())
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn(sibling_main.id, data['target_ids'])
        self.assertNotIn(self.item.id, data['target_ids'])

    def test_free_meal_source_targets_every_other_item(self):
        self.item.dish = None
        self.item.quantity = 0
        self.item.kcal = Decimal('0')
        self.item.is_free_meal = True
        self.item.save(update_fields=['dish', 'quantity', 'kcal', 'is_free_meal'])

        sibling_main = TemplateIntake.objects.create(
            template=self.template, dish=self.dish_main, intake=self.main_cena,
            quantity=120, kcal=Decimal('240.00'), menu_day=0, intake_alias='Plato principal - Cena',
        )
        self.client.force_login(self.nutri)
        response = self.client.get(self._url())
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['is_free_meal'])
        self.assertIn(sibling_main.id, data['target_ids'])

    def test_other_nutri_gets_404(self):
        other_nutri = make_nutri('tpl_copy2@example.com')
        self.client.force_login(other_nutri)
        response = self.client.get(self._url())
        self.assertEqual(response.status_code, 404)

    def test_item_from_different_template_returns_404(self):
        other_template = make_template(self.nutri, name='Otra')
        other_item = TemplateIntake.objects.create(
            template=other_template, dish=self.dish_main, intake=self.main_comida,
            quantity=100, kcal=Decimal('200.00'), menu_day=0, intake_alias='Plato principal - Comida',
        )
        self.client.force_login(self.nutri)
        url = reverse('copy_template_intake', args=[self.template.id, other_item.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)


class TemplateLifecycleViewTests(TestCase):

    def setUp(self):
        self.nutri = make_nutri('tpl_life1@example.com')
        self.other_nutri = make_nutri('tpl_life2@example.com')
        self.template = make_template(self.nutri)

    def test_deactivate_then_reactivate_cycle(self):
        self.client.force_login(self.nutri)

        response = self.client.post(reverse('deactivate_template', args=[self.template.id]))
        self.assertRedirects(response, reverse('list_templates'))
        self.template.refresh_from_db()
        self.assertFalse(self.template.active)

        # Ya desactivada: deactivate_template exige active=True, asi que un
        # segundo intento debe dar 404, no un no-op silencioso.
        response = self.client.post(reverse('deactivate_template', args=[self.template.id]))
        self.assertEqual(response.status_code, 404)

        response = self.client.post(reverse('reactivate_template', args=[self.template.id]))
        self.assertRedirects(response, reverse('list_deactivated_templates'))
        self.template.refresh_from_db()
        self.assertTrue(self.template.active)

    def test_delete_requires_deactivated_first(self):
        self.client.force_login(self.nutri)

        response = self.client.post(reverse('delete_template', args=[self.template.id]))
        self.assertEqual(response.status_code, 404)
        self.assertTrue(Template.objects.filter(id=self.template.id).exists())

        self.template.active = False
        self.template.save(update_fields=['active'])

        response = self.client.post(reverse('delete_template', args=[self.template.id]))
        self.assertRedirects(response, reverse('list_deactivated_templates'))
        self.assertFalse(Template.objects.filter(id=self.template.id).exists())

    def test_other_nutri_cannot_deactivate_reactivate_or_delete(self):
        self.client.force_login(self.other_nutri)

        response = self.client.post(reverse('deactivate_template', args=[self.template.id]))
        self.assertEqual(response.status_code, 404)

        self.template.active = False
        self.template.save(update_fields=['active'])

        response = self.client.post(reverse('reactivate_template', args=[self.template.id]))
        self.assertEqual(response.status_code, 404)

        response = self.client.post(reverse('delete_template', args=[self.template.id]))
        self.assertEqual(response.status_code, 404)

        self.assertTrue(Template.objects.filter(id=self.template.id).exists())
