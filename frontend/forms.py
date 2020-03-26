from django.forms import ModelForm, TextInput, Textarea
from django.utils.translation import gettext_lazy as _
from django import forms

from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError


class UserCreateForm(UserCreationForm):
    email = forms.EmailField(required=True,
                         label='Email',
                         error_messages={'exists': 'Oops'})

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")


    def save(self, commit=True):
        user = super(UserCreateForm, self).save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user

    def clean_email(self):
        if User.objects.filter(email=self.cleaned_data['email']).exists():
            raise ValidationError(self.fields['email'].error_messages['exists'])
        return self.cleaned_data['email']

