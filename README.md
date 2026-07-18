# OmniLab

OmniLab is a no-account virtual chemistry lab for chemistry students. The current release supports one complete reaction journey: prepare Sodium and Chlorine, then request an educational prediction with an equation, a short explanation, and three safety rules.

[Open the live lab](https://omnilab-bk8q.onrender.com/) · [Try the prepared Sodium and Chlorine demo](https://omnilab-bk8q.onrender.com/demo/sodium-chlorine/)

![OmniLab showing the supported Sodium and Chlorine reaction](static/images/omnilab-social-preview.png)

## What the current release does

- Opens directly in the browser without an account or payment.
- Provides Sodium and Chlorine as the supported pair for one reaction combination.
- Lets a student assemble the mixture and choose when to request a prediction.
- Returns an equation, a short explanation, and three safety rules for a supported result.
- Keeps the current setup and last result in the visitor's browser until they reset it.

## Start with the supported demo

The prepared demo opens the real lab with Sodium and Chlorine already selected. It does not submit anything automatically, so the visitor remains in control of whether to request the prediction.

1. Open the [prepared Sodium and Chlorine demo](https://omnilab-bk8q.onrender.com/demo/sodium-chlorine/).
2. Review the selected chemicals and setup.
3. Select **Analyze Chemical Reaction** to request the educational prediction.

## Educational and safety limits

OmniLab predicts reactions from the chemical names selected in the browser. Generated equations, explanations, and safety guidance can be incomplete or wrong. Check important information against trusted chemistry sources and follow an instructor's guidance, trained supervision, and the safety procedures of any physical laboratory.

The current release supports one unique reaction combination, Sodium and Chlorine. It is a narrow educational prediction tool, not a validated chemistry simulation, and it does not reproduce every real-world reaction condition.

## Run locally

Create a virtual environment and install the Python dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and add a GitHub Models token with Models read permission if you want to request reaction predictions. The rest of the interface can be explored without a provider token.

Prepare the local database and start Django:

```bash
python manage.py migrate
python manage.py runserver
```

Then open `http://127.0.0.1:8000/`.

## Tests

Run the Django test suite with:

```bash
python manage.py test
```

## Built with

- Django and Gunicorn
- TypeScript compiled to browser modules
- HTML5 Canvas and Bootstrap
- GitHub Models through the OpenAI Python client

## License

OmniLab is available under the [MIT License](LICENSE).
