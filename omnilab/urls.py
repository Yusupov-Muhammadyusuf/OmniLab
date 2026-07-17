from django.urls import path
from . import views

urlpatterns = [
    path('robots.txt', views.robots_txt, name="robots_txt"),
    path('sitemap.xml', views.sitemap_xml, name="sitemap_xml"),
    path('pricing/', views.pricing, name="pricing"),
    path('privacy/', views.privacy, name="privacy"),
    path('terms/', views.terms, name="terms"),
    path('ai_insights/', views.ai_insights, name="ai_insights"),
]
