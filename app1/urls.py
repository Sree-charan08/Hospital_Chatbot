from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='chat_index'),
    path('api/perform_action/', views.perform_action, name='perform_action'),
]
