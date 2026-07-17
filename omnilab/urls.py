from django.urls import path
from . import views

urlpatterns = [
    path('pricing/', views.pricing, name="pricing"),
    path('privacy/', views.privacy, name="privacy"),
    path('terms/', views.terms, name="terms"),
    path('ai_insights/', views.ai_insights, name="ai_insights"),
]
