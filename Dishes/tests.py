from django.test import TestCase
from django.urls import reverse

from Dishes.models import Dish, DishProduct
from Intakes.models import Intake
from Products.models import Product
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


class DishEditIsolationTests(TestCase):

    def setUp(self):
        self.nutri_a = make_nutri('nutri_a@example.com')
        self.nutri_b = make_nutri('nutri_b@example.com')
        self.admin = make_nutri('admin@example.com', is_staff=True)
        self.dish = Dish.objects.create(
            name='Plato de A',
            recipe_elaboration='Receta original',
            language='es',
            dish_type=Dish.DishType.MAIN,
            user=self.nutri_a,
        )
        self.url = reverse('edit_dish', args=[self.dish.id])

    def test_other_nutritionist_cannot_get_edit_dish(self):
        self.client.force_login(self.nutri_b)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 404)

    def test_other_nutritionist_cannot_post_edit_dish(self):
        self.client.force_login(self.nutri_b)
        response = self.client.post(self.url, {
            'recipe_name': 'Plato secuestrado por B',
            'description': 'Texto de B',
            'dish_type': Dish.DishType.DESSERT,
        })
        self.assertEqual(response.status_code, 404)

        self.dish.refresh_from_db()
        self.assertEqual(self.dish.name, 'Plato de A')
        self.assertEqual(self.dish.recipe_elaboration, 'Receta original')
        self.assertEqual(self.dish.dish_type, Dish.DishType.MAIN)

    def test_owner_can_get_edit_dish(self):
        self.client.force_login(self.nutri_a)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_staff_can_get_edit_dish(self):
        self.client.force_login(self.admin)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)


def make_product(name, user=None):
    return Product.objects.create(
        food_name=name,
        food_name_spanish=name,
        food_name_eng=name,
        origin_db='test',
        ed_porc=100,
        kcal_100g=100,
        prot_g=1,
        ch_g=1,
        fat_g=1,
        user=user,
    )


class DishEditBehaviorTests(TestCase):

    def setUp(self):
        self.nutri = make_nutri('nutri@example.com')
        self.admin = make_nutri('admin2@example.com', is_staff=True)
        self.intake_old = Intake.objects.create(name='Comida', order=1)
        self.intake_new = Intake.objects.create(name='Cena', order=2)
        self.old_product = make_product('Arroz')
        self.new_product = make_product('Pollo', user=self.nutri)

        self.shared = Dish.objects.create(
            name='Plato compartido',
            recipe_elaboration='Receta compartida',
            language='es',
            dish_type=Dish.DishType.MAIN,
            user=None,
        )
        self.shared.intakes.set([self.intake_old])
        DishProduct.objects.create(dish=self.shared, product=self.old_product, quantity=100)

        self.own = Dish.objects.create(
            name='Plato propio',
            recipe_elaboration='Receta propia',
            language='es',
            user=self.nutri,
        )

    def post_data(self, name):
        return {
            'recipe_name': name,
            'description': 'Nueva descripcion',
            'dish_type': Dish.DishType.DESSERT,
            'intakes': [self.intake_new.id],
            'ingredient_product_id': [self.new_product.id],
            'ingredient_quantity': ['250'],
        }

    def test_owner_post_edits_in_place(self):
        self.client.force_login(self.nutri)
        response = self.client.post(
            reverse('edit_dish', args=[self.own.id]), self.post_data('Plato propio editado')
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Dish.objects.count(), 2)
        self.own.refresh_from_db()
        self.assertEqual(self.own.name, 'Plato propio editado')
        self.assertEqual(self.own.user, self.nutri)
        self.assertEqual(self.own.dishproduct_set.get().product, self.new_product)

    def test_non_admin_can_get_edit_shared_dish(self):
        self.client.force_login(self.nutri)
        response = self.client.get(reverse('edit_dish', args=[self.shared.id]))
        self.assertEqual(response.status_code, 200)

    def test_non_admin_post_on_shared_dish_creates_personal_copy(self):
        self.client.force_login(self.nutri)
        response = self.client.post(
            reverse('edit_dish', args=[self.shared.id]), self.post_data('Mi copia')
        )
        self.assertEqual(response.status_code, 302)

        # Original intacto
        self.shared.refresh_from_db()
        self.assertEqual(self.shared.name, 'Plato compartido')
        self.assertEqual(self.shared.recipe_elaboration, 'Receta compartida')
        self.assertEqual(self.shared.dish_type, Dish.DishType.MAIN)
        self.assertIsNone(self.shared.user)
        self.assertEqual(list(self.shared.intakes.all()), [self.intake_old])
        original_row = self.shared.dishproduct_set.get()
        self.assertEqual(original_row.product, self.old_product)
        self.assertEqual(original_row.quantity, 100)

        # Exactamente una copia nueva del nutricionista
        copies = Dish.objects.filter(user=self.nutri, name='Mi copia')
        self.assertEqual(copies.count(), 1)
        self.assertEqual(Dish.objects.count(), 3)
        copy = copies.get()
        self.assertNotEqual(copy.id, self.shared.id)
        self.assertTrue(copy.active)
        self.assertEqual(copy.language, 'es')
        self.assertEqual(copy.dish_type, Dish.DishType.DESSERT)
        self.assertEqual(list(copy.intakes.all()), [self.intake_new])
        copy_row = copy.dishproduct_set.get()
        self.assertEqual(copy_row.product, self.new_product)
        self.assertEqual(copy_row.quantity, 250)

    def test_staff_post_on_shared_dish_edits_in_place(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse('edit_dish', args=[self.shared.id]), self.post_data('Compartido editado')
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Dish.objects.count(), 2)
        self.shared.refresh_from_db()
        self.assertEqual(self.shared.name, 'Compartido editado')
        self.assertIsNone(self.shared.user)
        self.assertEqual(self.shared.dishproduct_set.get().product, self.new_product)


