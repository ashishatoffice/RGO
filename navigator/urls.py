from django.urls import path
from . import views

urlpatterns = [
    path('', views.landing_page, name='landing'),
    path('navigate/', views.navigation_view, name='navigate'),
    path('navigate/inferred/', views.inferred_navigation_view, name='navigate_inferred'),
    path('navigate/events/', views.events_navigation_view, name='navigate_events'),
    path('sparql/', views.sparql_view, name='sparql'),
    path('details/', views.node_details, name='node_details'),
]
