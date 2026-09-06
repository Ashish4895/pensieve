from django.urls import path
from . import views

app_name = 'chatbot'

urlpatterns = [
    path('', views.index, name='index'),
    path('api/history/', views.get_history, name='get_history'),
    path('api/chat/', views.send_message, name='send_message'),
    path('api/clear/', views.clear_history, name='clear_history'),
]
