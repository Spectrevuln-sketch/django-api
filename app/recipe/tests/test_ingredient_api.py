from decimal import Decimal
from django.contrib.auth  import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from core.models import (
    Ingredient,
    Recipe
)

from recipe.serializers import IngredientSerializer


INGREDIENTS_URL = reverse('recipe:ingredient-list')


def detail_url(ingredient_id):
    return reverse('recipe:ingredient-detail', args=[ingredient_id])

def create_user(email= 'user@example.com', password='test123'):
    return get_user_model().objects.create_user(email, password)


class PublicIngredientsTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(INGREDIENTS_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

class PrivateIngredientsTests(TestCase):
    def setUp(self):
        self.user = create_user()
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_retriveIngredients_auth(self):
        Ingredient.objects.create(
            user= self.user,
            name= 'Ingredient1'
        )
        Ingredient.objects.create(
            user= self.user,
            name= 'Ingredient2'
        )

        res = self.client.get(INGREDIENTS_URL)
        ingredients = Ingredient.objects.all().order_by('-name')
        serializer = IngredientSerializer(ingredients, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_ingredient_limit_to_user(self):
        user2 = create_user(email= 'user2@example.com')
        Ingredient.objects.create(
            user= user2,
            name= 'Vanilla'
        )
        new_ingredient = Ingredient.objects.create( user= self.user, name='Coklat')

        res = self.client.get(INGREDIENTS_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['name'], new_ingredient.name)
        self.assertEqual(res.data[0]['id'], new_ingredient.id)

    def test_update_ingredient(self):
        ingredient = Ingredient.objects.create(
            user= self.user,
            name= 'Vanilla',
        )

        payload = {
            'name': 'Coklat',
        }

        url = detail_url(ingredient_id= ingredient.id)
        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        ingredient.refresh_from_db()
        self.assertEqual(ingredient.name, payload['name'])

    def test_delete_ingredient(self):
        ingredient = Ingredient.objects.create(
            user= self.user,
            name = 'Vanilla',
        )

        url = detail_url(ingredient.id)
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        get_ingredient = Ingredient.objects.filter(user= self.user)
        self.assertFalse(get_ingredient.exists())
        self.assertFalse(Ingredient.objects.filter(name='Vanilla').exists())

    def test_filter_ingredients_assigned_to_recipes(self):
        in1 = Ingredient.objects.create(user= self.user, name='Apple')
        in2 = Ingredient.objects.create(user= self.user, name='Turkey')
        recipe = Recipe.objects.create(
            title= 'Apple Crumble',
            time_minutes= 5,
            price=Decimal('4.50'),
            user= self.user
        )
        recipe.ingredients.add(in1)
        res = self.client.get(INGREDIENTS_URL, {'assigned_only': 1})

        s1 = IngredientSerializer(in1)
        s2 = IngredientSerializer(in2)
        self.assertIn(s1.data, res.data)
        self.assertNotIn(s2.data, res.data)

    def test_filter_ingredients_unique(self):
        ing = Ingredient.objects.create(user= self.user, name='Eggs')
        Ingredient.objects.create(user= self.user, name='Lentils')

        recipe1 = Recipe.objects.create(
            user=self.user,
            title='Eggs Bendict',
            time_minutes=60,
            price=Decimal('7.00')
        )
        recipe2 = Recipe.objects.create(
            user=self.user,
            title='Herb Eggs',
            time_minutes=60,
            price=Decimal('4.00'),
        )
        recipe1.ingredients.add(ing)
        recipe2.ingredients.add(ing)

        res = self.client.get(INGREDIENTS_URL, {'assigned_only': 1})

        self.assertEqual(len(res.data), 1)