from django.contrib.auth.forms import (
    AdminUserCreationForm,
    AuthenticationForm,
    BaseUserCreationForm,
    PasswordResetForm,
    SetPasswordForm,
)

from users.models import User


def add_bootstrap_classes(form):
    """Добавляет всем полям формы Bootstrap-класс form-control."""
    for field in form.fields.values():
        field.widget.attrs["class"] = "form-control"


class UserRegisterForm(BaseUserCreationForm):
    class Meta:
        model = User
        fields = ("email",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        add_bootstrap_classes(self)


class UserLoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        add_bootstrap_classes(self)


class UserPasswordResetForm(PasswordResetForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        add_bootstrap_classes(self)


class UserSetPasswordForm(SetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        add_bootstrap_classes(self)


class AdminUserAddForm(AdminUserCreationForm):
    """Форма создания пользователя в админке (стандартная ждёт поле username, а у нас его нет)."""

    class Meta:
        model = User
        fields = ("email",)
