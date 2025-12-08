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
from django.db.models import Sum
from django.contrib.auth import logout
from django.shortcuts import redirect

def login_view(request):
    return render(request, 'login/login.html')

def logout_view(request):
    """Cerrar sesión del usuario y redirigir a la página de inicio de sesión."""
    logout(request)
    return redirect('login')

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
        cart_count = carrito.items.aggregate(total=Sum('cantidad'))['total'] or 0
        ctx['cart_count'] = cart_count
        applied_coupons = carrito.descuentos.values_list('id', flat=True)
        ctx['descuentos'] = Descuento.objects.exclude(id__in=applied_coupons)
        return ctx

@login_required
def carrito_view(request):
    carrito = Carrito.objects.filter(usuario=request.user).first()
    items_qs = CarritoProducto.objects.filter(carrito=carrito).select_related('producto')
    items = []
    base_total = 0.0
    for it in items_qs:
        subtotal = it.producto.precio * it.cantidad
        # Calcular el stock restante dinámicamente
        stock_restante = it.producto.stock + it.cantidad
        items.append({
            'id': it.id,
            'nombre': it.producto.nombre,
            'imagen': it.producto.imagen,
            'precio': it.producto.precio,
            'cantidad': it.cantidad,
            'subtotal': subtotal,
            'stock_restante': stock_restante,  # Enviar el stock restante al frontend
        })
        base_total += subtotal

    descuentos_qs = carrito.descuentos.all() if carrito else Descuento.objects.none()
    total_pct = descuentos_qs.aggregate(total=Sum('porcentaje'))['total'] or 0.0
    discounted_total = max(0.0, base_total * (1 - float(total_pct) / 100.0))

    if carrito:
        carrito.precio_total = base_total
        carrito.save(update_fields=['precio_total'])

    return render(request, 'carrito.html', {
        'carrito': carrito,
        'items': items,
        'total': discounted_total,
        'descuentos': list(descuentos_qs),
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

        try:
            nueva_cantidad = int(request.POST.get('cantidad', 1))
        except (TypeError, ValueError):
            return JsonResponse({'error': 'Cantidad inválida'}, status=400)

        item = get_object_or_404(CarritoProducto.objects.select_for_update(), pk=item_id, carrito=carrito)
        producto = Producto.objects.select_for_update().get(pk=item.producto_id)

        # Verificar que la nueva cantidad no exceda el stock disponible
        if nueva_cantidad > item.cantidad + producto.stock:
            nueva_cantidad = item.cantidad + producto.stock

        if nueva_cantidad < 1:
            item.delete()
        else:
            producto.stock += item.cantidad - nueva_cantidad
            producto.save(update_fields=['stock'])
            item.cantidad = nueva_cantidad
            item.save(update_fields=['cantidad'])

        base_total = 0.0
        for it in CarritoProducto.objects.filter(carrito=carrito).select_related('producto'):
            base_total += it.producto.precio * it.cantidad
        carrito.precio_total = base_total
        carrito.save(update_fields=['precio_total'])

        total_pct = carrito.descuentos.aggregate(total=Sum('porcentaje'))['total'] or 0.0
        discounted_total = max(0.0, base_total * (1 - float(total_pct) / 100.0))

        return JsonResponse({
            'ok': True,
            'item_id': item.id,
            'cantidad': item.cantidad,
            'stock_restante': producto.stock,
            'subtotal': round(producto.precio * item.cantidad, 2),
            'total': round(discounted_total, 2),
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

        base_total = 0.0
        for it in CarritoProducto.objects.filter(carrito=c).select_related('producto'):
            base_total += it.producto.precio * it.cantidad
        c.precio_total = base_total
        c.save(update_fields=['precio_total'])

        total_pct = c.descuentos.aggregate(total=Sum('porcentaje'))['total'] or 0.0
        discounted_total = max(0.0, base_total * (1 - float(total_pct) / 100.0))

        return JsonResponse({
            'ok': True,
            'carrito_id': c.id,
            'producto_id': p.id,
            'cantidad_total': item.cantidad,
            'stock_restante': p.stock,
            'total': round(discounted_total, 2),
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

        producto.stock += item.cantidad
        producto.save(update_fields=['stock'])

        item.delete()

        base_total = 0.0
        for it in CarritoProducto.objects.filter(carrito=carrito).select_related('producto'):
            base_total += it.producto.precio * it.cantidad
        carrito.precio_total = base_total
        carrito.save(update_fields=['precio_total'])

        total_pct = carrito.descuentos.aggregate(total=Sum('porcentaje'))['total'] or 0.0
        discounted_total = max(0.0, base_total * (1 - float(total_pct) / 100.0))

        return JsonResponse({'ok': True, 'deleted': True, 'stock_restante': producto.stock, 'total': round(discounted_total, 2)})

@method_decorator(csrf_exempt, name='dispatch')
class CarritoApplyCouponView(View):
    @transaction.atomic
    def post(self, request, pk):
        if not request.user.is_authenticated:
            return HttpResponseForbidden()
        carrito = get_object_or_404(Carrito, pk=pk)
        if carrito.usuario != request.user:
            return HttpResponseForbidden()

        codigo = (request.POST.get('codigo') or '').strip()
        if not codigo:
            return JsonResponse({'error': 'Ingresa un código'}, status=400)

        try:
            descuento = Descuento.objects.get(codigo__iexact=codigo)
        except Descuento.DoesNotExist:
            return JsonResponse({'error': 'Código inválido'}, status=404)

        # Evitar duplicados
        if carrito.descuentos.filter(pk=descuento.pk).exists():
            base_total = 0.0
            for it in CarritoProducto.objects.filter(carrito=carrito).select_related('producto'):
                base_total += it.producto.precio * it.cantidad
            total_pct = carrito.descuentos.aggregate(total=Sum('porcentaje'))['total'] or 0.0
            discounted_total = max(0.0, base_total * (1 - float(total_pct) / 100.0))
            descs = list(carrito.descuentos.values('codigo', 'porcentaje'))
            return JsonResponse({
                'ok': True,
                'aplicado': {'codigo': descuento.codigo, 'porcentaje': descuento.porcentaje},
                'descuentos': descs,
                'base_total': round(base_total, 2),
                'total': round(discounted_total, 2)
            })

        carrito.descuentos.add(descuento)

        base_total = 0.0
        for it in CarritoProducto.objects.filter(carrito=carrito).select_related('producto'):
            base_total += it.producto.precio * it.cantidad

        total_pct = carrito.descuentos.aggregate(total=Sum('porcentaje'))['total'] or 0.0
        discounted_total = max(0.0, base_total * (1 - float(total_pct) / 100.0))

        carrito.precio_total = base_total
        carrito.save(update_fields=['precio_total'])

        descs = list(carrito.descuentos.values('codigo', 'porcentaje'))
        return JsonResponse({
            'ok': True,
            'aplicado': {'codigo': descuento.codigo, 'porcentaje': descuento.porcentaje},
            'descuentos': descs,
            'base_total': round(base_total, 2),
            'total': round(discounted_total, 2)
        })

    @transaction.atomic
    def delete(self, request, pk):
        if not request.user.is_authenticated:
            return HttpResponseForbidden()
        carrito = get_object_or_404(Carrito, pk=pk)
        if carrito.usuario != request.user:
            return HttpResponseForbidden()

        codigo = (request.GET.get('codigo') or '').strip()
        if not codigo:
            return JsonResponse({'error': 'Ingresa un código'}, status=400)

        try:
            descuento = Descuento.objects.get(codigo__iexact=codigo)
        except Descuento.DoesNotExist:
            return JsonResponse({'error': 'Código inválido'}, status=404)

        carrito.descuentos.remove(descuento)

        base_total = 0.0
        for it in CarritoProducto.objects.filter(carrito=carrito).select_related('producto'):
            base_total += it.producto.precio * it.cantidad

        total_pct = carrito.descuentos.aggregate(total=Sum('porcentaje'))['total'] or 0.0
        discounted_total = max(0.0, base_total * (1 - float(total_pct) / 100.0))

        carrito.precio_total = base_total
        carrito.save(update_fields=['precio_total'])

        descs = list(carrito.descuentos.values('codigo', 'porcentaje'))
        return JsonResponse({
            'ok': True,
            'removido': {'codigo': descuento.codigo, 'porcentaje': descuento.porcentaje},
            'descuentos': descs,
            'base_total': round(base_total, 2),
            'total': round(discounted_total, 2)
        })
    
@method_decorator(csrf_exempt, name='dispatch')
class VaciarCarritoView(View):
    @transaction.atomic
    def post(self, request, pk):
        if not request.user.is_authenticated:
            return HttpResponseForbidden()
        carrito = get_object_or_404(Carrito, pk=pk)
        if carrito.usuario != request.user:
            return HttpResponseForbidden()

        # Regresar los productos al stock
        for item in CarritoProducto.objects.filter(carrito=carrito).select_related('producto'):
            item.producto.stock += item.cantidad
            item.producto.save(update_fields=['stock'])
        CarritoProducto.objects.filter(carrito=carrito).delete()

        # Eliminar los descuentos aplicados
        carrito.descuentos.clear()

        # Actualizar el total del carrito
        carrito.precio_total = 0.0
        carrito.save(update_fields=['precio_total'])

        return JsonResponse({'ok': True, 'total': 0.0})
    
@method_decorator(csrf_exempt, name='dispatch')
class FinalizarCompraView(View):
    @transaction.atomic
    def post(self, request, pk):
        if not request.user.is_authenticated:
            return HttpResponseForbidden()
        carrito = get_object_or_404(Carrito, pk=pk)
        if carrito.usuario != request.user:
            return HttpResponseForbidden()

        # Eliminar los productos del carrito sin regresar al stock
        CarritoProducto.objects.filter(carrito=carrito).delete()

        carrito.precio_total = 0.0
        carrito.save(update_fields=['precio_total'])

        return JsonResponse({'ok': True})
    
@method_decorator(csrf_exempt, name='dispatch')
class CarritoRemoveCouponView(View):
    @transaction.atomic
    def post(self, request, pk):
        carrito = get_object_or_404(Carrito, pk=pk, usuario=request.user)
        codigo = request.POST.get('codigo')

        if not codigo:
            return JsonResponse({'error': 'Código de cupón no proporcionado.'}, status=400)

        descuento = carrito.descuentos.filter(codigo=codigo).first()
        if not descuento:
            return JsonResponse({'error': 'Cupón no encontrado en el carrito.'}, status=404)

        carrito.descuentos.remove(descuento)

        # Recalcular el total
        base_total = sum(item.producto.precio * item.cantidad for item in carrito.items.all())
        total_pct = carrito.descuentos.aggregate(total=Sum('porcentaje'))['total'] or 0.0
        discounted_total = max(0.0, base_total * (1 - float(total_pct) / 100.0))

        carrito.precio_total = discounted_total
        carrito.save(update_fields=['precio_total'])

        return JsonResponse({'total': discounted_total})