class DishEditOutOfScopeIngredientTests(TestCase):
    """Ingredientes ya presentes en la receta fuera del scope del editor."""

    def setUp(self):
        self.nutri = make_nutri('nutri_oos@example.com')
        self.other = make_nutri('other_oos@example.com')
        self.staff = make_nutri('staff_oos@example.com', is_staff=True)
        self.own_product = make_product('Propio', user=self.nutri)
        self.other_private = make_product('Privado ajeno', user=self.other)
        self.staff_private = make_product('Privado staff', user=self.staff)
        self.own_dish = Dish.objects.create(
            name='Plato propio', recipe_elaboration='x', language='es', user=self.nutri)

    def _post(self, dish, product_ids, name='Editado'):
        return self.client.post(reverse('edit_dish', args=[dish.id]), {
            'recipe_name': name,
            'description': 'Desc',
            'dish_type': Dish.DishType.MAIN,
            'ingredient_product_id': [p.id for p in product_ids],
            'ingredient_quantity': ['100'] * len(product_ids),
        })

    def test_existing_out_of_scope_ingredient_is_kept_on_edit(self):
        DishProduct.objects.create(dish=self.own_dish, product=self.other_private, quantity=50)
        self.client.force_login(self.nutri)
        response = self._post(self.own_dish, [self.other_private, self.own_product])
        self.assertEqual(response.status_code, 302)
        self.own_dish.refresh_from_db()
        self.assertEqual(self.own_dish.name, 'Editado')
        self.assertEqual(
            set(self.own_dish.dishproduct_set.values_list('product_id', flat=True)),
            {self.other_private.id, self.own_product.id},
        )

    def test_new_out_of_scope_ingredient_is_not_added_on_edit(self):
        self.client.force_login(self.nutri)
        response = self._post(self.own_dish, [self.other_private, self.own_product])
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            list(self.own_dish.dishproduct_set.values_list('product_id', flat=True)),
            [self.own_product.id],
        )

    def test_shared_dish_copy_keeps_staff_private_ingredient(self):
        shared = Dish.objects.create(
            name='Compartido', recipe_elaboration='x', language='es', user=None)
        DishProduct.objects.create(dish=shared, product=self.staff_private, quantity=70)
        self.client.force_login(self.nutri)
        response = self._post(shared, [self.staff_private], name='Mi copia')
        self.assertEqual(response.status_code, 302)

        copy = Dish.objects.get(user=self.nutri, name='Mi copia')
        self.assertNotEqual(copy.id, shared.id)
        self.assertEqual(
            list(copy.dishproduct_set.values_list('product_id', flat=True)),
            [self.staff_private.id],
        )
        shared.refresh_from_db()
        self.assertEqual(shared.name, 'Compartido')
        self.assertIsNone(shared.user)
        row = shared.dishproduct_set.get()
        self.assertEqual(row.product, self.staff_private)
        self.assertEqual(row.quantity, 70)


