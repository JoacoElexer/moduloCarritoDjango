from django.http import JsonResponse, HttpResponseNotAllowed
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, get_object_or_404
from .models import Producto, Descuento, Carrito, CarritoProducto
from django.views import View
from django.utils.decorators import method_decorator
from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin


def login_view(request):
    return render(request, 'login/login.html')

class ProductoListView(LoginRequiredMixin, ListView):
    model = Producto
    template_name = 'listaProductos.html'
    context_object_name = 'productos'

def carrito_view(request):
    carrito = Carrito.objects.first()
    return render(request, 'carritoView.html', {'carrito': carrito})

@method_decorator(csrf_exempt, name='dispatch')
class ProductoListCreateView(View):
    def get(self, request):
        data = list(Producto.objects.values())
        return JsonResponse(data, safe=False)

    def post(self, request):
        nombre = request.POST.get('nombre')
        imagen = request.POST.get('imagen')
        precio = float(request.POST.get('precio', 0))
        stock = int(request.POST.get('stock', 0))
        p = Producto.objects.create(nombre=nombre, imagen=imagen, precio=precio, stock=stock)
        return JsonResponse({'id': p.id})

@method_decorator(csrf_exempt, name='dispatch')
class ProductoDetailDeleteView(View):
    def get(self, request, pk):
        p = get_object_or_404(Producto, pk=pk)
        return JsonResponse({'id': p.id, 'nombre': p.nombre, 'imagen': p.imagen, 'precio': p.precio, 'stock': p.stock})

    def delete(self, request, pk):
        p = get_object_or_404(Producto, pk=pk)
        p.delete()
        return JsonResponse({'deleted': True})

@method_decorator(csrf_exempt, name='dispatch')
class DescuentoListCreateView(View):
    def get(self, request):
        return JsonResponse(list(Descuento.objects.values()), safe=False)

    def post(self, request):
        codigo = request.POST.get('codigo')
        porcentaje = float(request.POST.get('porcentaje', 0))
        d = Descuento.objects.create(codigo=codigo, porcentaje=porcentaje)
        return JsonResponse({'id': d.id})

@method_decorator(csrf_exempt, name='dispatch')
class DescuentoDetailDeleteView(View):
    def get(self, request, pk):
        d = get_object_or_404(Descuento, pk=pk)
        return JsonResponse({'id': d.id, 'codigo': d.codigo, 'porcentaje': d.porcentaje})

    def delete(self, request, pk):
        d = get_object_or_404(Descuento, pk=pk)
        d.delete()
        return JsonResponse({'deleted': True})

@method_decorator(csrf_exempt, name='dispatch')
class CarritoListCreateView(View):
    def get(self, request):
        return JsonResponse(list(Carrito.objects.values()), safe=False)

    def post(self, request):
        c = Carrito.objects.create(precio_total=0)
        return JsonResponse({'id': c.id})

@method_decorator(csrf_exempt, name='dispatch')
class CarritoDetailDeleteView(View):
    def get(self, request, pk):
        c = get_object_or_404(Carrito, pk=pk)
        items = CarritoProducto.objects.filter(carrito=c).values('producto_id', 'cantidad')
        descs = c.descuentos.values('codigo', 'porcentaje')
        return JsonResponse({'id': c.id, 'precio_total': c.precio_total, 'items': list(items), 'descuentos': list(descs)})

    def delete(self, request, pk):
        c = get_object_or_404(Carrito, pk=pk)
        c.delete()
        return JsonResponse({'deleted': True})