import json
from datetime import date
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from Clients.models import Client
from Dishes.models import Dish, DishProduct
from Menus.generator.domain import DietConfig, MealSlotConfig, NutritionTarget
from Menus.generator.ga import generate_day
from Menus.generator.meal_structure import get_meal_structure
from Menus.generator.persistence import persist_generated_diet
from Menus.generator.pools import build_candidate_pools
from Menus.generator.service import GenerationError, generate_diet
from Menus.models import Menu, MenuIntake
from Products.models import Product, ProductExcluded
from Users.models import User


def make_nutri(email):
    return User.objects.create_user(username=email, email=email, password='x', first_name='T', last_name='U')


def make_client(user):
    return Client.objects.create(
        user=user, email='cliente@example.com', first_name='Cli', last_name='Ente',
        birth_date=date(1990, 1, 1), gender='Male', height=180, weight='80.00',
        dni='00000000A', phone_number='600000000', phone_number_2='', address='',
        postal_code='', city='', activity_level='Moderada',
    )


def make_product(name, kcal, prot, fat, carb):
    return Product.objects.create(
        food_name=name, food_name_spanish=name, food_name_eng=name, origin_db='test',
        ed_porc=100, kcal_100g=kcal, prot_g=prot, ch_g=carb, fat_g=fat,
    )


def make_dish(name, dish_type, product, quantity=200, user=None):
    dish = Dish.objects.create(name=name, recipe_elaboration='', language='es', dish_type=dish_type, user=user)
    DishProduct.objects.create(dish=dish, product=product, quantity=quantity)
    return dish


class DietGeneratorTests(TestCase):

    def setUp(self):
        self.nutri = make_nutri('nutri@example.com')
        self.client_obj = make_client(self.nutri)

        self.p_main = make_product('Pollo', kcal=200, prot=30, fat=5, carb=0)
        self.p_starter = make_product('Ensalada', kcal=50, prot=2, fat=1, carb=5)
        self.p_dessert = make_product('Fruta', kcal=60, prot=1, fat=0, carb=15)
        self.p_excluded = make_product('Marisco', kcal=150, prot=20, fat=3, carb=0)

        self.dish_main = make_dish('Pollo asado', Dish.DishType.MAIN, self.p_main)
        self.dish_starter = make_dish('Ensalada verde', Dish.DishType.STARTER, self.p_starter)
        self.dish_dessert = make_dish('Macedonia', Dish.DishType.DESSERT, self.p_dessert)
        self.dish_excluded_main = make_dish('Paella de marisco', Dish.DishType.MAIN, self.p_excluded)

        _, groups = get_meal_structure()
        self.comida = groups['comida']
        self.target = NutritionTarget(kcal=800, prot_g=60, fat_g=25, carb_g=80)

    def _slot(self, include_starter=True, include_dessert=True):
        return MealSlotConfig(
            key='group-comida', label='Comida', kind='group', intakes=self.comida,
            include_starter=include_starter, include_dessert=include_dessert,
        )

    def test_generate_day_respects_structure(self):
        slot = self._slot()
        pools = build_candidate_pools(self.client_obj, self.nutri, [slot])
        day, _history = generate_day(pools, [slot], self.target, None, pop_size=6, n_generations=5)

        courses = day[slot.key]
        self.assertIn('starter', courses)
        self.assertIn('main', courses)
        self.assertIn('dessert', courses)
        self.assertIsNotNone(courses['starter'])
        self.assertIsNotNone(courses['main'])
        self.assertIsNotNone(courses['dessert'])

    def test_no_starter_or_dessert_when_not_requested(self):
        slot = self._slot(include_starter=False, include_dessert=False)
        pools = build_candidate_pools(self.client_obj, self.nutri, [slot])
        day, _history = generate_day(pools, [slot], self.target, None, pop_size=6, n_generations=5)

        courses = day[slot.key]
        self.assertNotIn('starter', courses)
        self.assertNotIn('dessert', courses)
        self.assertIsNotNone(courses['main'])

    def test_excluded_product_never_appears_in_pool(self):
        ProductExcluded.objects.create(client=self.client_obj, product=self.p_excluded)
        slot = self._slot(include_starter=False, include_dessert=False)
        pools = build_candidate_pools(self.client_obj, self.nutri, [slot])

        main_ids = {candidate.dish_id for candidate in pools[slot.key]['main']}
        self.assertNotIn(self.dish_excluded_main.id, main_ids)
        self.assertIn(self.dish_main.id, main_ids)

    def test_dish_owned_by_other_nutri_not_in_pool(self):
        other_nutri = make_nutri('otro@example.com')
        other_dish = make_dish('Pollo del otro nutri', Dish.DishType.MAIN, self.p_main, user=other_nutri)

        slot = self._slot(include_starter=False, include_dessert=False)
        pools = build_candidate_pools(self.client_obj, self.nutri, [slot])

        main_ids = {candidate.dish_id for candidate in pools[slot.key]['main']}
        self.assertNotIn(other_dish.id, main_ids)
        self.assertIn(self.dish_main.id, main_ids)  # el global (sin user) si es visible

    def test_dish_owned_by_other_nutri_visible_to_admin(self):
        admin = make_nutri('admin@example.com')
        admin.is_staff = True
        admin.save()
        other_nutri = make_nutri('otro2@example.com')
        other_dish = make_dish('Pollo del otro nutri 2', Dish.DishType.MAIN, self.p_main, user=other_nutri)

        slot = self._slot(include_starter=False, include_dessert=False)
        pools = build_candidate_pools(self.client_obj, admin, [slot])

        main_ids = {candidate.dish_id for candidate in pools[slot.key]['main']}
        self.assertIn(other_dish.id, main_ids)

    def test_max_portion_grams_is_respected(self):
        slot = self._slot(include_starter=False, include_dessert=False)
        pools = build_candidate_pools(self.client_obj, self.nutri, [slot])
        day, _history = generate_day(pools, [slot], self.target, max_portion_grams=50, pop_size=6, n_generations=5)

        _candidate, qty = day[slot.key]['main']
        self.assertLessEqual(qty, 50)

    def test_generate_diet_multi_day(self):
        slot = self._slot(include_starter=False, include_dessert=False)
        config = DietConfig(days=3, start_date=date(2026, 9, 1), meal_slots=[slot], target=self.target)
        days = generate_diet(self.client_obj, self.nutri, config)

        self.assertEqual(len(days), 3)
        for day in days:
            self.assertIsNotNone(day[slot.key]['main'])

    def test_generation_error_when_no_dishes_available(self):
        Dish.objects.all().delete()
        slot = self._slot(include_starter=False, include_dessert=False)
        config = DietConfig(days=1, start_date=date(2026, 9, 1), meal_slots=[slot], target=self.target)

        with self.assertRaises(GenerationError):
            generate_diet(self.client_obj, self.nutri, config)

    def test_persist_generated_diet(self):
        slot = self._slot(include_starter=False, include_dessert=False)
        config = DietConfig(days=2, start_date=date(2026, 9, 1), meal_slots=[slot], target=self.target)
        days = generate_diet(self.client_obj, self.nutri, config)

        menu = persist_generated_diet(self.nutri, self.client_obj, config, days)

        self.assertEqual(menu.client_id, self.client_obj.id)
        self.assertEqual(menu.date_ini, date(2026, 9, 1))
        self.assertEqual(menu.date_fin, date(2026, 9, 2))

        rows = MenuIntake.objects.filter(menu=menu)
        self.assertEqual(rows.count(), 2)
        self.assertEqual(set(rows.values_list('menu_day', flat=True)), {0, 1})


