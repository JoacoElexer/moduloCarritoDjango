from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, get_object_or_404
from .models import Producto, Descuento, Carrito, CarritoProducto
from django.views import View
from django.utils.decorators import method_decorator
from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required

def login_view(request):
    return render(request, 'login/login.html')

def _ensure_user_cart(user):
    carrito, _ = Carrito.objects.get_or_create(usuario=user, defaults={'precio_total': 0})
    return carrito

class ProductoListView(LoginRequiredMixin, ListView):
    model = Producto
    template_name = 'listaProductos.html'
    context_object_name = 'productos'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        carrito = _ensure_user_cart(self.request.user)
        ctx['carrito_id'] = carrito.id
        return ctx

@login_required
def carrito_view(request):
    carrito = Carrito.objects.filter(usuario=request.user).first()
    return render(request, 'carrito.html', {'carrito': carrito})

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
        # Solo lista el carrito del usuario autenticado
        if not request.user.is_authenticated:
            return HttpResponseForbidden()
        carrito = _ensure_user_cart(request.user)
        return JsonResponse({'id': carrito.id, 'usuario': request.user.id})

    def post(self, request):
        # No crear carritos arbitrarios; cada usuario tiene uno
        return HttpResponseForbidden()

@method_decorator(csrf_exempt, name='dispatch')
class CarritoDetailDeleteView(View):
    def get(self, request, pk):
        if not request.user.is_authenticated:
            return HttpResponseForbidden()
        c = get_object_or_404(Carrito, pk=pk)
        if c.usuario != request.user:
            return HttpResponseForbidden()
        items = CarritoProducto.objects.filter(carrito=c).values('producto_id', 'cantidad')
        descs = c.descuentos.values('codigo', 'porcentaje')
        return JsonResponse({'id': c.id, 'precio_total': c.precio_total, 'items': list(items), 'descuentos': list(descs)})

    def delete(self, request, pk):
        if not request.user.is_authenticated:
            return HttpResponseForbidden()
        c = get_object_or_404(Carrito, pk=pk)
        if c.usuario != request.user:
            return HttpResponseForbidden()
        c.delete()
        return JsonResponse({'deleted': True})

    def post(self, request, pk):
        if not request.user.is_authenticated:
            return HttpResponseForbidden()
        c = get_object_or_404(Carrito, pk=pk)
        if c.usuario != request.user:
            return HttpResponseForbidden()

        try:
            producto_id = int(request.POST.get('producto_id', '0'))
            cantidad = int(request.POST.get('cantidad', '0'))
        except ValueError:
            return JsonResponse({'error': 'Datos inválidos'}, status=400)

        if cantidad < 1:
            return JsonResponse({'error': 'Cantidad debe ser >= 1'}, status=400)

        p = get_object_or_404(Producto, pk=producto_id)

        item, created = CarritoProducto.objects.get_or_create(
            carrito=c, producto=p, defaults={'cantidad': cantidad}
        )
        if not created:
            item.cantidad += cantidad
            item.save(update_fields=['cantidad'])

        return JsonResponse({'ok': True, 'carrito_id': c.id, 'producto_id': p.id, 'cantidad_total': item.cantidad})