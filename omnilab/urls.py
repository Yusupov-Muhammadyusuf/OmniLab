from django.urls import path
from . import views

urlpatterns = [
    path('ai_insights/', views.ai_insights, name="ai_insights"),
]