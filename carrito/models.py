from django.db import models

# Create your models here.

class Producto(models.Model):
    imagen = models.URLField(max_length=500)
    nombre = models.CharField(max_length=100)
    precio = models.FloatField()
    stock = models.IntegerField()

    def __str__(self):
        return self.nombre

class Descuento(models.Model):
    codigo = models.CharField(max_length=100, unique=True)
    porcentaje = models.FloatField()

    def __str__(self):
        return f"{self.codigo} ({self.porcentaje}%)"

class Carrito(models.Model): 
    descuentos = models.ManyToManyField(Descuento, blank=True)
    precio_total = models.FloatField(default=0.0)

    def __str__(self):
        return f"Carrito #{self.id}"

class CarritoProducto(models.Model):
    carrito = models.ForeignKey(Carrito, on_delete=models.CASCADE, related_name='items')
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    cantidad = models.IntegerField(default=1)

    class Meta:
        unique_together = ('carrito', 'producto')