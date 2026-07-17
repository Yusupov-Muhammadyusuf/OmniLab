from django.urls import path
from . import views

urlpatterns = [
    path('pricing/', views.pricing, name="pricing"),
    path('ai_insights/', views.ai_insights, name="ai_insights"),
]
