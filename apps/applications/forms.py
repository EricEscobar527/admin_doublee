from django import forms

from .models import Application

CONFIG_FIELDS = ["paywall_enabled", "beta_ends_at", "beta_message", "subscription_product_id", "min_supported_build"]


class ApplicationForm(forms.ModelForm):
    class Meta:
        model = Application
        fields = ["name", "code", "package_name", "color", "description", "is_active", *CONFIG_FIELDS]
        widgets = {
            "color": forms.TextInput(attrs={"type": "color"}),
            "description": forms.Textarea(attrs={"rows": 3}),
            "beta_ends_at": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["beta_ends_at"].input_formats = ["%Y-%m-%d"]
        for name, field in self.fields.items():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs["class"] = "form-check-input"
            elif name == "color":
                widget.attrs["class"] = "form-control form-control-color"
            else:
                widget.attrs["class"] = "form-control"

    def clean_code(self):
        return self.cleaned_data["code"].lower()

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("paywall_enabled") and not cleaned.get("subscription_product_id"):
            self.add_error("subscription_product_id", "Obligatorio si el cobro está activado.")
        return cleaned

    def general_fields(self):
        return [f for f in self if f.name not in CONFIG_FIELDS]

    def config_fields(self):
        return [f for f in self if f.name in CONFIG_FIELDS]
