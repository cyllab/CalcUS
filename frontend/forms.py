"""
This file of part of CalcUS.

Copyright (C) 2020-2022 Raphaël Robidas

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import logging

from django.conf import settings
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.contrib.auth.forms import AuthenticationForm, UsernameField

if settings.IS_CLOUD:
    from captcha.fields import ReCaptchaField

from frontend.models import User, ClassGroup
from frontend.helpers import get_random_string

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s]  %(module)s: %(message)s"
)
logger = logging.getLogger(__name__)


class ResearcherCreateForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        label="Email",
        error_messages={"exists": "This email has already been used"},
    )

    if settings.IS_CLOUD:
        captcha = ReCaptchaField()

    class Meta:
        model = User
        fields = ("email", "password1", "password2")

    def save(self, commit=True):
        user = super(ResearcherCreateForm, self).save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user

    def clean_email(self):
        validate_email(self.cleaned_data["email"])
        if User.objects.filter(email=self.cleaned_data["email"]).exists():
            raise ValidationError(self.fields["email"].error_messages["exists"])
        return self.cleaned_data["email"]


class StudentCreateForm(forms.ModelForm):
    full_name = forms.CharField(required=True, label="Full name", max_length=256)
    access_code = forms.CharField(
        required=True,
        label="Access code",
    )

    if settings.IS_CLOUD:
        captcha = ReCaptchaField()

    class Meta:
        model = User
        fields = ("full_name",)

    def clean_full_name(self):
        full_name = self.cleaned_data["full_name"]
        if len(full_name) < 3:
            self.add_error("full_name", "The full name entered is unreasonably short")
        if len(full_name) > 255:
            self.add_error("full_name", "The full name entered is unreasonably long")
        return full_name

    def clean_access_code(self):
        self.validate_access_code()

    def validate_access_code(self):
        code = self.cleaned_data["access_code"]

        classes = ClassGroup.objects.filter(access_code=code)

        if classes.count() == 0:
            raise ValidationError(f"No group found with such access code")
        elif classes.count() > 1:
            logger.error(f"Multiple groups found with access code {code}!")
            raise ValidationError(f"Internal error")
        elif classes.count() == 1:
            self.student_class = classes.first()
        else:
            logger.error(
                f"Unexpected number of groups found with access code {code}: {classes.count()}!"
            )
            raise ValidationError(f"Internal error")

    def save(self, commit=True):
        user = super().save(commit=False)

        # TODO: give this to the student?
        self.rand_email = get_random_string() + "@calcus.cloud"
        self.rand_password = get_random_string()

        user.email = self.rand_email
        user.set_password(self.rand_password)
        user.in_class = self.student_class
        user.is_temporary = True

        if commit:
            user.save()
        return user


class UserLoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super(UserLoginForm, self).__init__(*args, **kwargs)

    if settings.IS_CLOUD:
        captcha = ReCaptchaField()
