from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('listaProductos/', views.ProductoListView.as_view(), name='lista_productos'),
    path('carritoView/', views.carrito_view, name='carrito_view'),

    path('producto/', views.ProductoListCreateView.as_view()),
    path('producto/<int:pk>/', views.ProductoDetailDeleteView.as_view()),
    path('descuento/', views.DescuentoListCreateView.as_view()),
    path('descuento/<int:pk>/', views.DescuentoDetailDeleteView.as_view()),
    path('carrito/', views.CarritoListCreateView.as_view()),
    path('carrito/<int:pk>/', views.CarritoDetailDeleteView.as_view()),
]