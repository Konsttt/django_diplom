from django import forms

from backend.models import UploadFiles, User


class UploadFilesForm(forms.ModelForm):

    class Meta:
        model = UploadFiles
        fields = ['user', 'email', 'name', 'file']
        widgets = {'user': forms.HiddenInput(), 'email': forms.HiddenInput()}


class LoginForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['email', 'password']