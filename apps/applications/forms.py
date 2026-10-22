from django import forms

from .models import Application


class ApplicationForm(forms.ModelForm):
    class Meta:
        model = Application
        fields = ["name", "code", "package_name", "color", "description", "is_active"]
        widgets = {
            "color": forms.TextInput(attrs={"type": "color"}),
            "description": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
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
