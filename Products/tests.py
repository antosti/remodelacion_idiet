from django.test import TestCase
from django.urls import reverse

from Dishes.models import Dish, DishProduct
from decimal import Decimal

from Micronutrients.models import Micronutrient
from Products.models import Product, ProductMicronutrient
from SuperGroup.models import SuperGroup
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


def make_product(name, user=None, is_active=True, ed_porc=100):
    return Product.objects.create(
        food_name=name,
        food_name_spanish=name,
        food_name_eng=name,
        origin_db='test',
        ed_porc=ed_porc,
        kcal_100g=100,
        prot_g=1,
        ch_g=1,
        fat_g=1,
        user=user,
        is_active=is_active,
    )


class ProductIsolationTests(TestCase):
    """Otro nutricionista no debe poder leer/mutar productos privados de A."""

    def setUp(self):
        self.nutri_a = make_nutri('nutri_a@example.com')
        self.nutri_b = make_nutri('nutri_b@example.com')
        self.admin = make_nutri('admin@example.com', is_staff=True)
        self.active_a = make_product('Producto activo de A', user=self.nutri_a)
        self.inactive_a = make_product(
            'Producto inactivo de A', user=self.nutri_a, is_active=False
        )

    def test_other_nutritionist_cannot_get_edit_food(self):
        self.client.force_login(self.nutri_b)
        response = self.client.get(reverse('edit_food', args=[self.active_a.id]))
        self.assertEqual(response.status_code, 404)

    def test_other_nutritionist_cannot_post_edit_food(self):
        self.client.force_login(self.nutri_b)
        response = self.client.post(reverse('edit_food', args=[self.active_a.id]), {
            'name': 'Secuestrado por B',
            'english_name': 'Hijacked',
            'kcal_100g': '999',
            'proteins': '1',
            'hydrates': '1',
            'fats': '1',
        })
        self.assertEqual(response.status_code, 404)

        self.active_a.refresh_from_db()
        self.assertEqual(self.active_a.food_name_spanish, 'Producto activo de A')
        self.assertEqual(self.active_a.kcal_100g, 100)

    def test_other_nutritionist_cannot_deactivate_food(self):
        self.client.force_login(self.nutri_b)
        response = self.client.post(reverse('deactivate_food', args=[self.active_a.id]))
        self.active_a.refresh_from_db()
        self.assertTrue(self.active_a.is_active)
        self.assertEqual(response.status_code, 404)

    def test_other_nutritionist_cannot_reactivate_food(self):
        self.client.force_login(self.nutri_b)
        response = self.client.post(reverse('reactivate_food', args=[self.inactive_a.id]))
        self.inactive_a.refresh_from_db()
        self.assertFalse(self.inactive_a.is_active)
        self.assertEqual(response.status_code, 404)

    def test_other_nutritionist_cannot_delete_food(self):
        self.client.force_login(self.nutri_b)
        response = self.client.post(reverse('delete_food', args=[self.inactive_a.id]))
        self.assertTrue(Product.objects.filter(id=self.inactive_a.id).exists())
        self.assertEqual(response.status_code, 404)

    def test_bulk_deactivate_only_affects_own_products(self):
        own_b = make_product('Producto de B', user=self.nutri_b)
        self.client.force_login(self.nutri_b)
        self.client.post(reverse('deactivate_foods_bulk'), {
            'selected_foods': [self.active_a.id, own_b.id],
        })
        self.active_a.refresh_from_db()
        own_b.refresh_from_db()
        self.assertTrue(self.active_a.is_active)
        self.assertFalse(own_b.is_active)

    def test_bulk_reactivate_only_affects_own_products(self):
        own_b = make_product('Producto de B', user=self.nutri_b, is_active=False)
        self.client.force_login(self.nutri_b)
        self.client.post(reverse('reactivate_foods_bulk'), {
            'selected_foods': [self.inactive_a.id, own_b.id],
        })
        self.inactive_a.refresh_from_db()
        own_b.refresh_from_db()
        self.assertFalse(self.inactive_a.is_active)
        self.assertTrue(own_b.is_active)

    def test_bulk_delete_only_affects_own_products(self):
        own_b = make_product('Producto de B', user=self.nutri_b, is_active=False)
        self.client.force_login(self.nutri_b)
        self.client.post(reverse('delete_foods_bulk'), {
            'selected_foods': [self.inactive_a.id, own_b.id],
        })
        self.assertTrue(Product.objects.filter(id=self.inactive_a.id).exists())
        self.assertFalse(Product.objects.filter(id=own_b.id).exists())

    def test_owner_can_get_edit_food(self):
        self.client.force_login(self.nutri_a)
        response = self.client.get(reverse('edit_food', args=[self.active_a.id]))
        self.assertEqual(response.status_code, 200)

    def test_staff_can_get_edit_food(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('edit_food', args=[self.active_a.id]))
        self.assertEqual(response.status_code, 200)

    def test_other_nutritionist_cannot_use_private_product_in_dish(self):
        own_b = make_product('Producto de B', user=self.nutri_b)
        self.client.force_login(self.nutri_b)
        self.client.post(reverse('create_dish'), {
            'recipe_name': 'Plato de B',
            'description': 'Texto',
            'dish_type': Dish.DishType.MAIN,
            'ingredient_product_id': [self.active_a.id, own_b.id],
            'ingredient_quantity': ['100', '100'],
        })
        dish = Dish.objects.get(name='Plato de B', user=self.nutri_b)
        self.assertFalse(
            DishProduct.objects.filter(dish=dish, product=self.active_a).exists()
        )
        self.assertTrue(
            DishProduct.objects.filter(dish=dish, product=own_b).exists()
        )


