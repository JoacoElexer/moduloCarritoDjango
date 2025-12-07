from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, get_object_or_404
from .models import Producto, Descuento, Carrito, CarritoProducto
from django.views import View
from django.utils.decorators import method_decorator
from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.views.decorators.http import require_http_methods


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
    items_qs = CarritoProducto.objects.filter(carrito=carrito).select_related('producto')
    items = []
    total = 0.0
    for it in items_qs:
        subtotal = it.producto.precio * it.cantidad
        items.append({
            'id': it.id,
            'nombre': it.producto.nombre,
            'imagen': it.producto.imagen,
            'precio': it.producto.precio,
            'cantidad': it.cantidad,
            'subtotal': subtotal,
        })
        total += subtotal

    # Actualiza precio_total si quieres mantenerlo consistente
    if carrito:
        carrito.precio_total = total
        carrito.save(update_fields=['precio_total'])

    return render(request, 'carrito.html', {
        'carrito': carrito,
        'items': items,
        'total': total,
        'descuentos': list(carrito.descuentos.all()) if carrito else [],
    })

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
        if not request.user.is_authenticated:
            return HttpResponseForbidden()
        carrito = _ensure_user_cart(request.user)
        return JsonResponse({'id': carrito.id, 'usuario': request.user.id})

    def post(self, request):
        return HttpResponseForbidden()
    
@method_decorator(csrf_exempt, name='dispatch')
class CarritoItemUpdateView(View):
    @transaction.atomic
    def post(self, request, pk, item_id):
        if not request.user.is_authenticated:
            return HttpResponseForbidden()
        carrito = get_object_or_404(Carrito, pk=pk)
        if carrito.usuario != request.user:
            return HttpResponseForbidden()

        # Parse new quantity
        try:
            nueva_cantidad = int(request.POST.get('cantidad', '').strip())
        except (TypeError, ValueError):
            return JsonResponse({'error': 'Cantidad inválida'}, status=400)

        item = get_object_or_404(CarritoProducto.objects.select_for_update(), pk=item_id, carrito=carrito)
        producto = Producto.objects.select_for_update().get(pk=item.producto_id)

        if nueva_cantidad < 1:
            # Equivalent to delete logic below, but here we treat <1 as remove
            producto.stock += item.cantidad
            producto.save(update_fields=['stock'])
            item.delete()
            # Recompute total
            total = 0.0
            for it in CarritoProducto.objects.filter(carrito=carrito).select_related('producto'):
                total += it.producto.precio * it.cantidad
            carrito.precio_total = total
            carrito.save(update_fields=['precio_total'])
            return JsonResponse({'ok': True, 'removed': True, 'stock_restante': producto.stock, 'total': total})

        # Determine delta and check stock when increasing
        delta = nueva_cantidad - item.cantidad
        if delta > 0:
            if producto.stock < delta:
                return JsonResponse({'error': 'Stock insuficiente', 'stock_disponible': producto.stock}, status=400)
            producto.stock -= delta
        elif delta < 0:
            producto.stock += (-delta)

        producto.save(update_fields=['stock'])

        item.cantidad = nueva_cantidad
        item.save(update_fields=['cantidad'])

        # Recompute total
        total = 0.0
        for it in CarritoProducto.objects.filter(carrito=carrito).select_related('producto'):
            total += it.producto.precio * it.cantidad
        carrito.precio_total = total
        carrito.save(update_fields=['precio_total'])

        return JsonResponse({
            'ok': True,
            'item_id': item.id,
            'cantidad': item.cantidad,
            'stock_restante': producto.stock,
            'subtotal': round(producto.precio * item.cantidad, 2),
            'total': round(total, 2),
        })

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

    @transaction.atomic
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

        try:
            p = Producto.objects.select_for_update().get(pk=producto_id)
        except Producto.DoesNotExist:
            return JsonResponse({'error': 'Producto no existe'}, status=404)

        if p.stock < cantidad:
            return JsonResponse({'error': 'Stock insuficiente', 'stock_disponible': p.stock}, status=400)

        item, created = CarritoProducto.objects.get_or_create(
            carrito=c, producto=p, defaults={'cantidad': cantidad}
        )
        if not created:
            item.cantidad += cantidad
            item.save(update_fields=['cantidad'])

        p.stock -= cantidad
        p.save(update_fields=['stock'])

        return JsonResponse({
            'ok': True,
            'carrito_id': c.id,
            'producto_id': p.id,
            'cantidad_total': item.cantidad,
            'stock_restante': p.stock
        })
    
@method_decorator(csrf_exempt, name='dispatch')
class CarritoItemDeleteView(View):
    @transaction.atomic
    def delete(self, request, pk, item_id):
        if not request.user.is_authenticated:
            return HttpResponseForbidden()
        carrito = get_object_or_404(Carrito, pk=pk)
        if carrito.usuario != request.user:
            return HttpResponseForbidden()

        item = get_object_or_404(CarritoProducto.objects.select_for_update(), pk=item_id, carrito=carrito)
        producto = Producto.objects.select_for_update().get(pk=item.producto_id)

        # Restore stock fully
        producto.stock += item.cantidad
        producto.save(update_fields=['stock'])

        item.delete()

        # Recompute total
        total = 0.0
        for it in CarritoProducto.objects.filter(carrito=carrito).select_related('producto'):
            total += it.producto.precio * it.cantidad
        carrito.precio_total = total
        carrito.save(update_fields=['precio_total'])

        return JsonResponse({'ok': True, 'deleted': True, 'stock_restante': producto.stock, 'total': round(total, 2)})