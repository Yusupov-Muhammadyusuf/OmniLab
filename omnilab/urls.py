from django.urls import path
from . import views

urlpatterns = [
    path('robots.txt', views.robots_txt, name="robots_txt"),
    path('sitemap.xml', views.sitemap_xml, name="sitemap_xml"),
    path('pricing/', views.pricing, name="pricing"),
    path('contact/', views.contact, name="contact"),
    path('faq/', views.faq, name="faq"),
    path('privacy/', views.privacy, name="privacy"),
    path('terms/', views.terms, name="terms"),
    path('guides/', views.guide_library, name="guide_library"),
    path(
        'demo/sodium-chlorine/',
        views.sodium_chlorine_demo,
        name="sodium_chlorine_demo",
    ),
    path(
        'demo/carbon-dioxide-calcium-hydroxide/',
        views.prepared_reaction_demo,
        {'demo_key': 'carbon-dioxide-calcium-hydroxide'},
        name="demo_carbon_dioxide_calcium_hydroxide",
    ),
    path(
        'demo/sodium-carbonate-hydrochloric-acid/',
        views.prepared_reaction_demo,
        {'demo_key': 'sodium-carbonate-hydrochloric-acid'},
        name="demo_sodium_carbonate_hydrochloric_acid",
    ),
    path(
        'demo/silver-nitrate-potassium-iodide/',
        views.prepared_reaction_demo,
        {'demo_key': 'silver-nitrate-potassium-iodide'},
        name="demo_silver_nitrate_potassium_iodide",
    ),
    path(
        'demo/copper-sulfate-potassium-hydroxide/',
        views.prepared_reaction_demo,
        {'demo_key': 'copper-sulfate-potassium-hydroxide'},
        name="demo_copper_sulfate_potassium_hydroxide",
    ),
    path(
        'demo/sodium-water/',
        views.prepared_reaction_demo,
        {'demo_key': 'sodium-water'},
        name="demo_sodium_water",
    ),
    path(
        'demo/zinc-hydrochloric-acid/',
        views.prepared_reaction_demo,
        {'demo_key': 'zinc-hydrochloric-acid'},
        name="demo_zinc_hydrochloric_acid",
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
    path(
        'guides/chemical-reaction-virtual-lab/',
        views.chemical_reaction_virtual_lab,
        name="chemical_reaction_virtual_lab",
    ),
    path(
        'guides/why-limewater-turns-cloudy-with-carbon-dioxide/',
        views.observation_guide,
        {'guide_key': 'limewater-carbon-dioxide'},
        name="guide_limewater_carbon_dioxide",
    ),
    path(
        'guides/why-sodium-carbonate-fizzes-with-hydrochloric-acid/',
        views.observation_guide,
        {'guide_key': 'sodium-carbonate-hydrochloric-acid'},
        name="guide_sodium_carbonate_hydrochloric_acid",
    ),
    path(
        'guides/silver-nitrate-potassium-iodide-precipitate/',
        views.observation_guide,
        {'guide_key': 'silver-nitrate-potassium-iodide'},
        name="guide_silver_nitrate_potassium_iodide",
    ),
    path(
        'guides/copper-ii-sulfate-potassium-hydroxide-precipitate/',
        views.observation_guide,
        {'guide_key': 'copper-sulfate-potassium-hydroxide'},
        name="guide_copper_sulfate_potassium_hydroxide",
    ),
    path(
        'guides/reaction-of-sodium-in-water/',
        views.observation_guide,
        {'guide_key': 'sodium-water'},
        name="guide_sodium_water",
    ),
    path(
        'guides/zinc-and-hydrochloric-acid-reaction/',
        views.observation_guide,
        {'guide_key': 'zinc-hydrochloric-acid'},
        name="guide_zinc_hydrochloric_acid",
    ),
    path('ai_insights/', views.ai_insights, name="ai_insights"),
]
