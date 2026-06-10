import os
import json
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    base_url="https://models.inference.ai.azure.com",
    api_key=os.getenv("FEATHERLESS_AI_API")
)

def index(request):
    return render(request, "index.html")

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