from django.urls import path
from . import views

urlpatterns = [
    path('robots.txt', views.robots_txt, name="robots_txt"),
    path('sitemap.xml', views.sitemap_xml, name="sitemap_xml"),
    path('pricing/', views.pricing, name="pricing"),
    path('privacy/', views.privacy, name="privacy"),
    path('terms/', views.terms, name="terms"),
    path(
        'demo/sodium-chlorine/',
        views.sodium_chlorine_demo,
        name="sodium_chlorine_demo",
    ),
    path(
        'guides/sodium-and-chlorine-reaction/',
        views.guided_experiment,
        {'guide_key': 'reaction'},
        name="guide_sodium_chlorine_reaction",
    ),
    path(
        'guides/sodium-and-chlorine-formula/',
        views.guided_experiment,
        {'guide_key': 'formula'},
        name="guide_sodium_chlorine_formula",
    ),
    path(
        'guides/sodium-and-chlorine-ionic-bond/',
        views.guided_experiment,
        {'guide_key': 'ionic-bond'},
        name="guide_sodium_chlorine_ionic_bond",
    ),
    path('ai_insights/', views.ai_insights, name="ai_insights"),
]
