from django import forms


class ContactForm(forms.Form):
    name = forms.CharField(
        max_length=100,
        strip=True,
        error_messages={"required": "Enter your name."},
    )
    email = forms.EmailField(
        max_length=254,
        error_messages={
            "required": "Enter your email address.",
            "invalid": "Enter a valid email address.",
        },
    )
    subject = forms.CharField(max_length=120, required=False, strip=True)
    message = forms.CharField(
        max_length=4000,
        strip=True,
        widget=forms.Textarea,
        error_messages={"required": "Enter a message."},
    )
    website = forms.CharField(required=False, widget=forms.HiddenInput)

    def clean_subject(self):
        subject = self.cleaned_data["subject"]
        return " ".join(subject.splitlines())