class DishStateChangeIsolationTests(TestCase):

    def setUp(self):
        self.owner = make_nutri('owner@example.com')
        self.other = make_nutri('other@example.com')
        self.admin = make_nutri('admin3@example.com', is_staff=True)
        self.active_dish = Dish.objects.create(
            name='Activo de A', recipe_elaboration='x', language='es', user=self.owner
        )
        self.inactive_dish = Dish.objects.create(
            name='Inactivo de A', recipe_elaboration='x', language='es',
            user=self.owner, active=False,
        )
        self.shared_active = Dish.objects.create(
            name='Compartido activo', recipe_elaboration='x', language='es', user=None
        )
        self.shared_inactive = Dish.objects.create(
            name='Compartido inactivo', recipe_elaboration='x', language='es',
            user=None, active=False,
        )

    def post(self, name, dish):
        return self.client.post(reverse(name, args=[dish.id]))

    def assert_state(self, dish, active):
        dish.refresh_from_db()
        self.assertEqual(dish.active, active)

    def test_other_nutritionist_cannot_change_dish_state(self):
        self.client.force_login(self.other)
        self.assertEqual(self.post('deactivate_dish', self.active_dish).status_code, 404)
        self.assertEqual(self.post('reactivate_dish', self.inactive_dish).status_code, 404)
        self.assertEqual(self.post('delete_dish', self.inactive_dish).status_code, 404)
        self.assert_state(self.active_dish, True)
        self.assert_state(self.inactive_dish, False)

    def test_non_admin_cannot_change_shared_dish_state(self):
        self.client.force_login(self.owner)
        self.assertEqual(self.post('deactivate_dish', self.shared_active).status_code, 404)
        self.assertEqual(self.post('reactivate_dish', self.shared_inactive).status_code, 404)
        self.assertEqual(self.post('delete_dish', self.shared_inactive).status_code, 404)
        self.assert_state(self.shared_active, True)
        self.assert_state(self.shared_inactive, False)

    def test_owner_can_deactivate_reactivate_and_delete(self):
        self.client.force_login(self.owner)
        self.assertEqual(self.post('deactivate_dish', self.active_dish).status_code, 302)
        self.assert_state(self.active_dish, False)
        self.assertEqual(self.post('reactivate_dish', self.active_dish).status_code, 302)
        self.assert_state(self.active_dish, True)
        self.assertEqual(self.post('delete_dish', self.inactive_dish).status_code, 302)
        self.assertFalse(Dish.objects.filter(id=self.inactive_dish.id).exists())

    def test_staff_can_deactivate_shared_dish(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.post('deactivate_dish', self.shared_active).status_code, 302)
        self.assert_state(self.shared_active, False)



class DishListVisibilityTests(TestCase):
    """Listados renderizados: platos compartidos (user=NULL) y boton Desactivar."""

    def setUp(self):
        self.nutri = make_nutri('list_nutri@example.com')
        self.admin = make_nutri('list_admin@example.com', is_staff=True)
        make = lambda name, user, active: Dish.objects.create(
            name=name, recipe_elaboration='', language='es',
            dish_type=Dish.DishType.MAIN, user=user, active=active,
        )
        self.shared_active = make('CompartidoActivoXYZ', None, True)
        self.own_active = make('PropioActivoXYZ', self.nutri, True)
        self.shared_inactive = make('CompartidoInactivoXYZ', None, False)
        self.own_inactive = make('PropioInactivoXYZ', self.nutri, False)

    def _deactivate_url(self, dish):
        return reverse('deactivate_dish', args=[dish.id])

    def test_non_staff_deactivated_list_hides_shared_and_shows_own(self):
        self.client.force_login(self.nutri)
        response = self.client.get(reverse('list_deactive_dishes'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'PropioInactivoXYZ')
        self.assertNotContains(response, 'CompartidoInactivoXYZ')

    def test_staff_deactivated_list_includes_shared(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('list_deactive_dishes'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'CompartidoInactivoXYZ')

    def test_non_staff_active_list_shows_shared_without_deactivate_form(self):
        self.client.force_login(self.nutri)
        response = self.client.get(reverse('list_active_dishes'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'CompartidoActivoXYZ')
        self.assertContains(response, 'PropioActivoXYZ')
        self.assertNotContains(response, self._deactivate_url(self.shared_active))
        self.assertContains(response, self._deactivate_url(self.own_active))

    def test_staff_active_list_has_deactivate_form_for_shared(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('list_active_dishes'))
        self.assertContains(response, self._deactivate_url(self.shared_active))
