from django.urls import path
from . import views

app_name = 'repos'

urlpatterns = [
    path('', views.repository_list, name='repository_list'),
    path('import/', views.repository_import, name='repository_import'),
    path('create/', views.repository_create, name='repository_create'),
    path('<int:pk>/', views.repository_detail, name='repository_detail'),
    path('<int:pk>/delete/', views.repository_delete, name='repository_delete'),
]
