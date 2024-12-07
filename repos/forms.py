from django import forms
from .models import Repository

class RepositoryForm(forms.ModelForm):
    class Meta:
        model = Repository
        fields = ['name', 'description', 'private']

class RepositoryImportForm(forms.Form):
    username = forms.CharField(
        required=False,
        help_text="Leave empty to import your own repositories"
    )
    include_private = forms.BooleanField(
        required=False,
        initial=True,
        help_text="Include private repositories"
    )
    include_organization = forms.BooleanField(
        required=False,
        initial=True,
        help_text="Include repositories from organizations"
    )
    include_collaborations = forms.BooleanField(
        required=False,
        initial=True,
        help_text="Include repositories you collaborate on"
    )

class RepositorySearchForm(forms.Form):
    query = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search repositories...',
            'aria-label': 'Search'
        })
    )

class RepositoryCreateForm(forms.Form):
    name = forms.CharField(max_length=100)
    description = forms.CharField(widget=forms.Textarea, required=False)
    private = forms.BooleanField(required=False, initial=False)
    auto_init = forms.BooleanField(
        required=False,
        initial=True,
        help_text="Initialize repository with README"
    )