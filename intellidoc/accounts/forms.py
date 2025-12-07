# accounts/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import get_user_model

User = get_user_model()

class CustomUserCreationForm(UserCreationForm):
    """Registration form using email only (username auto-generated internally)."""

    username = None  # hide username completely

    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'input', 'placeholder': 'Enter your email'})
    )
    first_name = forms.CharField(required=True, widget=forms.TextInput(attrs={'class': 'input'}))
    last_name = forms.CharField(required=True, widget=forms.TextInput(attrs={'class': 'input'}))
    password1 = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'input'}))
    password2 = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'input'}))

    class Meta:
        model = User
        fields = ("email", "first_name", "last_name", "password1", "password2")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data["email"].split("@")[0]  # auto username
        if commit:
            user.save()
        return user


class CustomAuthenticationForm(AuthenticationForm):
    """Login form using email instead of username."""

    username = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'input', 'placeholder': 'Email'})
    )
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'input', 'placeholder': 'Password'}))

    def confirm_login_allowed(self, user):
        if not user.is_active:
            raise forms.ValidationError("This account is inactive.", code="inactive")
