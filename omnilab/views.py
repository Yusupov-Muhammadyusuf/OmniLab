import os
import json
from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

PRODUCTION_BASE_URL = "https://omnilab-bk8q.onrender.com"
PUBLIC_CANONICAL_URLS = {
    "index": f"{PRODUCTION_BASE_URL}/",
    "pricing": f"{PRODUCTION_BASE_URL}/pricing/",
    "privacy": f"{PRODUCTION_BASE_URL}/privacy/",
    "terms": f"{PRODUCTION_BASE_URL}/terms/",
}

HOMEPAGE_FAQS = [
    {
        "question": "How do I set up an experiment in OmniLab?",
        "answer": (
            "Choose an Erlenmeyer flask, graduated test tube, or laboratory "
            "beaker from Apparatus. Open Chemicals, search the available "
            "inputs, and drag one or more into the vessel. Add the virtual "
            "Bunsen burner if you want to model heating, then select Analyze "
            "Chemical Reaction."
        ),
    },
    {
        "question": "Which chemicals and equipment can I use?",
        "answer": (
            "The current release uses the chemicals listed in its searchable "
            "Chemicals menu. Equipment includes an Erlenmeyer flask, graduated "
            "test tube, laboratory beaker, and virtual Bunsen burner. The menus "
            "in the lab are the current source of truth for supported inputs."
        ),
    },
    {
        "question": "How accurate are the reaction results?",
        "answer": (
            "OmniLab generates predicted equations, explanations, visual "
            "effects, and safety guidance from the chemical names you select. "
            "Generated results can be incomplete or wrong, so check important "
            "information against trusted chemistry sources and follow your "
            "instructor's guidance."
        ),
    },
    {
        "question": "Can OmniLab replace a physical chemistry lab?",
        "answer": (
            "No. OmniLab is an educational prediction tool for exploring "
            "setups before working with real materials. It doesn't reproduce "
            "every real-world condition or replace trained supervision, "
            "professional judgment, or the safety procedures of a physical "
            "laboratory."
        ),
    },
    {
        "question": "Do I need an account to start?",
        "answer": (
            "No. The current public release opens directly in the lab and "
            "doesn't require an account or payment. Future access or pricing "
            "may change as the product develops."
        ),
    },
]

client = OpenAI(
    base_url="https://models.inference.ai.azure.com",
    api_key=os.getenv("FEATHERLESS_AI_API")
)

def index(request):
    faq_schema = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": faq["question"],
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": faq["answer"],
                },
            }
            for faq in HOMEPAGE_FAQS
        ],
    }
    software_schema = {
        "@context": "https://schema.org",
        "@type": "SoftwareApplication",
        "name": "OmniLab",
        "url": PUBLIC_CANONICAL_URLS["index"],
        "description": (
            "An interactive virtual chemistry laboratory for chemistry "
            "students to mix compounds, choose lab equipment, and review "
            "predicted reactions."
        ),
        "applicationCategory": "EducationalApplication",
        "operatingSystem": "Any",
        "featureList": [
            "Search and mix supported chemicals",
            "Choose a flask, test tube, beaker, or virtual Bunsen burner",
            (
                "Review predicted equations, explanations, visual effects, "
                "and safety guidance"
            ),
        ],
        "license": (
            "https://github.com/Yusupov-Muhammadyusuf/OmniLab/blob/main/LICENSE"
        ),
        "codeRepository": "https://github.com/Yusupov-Muhammadyusuf/OmniLab",
    }
    return render(
        request,
        "index.html",
        {
            "canonical_url": PUBLIC_CANONICAL_URLS["index"],
            "homepage_faqs": HOMEPAGE_FAQS,
            "faq_schema_json": json.dumps(faq_schema),
            "software_schema_json": json.dumps(software_schema),
        },
    )

def pricing(request):
    return render(
        request,
        "pricing.html",
        {"canonical_url": PUBLIC_CANONICAL_URLS["pricing"]},
    )