class CreateDietViewTests(TestCase):

    def setUp(self):
        self.nutri1 = make_nutri('nutri1@example.com')
        self.nutri2 = make_nutri('nutri2@example.com')
        self.client1 = make_client(self.nutri1)

        product = make_product('Pollo', kcal=200, prot=30, fat=5, carb=0)
        make_dish('Pollo asado', Dish.DishType.MAIN, product)

    def test_nutri_can_generate_diet_for_own_client(self):
        self.client.force_login(self.nutri1)
        response = self.client.post(reverse('create_diet', args=[self.client1.id]), {
            'days': '2',
            'start_date': '2026-09-01',
            'include_comida': 'on',
            'platos_comida': '1',
        })

        self.assertRedirects(response, reverse('client_detail', args=[self.client1.id]))
        menu = Menu.objects.get(client=self.client1)
        self.assertEqual(menu.user_id, self.nutri1.id)
        self.assertEqual(MenuIntake.objects.filter(menu=menu).count(), 2)

    def test_other_nutricionista_cannot_access(self):
        self.client.force_login(self.nutri2)
        response = self.client.get(reverse('create_diet', args=[self.client1.id]))
        self.assertEqual(response.status_code, 404)

    def test_invalid_days_shows_error_without_creating_menu(self):
        self.client.force_login(self.nutri1)
        response = self.client.post(reverse('create_diet', args=[self.client1.id]), {
            'days': '0',
            'start_date': '2026-09-01',
            'include_comida': 'on',
            'platos_comida': '1',
        })

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Menu.objects.filter(client=self.client1).exists())

    def test_generation_error_shows_message_without_creating_menu(self):
        Dish.objects.all().delete()
        self.client.force_login(self.nutri1)
        response = self.client.post(reverse('create_diet', args=[self.client1.id]), {
            'days': '1',
            'start_date': '2026-09-01',
            'include_comida': 'on',
            'platos_comida': '1',
        })

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Menu.objects.filter(client=self.client1).exists())


