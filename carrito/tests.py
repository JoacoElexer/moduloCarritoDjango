from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse, NoReverseMatch
from .models import Producto, Descuento, Carrito, CarritoProducto

class BaseSetup(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="abraham", password="lol")
        self.client.login(username="abraham", password="lol")
        self.carrito = Carrito.objects.create(usuario=self.user)

class AuthAndPagesTests(BaseSetup):
    # Verifica que la vista de login responde correctamente (200) o redirige (302) si así está configurada.
    def test_login_view_render(self):
        try:
            url = reverse("login")
        except NoReverseMatch:
            url = "/login/"
        resp = self.client.get(url)
        self.assertIn(resp.status_code, (200, 302))

    # Comprueba que acceder a la lista de productos sin autenticación redirige al login (302).
    def test_lista_productos_login_required(self):
        self.client.logout()
        try:
            url = reverse("listaProductos")
        except NoReverseMatch:
            url = "/listaProductos/"
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 302)

    # Comprueba que la vista del carrito requiere autenticación y redirige si no hay sesión (302).
    def test_carrito_view_login_required(self):
        self.client.logout()
        try:
            url = reverse("carritoView")
        except NoReverseMatch:
            url = "/carritoView/"
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 302)

class ModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="u1", password="p")
        self.carrito = Carrito.objects.create(usuario=self.user)

    # Garantiza que solo exista un carrito por usuario (OneToOne), fallando al crear un segundo.
    def test_carrito_unico_por_usuario(self):
        with self.assertRaises(Exception):
            Carrito.objects.create(usuario=self.user)

    # Crea un producto y un item de carrito, y verifica relaciones y cantidad asignada.
    def test_producto_y_relacion_item(self):
        prod = Producto.objects.create(imagen="http://img/1", nombre="Prod1", precio=10.0, stock=3)
        item = CarritoProducto.objects.create(carrito=self.carrito, producto=prod, cantidad=1)
        self.assertEqual(item.carrito, self.carrito)
        self.assertEqual(item.producto, prod)
        self.assertEqual(item.cantidad, 1)