from django import forms

class ClaimForm(forms.Form):
    requested_ip = forms.CharField(
        required=False,
        label="IP (optional)",
        widget=forms.TextInput(attrs={"placeholder": "e.g. 192.168.1.50"})
    )
    hostname = forms.CharField(required=False)
    description = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))
