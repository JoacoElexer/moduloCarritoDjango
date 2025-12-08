from django.urls import path
from . import views

urlpatterns = [
    # URL para el inicio de sesión del usuario
    path('login/', views.login_view, name='login'),

    # URL para listar todos los productos
    path('listaProductos/', views.ProductoListView.as_view(), name='lista_productos'),

    # URL para visualizar el carrito de compras
    path('carritoView/', views.carrito_view, name='carrito_view'),

    # URL para crear y listar productos
    path('producto/', views.ProductoListCreateView.as_view()),

    # URL para obtener y eliminar un producto específico por su ID
    path('producto/<int:pk>/', views.ProductoDetailDeleteView.as_view()),

    # URL para crear y listar descuentos
    path('descuento/', views.DescuentoListCreateView.as_view()),

    # URL para obtener y eliminar un descuento específico por su ID
    path('descuento/<int:pk>/', views.DescuentoDetailDeleteView.as_view()),

    # URL para crear y listar carritos de compras
    path('carrito/', views.CarritoListCreateView.as_view()),

    # URL para obtener y eliminar un carrito de compras específico por su ID
    path('carrito/<int:pk>/', views.CarritoDetailDeleteView.as_view()),

    # URL para actualizar un artículo en un carrito de compras específico
    path('carrito/<int:pk>/item/<int:item_id>/update/', views.CarritoItemUpdateView.as_view()),

    # URL para eliminar un artículo de un carrito de compras específico
    path('carrito/<int:pk>/item/<int:item_id>/delete/', views.CarritoItemDeleteView.as_view()),

    # URL para aplicar un cupón a un carrito de compras específico
    path('carrito/<int:pk>/aplicar-cupon/', views.CarritoApplyCouponView.as_view(), name='aplicar_cupon'),

    # URL para vaciar un carrito de compras específico
    path('carrito/<int:pk>/vaciar/', views.VaciarCarritoView.as_view(), name='vaciar_carrito'),

    # URL para finalizar la compra de un carrito de compras específico
    path('carrito/<int:pk>/finalizar/', views.FinalizarCompraView.as_view(), name='finalizar_compra'),

    # URL para quitar un cupón de un carrito de compras específico
    path('carrito/<int:pk>/quitar-cupon/', views.CarritoRemoveCouponView.as_view(), name='quitar_cupon'),
]