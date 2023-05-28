from django import forms
from django.contrib.auth.forms import PasswordResetForm
from backend.models import UploadFiles, User
from backend.tasks import password_reset_token_mail_task


class UploadFilesForm(forms.ModelForm):

    class Meta:
        model = UploadFiles
        fields = ['user', 'email', 'name', 'file']
        widgets = {'user': forms.HiddenInput(), 'email': forms.HiddenInput()}


class LoginForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['email', 'password']


class RegisterForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['email', 'password', 'first_name', 'last_name', 'company', 'position', 'username']


class ResetPasswordForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['email']


class EnterNewPasswordForm(forms.Form):
    token = forms.CharField(min_length=10, max_length=40, widget=forms.HiddenInput())
    password = forms.CharField(min_length=8)