class SharedProductEditTests(TestCase):
    """Un no-admin editando un producto compartido (user=NULL) crea una copia propia."""

    def setUp(self):
        self.nutri = make_nutri('nutri@example.com')
        self.admin = make_nutri('admin@example.com', is_staff=True)
        self.shared = make_product('Compartido', user=None, ed_porc=85)
        self.super_group = SuperGroup.objects.create(name='SG original')
        self.shared.super_groups.add(self.super_group)
        # 5 y 6 estan en el formulario; 69 no se expone en el formulario.
        for mid in (5, 6, 69):
            Micronutrient.objects.get_or_create(id=mid, defaults={'name': f'Micro {mid}'})
        ProductMicronutrient.objects.create(
            product=self.shared, micronutrient_id=5, value=Decimal('1.50'))
        ProductMicronutrient.objects.create(
            product=self.shared, micronutrient_id=6, value=Decimal('2.50'))
        ProductMicronutrient.objects.create(
            product=self.shared, micronutrient_id=69, value=Decimal('7.25'))

    def _post_data(self, **extra):
        data = {
            'name': 'Editado por usuario',
            'english_name': 'Edited',
            'kcal_100g': '321',
            'proteins': '3',
            'hydrates': '4',
            'fats': '5',
            'micronutrient_5': '9.00',
            'micronutrient_6': '0',
        }
        data.update(extra)
        return data

    def _micro_values(self, product):
        return {
            pm.micronutrient_id: pm.value
            for pm in ProductMicronutrient.objects.filter(product=product)
        }

    def test_non_admin_edit_creates_personal_copy(self):
        self.client.force_login(self.nutri)
        before = Product.objects.count()
        response = self.client.post(
            reverse('edit_food', args=[self.shared.id]),
            self._post_data(super_group=[]),
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Product.objects.count(), before + 1)

        self.shared.refresh_from_db()
        self.assertEqual(self.shared.food_name_spanish, 'Compartido')
        self.assertEqual(self.shared.kcal_100g, 100)
        self.assertIsNone(self.shared.user_id)
        self.assertEqual(self.shared.origin_db, 'test')
        self.assertEqual(
            list(self.shared.super_groups.values_list('id', flat=True)),
            [self.super_group.id],
        )
        self.assertEqual(self._micro_values(self.shared), {
            5: Decimal('1.50'), 6: Decimal('2.50'), 69: Decimal('7.25'),
        })

        copy = Product.objects.exclude(id=self.shared.id).get(user=self.nutri)
        self.assertEqual(copy.food_name_spanish, 'Editado por usuario')
        self.assertEqual(copy.kcal_100g, 321)
        self.assertEqual(self.shared.ed_porc, 85)
        self.assertEqual(copy.ed_porc, self.shared.ed_porc)
        self.assertEqual(copy.origin_db, 'Editado')
        self.assertTrue(copy.is_active)
        self.assertEqual(copy.super_groups.count(), 0)
        # 5 actualizado, 6 borrado (0), 69 (no expuesto) conserva el original.
        self.assertEqual(self._micro_values(copy), {
            5: Decimal('9.00'), 69: Decimal('7.25'),
        })

    def test_non_admin_can_get_edit_shared_food(self):
        self.client.force_login(self.nutri)
        response = self.client.get(reverse('edit_food', args=[self.shared.id]))
        self.assertEqual(response.status_code, 200)

    def test_non_admin_copy_takes_super_groups_from_post(self):
        other = SuperGroup.objects.create(name='SG nuevo')
        self.client.force_login(self.nutri)
        self.client.post(
            reverse('edit_food', args=[self.shared.id]),
            self._post_data(super_group=[other.id]),
        )
        copy = Product.objects.get(user=self.nutri)
        self.assertEqual(
            list(copy.super_groups.values_list('id', flat=True)), [other.id])

    def test_staff_edits_shared_product_in_place(self):
        self.client.force_login(self.admin)
        before = Product.objects.count()
        response = self.client.post(
            reverse('edit_food', args=[self.shared.id]), self._post_data())
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Product.objects.count(), before)
        self.shared.refresh_from_db()
        self.assertEqual(self.shared.food_name_spanish, 'Editado por usuario')
        self.assertIsNone(self.shared.user_id)
        self.assertEqual(self._micro_values(self.shared), {
            5: Decimal('9.00'), 69: Decimal('7.25'),
        })

    def test_owner_edits_own_product_in_place(self):
        own = make_product('Propio', user=self.nutri)
        self.client.force_login(self.nutri)
        before = Product.objects.count()
        response = self.client.post(
            reverse('edit_food', args=[own.id]), self._post_data())
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Product.objects.count(), before)
        own.refresh_from_db()
        self.assertEqual(own.food_name_spanish, 'Editado por usuario')
        self.assertEqual(own.user_id, self.nutri.id)