def privacy(request):
    return render(
        request,
        "privacy.html",
        {"canonical_url": PUBLIC_CANONICAL_URLS["privacy"]},
    )

def terms(request):
    return render(
        request,
        "terms.html",
        {"canonical_url": PUBLIC_CANONICAL_URLS["terms"]},
    )


def robots_txt(request):
    content = "\n".join(
        [
            "User-agent: *",
            "Allow: /",
            "Disallow: /admin/",
            "Disallow: /ai_insights/",
            f"Sitemap: {PRODUCTION_BASE_URL}/sitemap.xml",
            "",
        ]
    )
    return HttpResponse(content, content_type="text/plain; charset=utf-8")


def sitemap_xml(request):
    urls = "".join(
        f"  <url><loc>{url}</loc></url>\n"
        for url in PUBLIC_CANONICAL_URLS.values()
    )
    content = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{urls}"
        "</urlset>\n"
    )
    return HttpResponse(content, content_type="application/xml; charset=utf-8")

@csrf_exempt
def ai_insights(request):
    if request.method == "POST":
        user_query = request.POST.get("query", "No chemicals specified.")

        system_prompt = (
            "You are an advanced academic chemistry simulator engine for OmniLab. "
            "Analyze the mixture of provided chemicals thoroughly.\n\n"
            "You MUST return strictly a single valid JSON object containing these exact keys:\n"
            "{\n"
            "  \"effect\": \"explosion\",\n"
            "  \"equation\": \"detailed balanced molecular equations with states\",\n"
            "  \"explanation\": \"clear educational explanation\",\n"
            "  \"safety\": \"detailed guidelines\"\n"
            "}\n\n"
            "Instructions for output tuning:\n"
            "1. 'effect': Choose exactly one value from ['explosion', 'smoke', 'color_change', 'bubble', 'none']. Set to 'explosion' if highly reactive metals (Na, K, Mg) meet water/acids. Set to 'smoke' for strong neutralization or gas evolution. Otherwise choose 'color_change' or 'bubble' based on the properties.\n"
            "2. 'equation': Provide ONLY the balanced chemical molecular equations with states (e.g., '2NaOH(aq) + H2SO4(aq) -> Na2SO4(aq) + 2H2O(l)'). Do NOT include any nested JSON, step-by-step text descriptions, explanations, spectator ions text, or words inside this field. Just raw chemical equations separated by ' | ' if there are multiple steps.\n"        
            "3. 'explanation': Provide a concise, clear, and high-density academic explanation (strictly 3-4 sentences maximum). Do NOT generate random text, messy paragraphs, or long historical essays. Focus exclusively on the main chemical reaction, thermodynamics (exothermic/endothermic), and its core behavior.\n"
            "4. 'safety': Provide exactly three short, practical laboratory safety rules tailored to these reagents. Format them as a single string separated by ' | ' (e.g., 'Wear heavy-duty nitrile gloves. | Avoid inhaling any evolved gases. | Keep the reaction flask away from open flames.'). Start each rule with a strong action verb. Keep them simple, logical, and chemical-focused."
        )

        try:
            response = client.chat.completions.create(
                model="Meta-Llama-3.1-8B-Instruct", 
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_query}
                ],
                response_format={"type": "json_object"},
                temperature=0.0,  
                max_tokens=3000
            )
            
            ai_raw_text = response.choices[0].message.content.strip()
            data = json.loads(ai_raw_text)
            
            return JsonResponse({"status": "success", "data": data})
            
        except (json.JSONDecodeError, ValueError):
            return JsonResponse({
                "status": "success", 
                "data": {
                    "effect": "none",
                    "equation": "Reaction data refreshed.",
                    "explanation": "The simulator was unable to fully load the response due to data formatting. Please try again.",
                    "safety": "Standard lab safety protocols apply. | Wear goggles. | Work in a ventilated area."
                }
            })
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)})
        
    return JsonResponse({"status": "error", "message": "Only POST requests are accepted."})
