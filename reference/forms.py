from django import forms

from .services import VEHICLE_DESTINATIONS


class VehicleSelectorForm(forms.Form):
    q = forms.CharField(label="Search manufacturers and models", max_length=200, required=False)
    manufacturer = forms.SlugField(label="Manufacturer", max_length=120, required=False)
    destination = forms.ChoiceField(
        choices=[(item.token, item.label) for item in VEHICLE_DESTINATIONS],
        widget=forms.HiddenInput,
        error_messages={"invalid_choice": "Choose a valid navigation destination.",
                        "required": "Choose a valid navigation destination."},
    )
    model = forms.SlugField(max_length=120, required=False, widget=forms.HiddenInput)