class EditMenuIntakeViewTests(TestCase):

    def setUp(self):
        self.nutri = make_nutri('nutri3@example.com')
        self.client_obj = make_client(self.nutri)

        self.p_main = make_product('Pollo', kcal=200, prot=30, fat=5, carb=0)
        self.p_main_alt = make_product('Ternera', kcal=250, prot=28, fat=15, carb=0)

        self.dish_main = make_dish('Pollo asado', Dish.DishType.MAIN, self.p_main)
        self.dish_main_alt = make_dish('Ternera asada', Dish.DishType.MAIN, self.p_main_alt)

        _, groups = get_meal_structure()
        self.main_intake = groups['comida']['main']

        self.menu = Menu.objects.create(
            user=self.nutri, client=self.client_obj,
            date_ini=date(2026, 9, 1), date_fin=date(2026, 9, 1),
        )
        self.item = MenuIntake.objects.create(
            menu=self.menu, dish=self.dish_main, intake=self.main_intake,
            quantity=100, kcal=Decimal('200.00'), menu_day=0,
            intake_alias='Plato principal - Comida',
        )

    def _url(self, item=None):
        item = item or self.item
        return reverse('edit_menu_intake', args=[self.client_obj.id, self.menu.id, item.id])

    def test_get_returns_current_state_and_options(self):
        self.client.force_login(self.nutri)
        response = self.client.get(self._url())

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['dish_id'], self.dish_main.id)
        self.assertEqual(data['quantity'], 100)
        option_ids = {opt['id'] for opt in data['options']}
        self.assertIn(self.dish_main.id, option_ids)
        self.assertIn(self.dish_main_alt.id, option_ids)

    def test_post_updates_dish_quantity_and_kcal_without_touching_other_rows(self):
        other_item = MenuIntake.objects.create(
            menu=self.menu, dish=self.dish_main, intake=self.main_intake,
            quantity=150, kcal=Decimal('300.00'), menu_day=0,
            intake_alias='Otros',
        )

        self.client.force_login(self.nutri)
        response = self.client.post(
            self._url(), data=json.dumps({'dish_id': self.dish_main_alt.id, 'quantity': 150}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['dish_name'], 'Ternera asada')
        self.assertEqual(data['quantity'], 150)
        self.assertAlmostEqual(data['kcal'], 375.0)  # 250 kcal/100g * 150g
        self.assertAlmostEqual(data['day_kcal'], 375.0 + 300.0)

        self.item.refresh_from_db()
        self.assertEqual(self.item.dish_id, self.dish_main_alt.id)
        self.assertEqual(self.item.quantity, 150)

        other_item.refresh_from_db()
        self.assertEqual(other_item.dish_id, self.dish_main.id)
        self.assertEqual(other_item.quantity, 150)

    def test_post_rejects_invalid_dish(self):
        self.client.force_login(self.nutri)
        response = self.client.post(
            self._url(), data=json.dumps({'dish_id': 999999, 'quantity': 100}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)

    def test_other_nutri_cannot_edit(self):
        other_nutri = make_nutri('otro3@example.com')
        self.client.force_login(other_nutri)
        response = self.client.get(self._url())
        self.assertEqual(response.status_code, 404)


class DeleteMenuViewTests(TestCase):

    def setUp(self):
        self.nutri = make_nutri('nutri5@example.com')
        self.client_obj = make_client(self.nutri)
        self.menu = Menu.objects.create(
            user=self.nutri, client=self.client_obj,
            date_ini=date(2026, 9, 1), date_fin=date(2026, 9, 1),
        )

    def _url(self, menu=None):
        menu = menu or self.menu
        return reverse('delete_menu', args=[self.client_obj.id, menu.id])

    def test_nutri_can_delete_own_client_menu(self):
        self.client.force_login(self.nutri)
        response = self.client.post(self._url())

        self.assertRedirects(response, reverse('client_diets', args=[self.client_obj.id]))
        self.assertFalse(Menu.objects.filter(id=self.menu.id).exists())

    def test_get_not_allowed(self):
        self.client.force_login(self.nutri)
        response = self.client.get(self._url())

        self.assertEqual(response.status_code, 405)
        self.assertTrue(Menu.objects.filter(id=self.menu.id).exists())

    def test_other_nutri_cannot_delete(self):
        other_nutri = make_nutri('otro5@example.com')
        self.client.force_login(other_nutri)
        response = self.client.post(self._url())

        self.assertEqual(response.status_code, 404)
        self.assertTrue(Menu.objects.filter(id=self.menu.id).exists())


class RegenerateMenuViewTests(TestCase):

    def setUp(self):
        self.nutri = make_nutri('nutri4@example.com')
        self.client_obj = make_client(self.nutri)

        self.p_main = make_product('Pollo', kcal=200, prot=30, fat=5, carb=0)
        self.dish_main = make_dish('Pollo asado', Dish.DishType.MAIN, self.p_main)

        _, groups = get_meal_structure()
        self.comida = groups['comida']
        self.target = NutritionTarget(kcal=800, prot_g=60, fat_g=25, carb_g=80)

        self.slot = MealSlotConfig(
            key='group-comida', label='Comida', kind='group', intakes=self.comida,
            include_starter=False, include_dessert=False,
        )
        self.config = DietConfig(days=1, start_date=date(2026, 9, 1), meal_slots=[self.slot], target=self.target)
        days = generate_diet(self.client_obj, self.nutri, self.config)
        self.menu = persist_generated_diet(self.nutri, self.client_obj, self.config, days)
        self.item = MenuIntake.objects.get(menu=self.menu, intake_alias='Plato principal - Comida')

    def _url(self, menu=None):
        menu = menu or self.menu
        return reverse('regenerate_menu', args=[self.client_obj.id, menu.id])

    def test_regenerate_deletes_old_menu_and_creates_new_one(self):
        self.client.force_login(self.nutri)
        old_menu_id = self.menu.id
        response = self.client.post(self._url())

        self.assertFalse(Menu.objects.filter(id=old_menu_id).exists())
        new_menu = Menu.objects.get(client=self.client_obj)
        self.assertNotEqual(new_menu.id, old_menu_id)
        self.assertRedirects(response, reverse('diet_detail', args=[self.client_obj.id, new_menu.id]))
        self.assertTrue(MenuIntake.objects.filter(menu=new_menu).exists())

    def test_regenerate_keeps_locked_dish_and_quantity_in_place(self):
        self.item.quantity = 33
        self.item.save(update_fields=['quantity'])

        self.client.force_login(self.nutri)
        self.client.post(self._url(), {'locked_items': [self.item.id]})

        new_menu = Menu.objects.get(client=self.client_obj)
        new_item = MenuIntake.objects.get(menu=new_menu, menu_day=0, intake_alias='Plato principal - Comida')
        self.assertEqual(new_item.dish_id, self.dish_main.id)
        self.assertEqual(new_item.quantity, 33)

    def test_regenerate_without_config_uses_menu_daily_kcal_as_target(self):
        # Simula una dieta antigua sin generation_config, cuyo objetivo real
        # (1200 kcal/dia) es muy distinto del que calcularia por defecto
        # default_target_for_client para este cliente de prueba.
        self.item.kcal = Decimal('1200.00')
        self.item.quantity = 600
        self.item.save(update_fields=['kcal', 'quantity'])
        self.menu.generation_config = None
        self.menu.save(update_fields=['generation_config'])

        self.client.force_login(self.nutri)
        self.client.post(self._url())

        new_menu = Menu.objects.get(client=self.client_obj)
        new_item = MenuIntake.objects.get(menu=new_menu, menu_day=0, intake_alias='Plato principal - Comida')
        self.assertEqual(new_item.quantity, 600)
        self.assertAlmostEqual(float(new_item.kcal), 1200.0, delta=1)

    def test_regenerate_works_for_legacy_menu_without_generation_config(self):
        # Simula una dieta generada antes de que existiera Menu.generation_config.
        self.menu.generation_config = None
        self.menu.save(update_fields=['generation_config'])

        self.client.force_login(self.nutri)
        old_menu_id = self.menu.id
        response = self.client.post(self._url())

        self.assertFalse(Menu.objects.filter(id=old_menu_id).exists())
        new_menu = Menu.objects.get(client=self.client_obj)
        self.assertRedirects(response, reverse('diet_detail', args=[self.client_obj.id, new_menu.id]))
        self.assertTrue(MenuIntake.objects.filter(menu=new_menu).exists())

    def test_menu_without_any_intakes_cannot_regenerate(self):
        plain_menu = Menu.objects.create(
            user=self.nutri, client=self.client_obj,
            date_ini=date(2026, 9, 5), date_fin=date(2026, 9, 5),
        )
        self.client.force_login(self.nutri)
        response = self.client.post(self._url(plain_menu))

        self.assertRedirects(response, reverse('diet_detail', args=[self.client_obj.id, plain_menu.id]))
        self.assertTrue(Menu.objects.filter(id=plain_menu.id).exists())

    def test_other_nutri_cannot_regenerate(self):
        other_nutri = make_nutri('otro4@example.com')
        self.client.force_login(other_nutri)
        response = self.client.post(self._url())
        self.assertEqual(response.status_code, 404)
