from django.contrib import admin
from .models import Producto, Descuento, Carrito, CarritoProducto

# Register your models here.

admin.site.register(Producto) 
admin.site.register(Descuento)
admin.site.register(Carrito)
admin.site.register(CarritoProducto)