class SharedProductMutationTests(TestCase):
    """Los productos compartidos solo los puede desactivar/eliminar un admin."""

    def setUp(self):
        self.nutri = make_nutri('nutri@example.com')
        self.admin = make_nutri('admin@example.com', is_staff=True)
        self.shared_active = make_product('Compartido activo', user=None)
        self.shared_inactive = make_product(
            'Compartido inactivo', user=None, is_active=False)
        self.own_active = make_product('Propio activo', user=self.nutri)
        self.own_inactive = make_product(
            'Propio inactivo', user=self.nutri, is_active=False)

    def test_non_admin_cannot_deactivate_shared_food(self):
        self.client.force_login(self.nutri)
        response = self.client.post(
            reverse('deactivate_food', args=[self.shared_active.id]))
        self.assertEqual(response.status_code, 404)
        self.shared_active.refresh_from_db()
        self.assertTrue(self.shared_active.is_active)

    def test_non_admin_cannot_reactivate_or_delete_shared_food(self):
        self.client.force_login(self.nutri)
        r1 = self.client.post(
            reverse('reactivate_food', args=[self.shared_inactive.id]))
        r2 = self.client.post(
            reverse('delete_food', args=[self.shared_inactive.id]))
        self.assertEqual(r1.status_code, 404)
        self.assertEqual(r2.status_code, 404)
        self.shared_inactive.refresh_from_db()
        self.assertFalse(self.shared_inactive.is_active)

    def test_bulk_actions_ignore_shared_ids_for_non_admin(self):
        self.client.force_login(self.nutri)
        self.client.post(reverse('deactivate_foods_bulk'), {
            'selected_foods': [self.shared_active.id, self.own_active.id]})
        self.client.post(reverse('reactivate_foods_bulk'), {
            'selected_foods': [self.shared_inactive.id, self.own_inactive.id]})
        self.shared_active.refresh_from_db()
        self.shared_inactive.refresh_from_db()
        self.own_active.refresh_from_db()
        self.own_inactive.refresh_from_db()
        self.assertTrue(self.shared_active.is_active)
        self.assertFalse(self.shared_inactive.is_active)
        self.assertFalse(self.own_active.is_active)
        self.assertTrue(self.own_inactive.is_active)

    def test_bulk_delete_ignores_shared_ids_for_non_admin(self):
        self.client.force_login(self.nutri)
        self.client.post(reverse('delete_foods_bulk'), {
            'selected_foods': [self.shared_inactive.id]})
        self.assertTrue(Product.objects.filter(id=self.shared_inactive.id).exists())

    def test_staff_can_deactivate_shared_food(self):
        self.client.force_login(self.admin)
        self.client.post(reverse('deactivate_food', args=[self.shared_active.id]))
        self.shared_active.refresh_from_db()
        self.assertFalse(self.shared_active.is_active)

    def test_deactive_list_excludes_shared_for_non_staff(self):
        self.client.force_login(self.nutri)
        response = self.client.get(reverse('list_deactive_foods'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Propio inactivo')
        self.assertNotContains(response, 'Compartido inactivo')

    def test_deactive_list_includes_shared_for_staff(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('list_deactive_foods'))
        self.assertContains(response, 'Compartido inactivo')
        self.assertContains(response, 'Propio inactivo')

    def test_active_list_hides_controls_for_shared_for_non_staff(self):
        self.client.force_login(self.nutri)
        response = self.client.get(reverse('list_active_foods'))
        self.assertContains(response, 'Compartido activo')
        self.assertNotContains(
            response, reverse('deactivate_food', args=[self.shared_active.id]))
        self.assertContains(
            response, reverse('deactivate_food', args=[self.own_active.id]))
        self.assertContains(response, f'data-food-id="{self.own_active.id}"')
        self.assertNotContains(
            response, f'data-food-id="{self.shared_active.id}"')

    def test_active_list_shows_controls_for_shared_for_staff(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('list_active_foods'))
        self.assertContains(
            response, reverse('deactivate_food', args=[self.shared_active.id]))
        self.assertContains(
            response, f'data-food-id="{self.shared_active.id}"')

    def test_non_admin_can_use_shared_product_in_dish(self):
        self.client.force_login(self.nutri)
        self.client.post(reverse('create_dish'), {
            'recipe_name': 'Plato con compartido',
            'description': 'Texto',
            'dish_type': Dish.DishType.MAIN,
            'ingredient_product_id': [self.shared_active.id],
            'ingredient_quantity': ['100'],
        })
        dish = Dish.objects.get(name='Plato con compartido', user=self.nutri)
        self.assertTrue(
            DishProduct.objects.filter(dish=dish, product=self.shared_active).exists())
