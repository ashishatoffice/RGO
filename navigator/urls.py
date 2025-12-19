from django.urls import path
from . import views

urlpatterns = [
    path('', views.landing_page, name='landing'),
    path('navigate/', views.navigation_view, name='navigate'),
    path('sparql/', views.sparql_view, name='sparql'),
    path('details/', views.node_details, name='node_details'),
]
