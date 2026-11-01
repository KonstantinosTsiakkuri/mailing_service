from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.views import (
    LoginView,
    LogoutView,
    PasswordResetCompleteView,
    PasswordResetConfirmView,
    PasswordResetDoneView,
    PasswordResetView,
)
from django.core.mail import send_mail
from django.shortcuts import get_object_or_404, redirect
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.views import View
from django.views.generic import CreateView, ListView

from users.forms import UserLoginForm, UserPasswordResetForm, UserRegisterForm, UserSetPasswordForm
from users.models import User


class RegisterView(CreateView):
    model = User
    form_class = UserRegisterForm
    template_name = "users/register.html"
    success_url = reverse_lazy("users:login")

    def form_valid(self, form):
        # Пользователь создаётся неактивным: войти он сможет только после перехода по ссылке из письма
        user = form.save(commit=False)
        user.is_active = False
        user.save()
        try:
            self.send_activation_email(user)
        except Exception as error:
            user.delete()  # иначе email остался бы занятым, а письма у пользователя нет
            form.add_error(None, f"Не удалось отправить письмо с подтверждением: {error}")
            return self.form_invalid(form)
        messages.success(self.request, "Мы отправили письмо со ссылкой для подтверждения email. Перейдите по ссылке.")
        return redirect(self.success_url)

    def send_activation_email(self, user):
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        link = self.request.build_absolute_uri(reverse("users:activate", kwargs={"uidb64": uid, "token": token}))
        send_mail(
            subject="Подтверждение регистрации",
            message=render_to_string("users/activation_email.txt", {"link": link}),
            from_email=None,
            recipient_list=[user.email],
            fail_silently=False,
        )


class ActivateView(View):
    def get(self, request, uidb64, token):
        try:
            user = User.objects.get(pk=force_str(urlsafe_base64_decode(uidb64)))
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None

        if user is None or not default_token_generator.check_token(user, token):
            messages.error(request, "Ссылка подтверждения недействительна или устарела. Зарегистрируйтесь заново.")
        elif user.is_active:
            messages.info(request, "Этот аккаунт уже подтверждён. Можно входить.")
        else:
            user.is_active = True
            user.save(update_fields=["is_active"])
            messages.success(request, "Email подтверждён. Теперь можно войти.")
        return redirect("users:login")


class UserLoginView(LoginView):
    form_class = UserLoginForm
    template_name = "users/login.html"


class UserLogoutView(LogoutView):
    pass


class UserPasswordResetView(PasswordResetView):
    form_class = UserPasswordResetForm
    template_name = "users/password_reset_form.html"
    email_template_name = "users/password_reset_email.txt"
    subject_template_name = "users/password_reset_subject.txt"
    success_url = reverse_lazy("users:password_reset_done")


class UserPasswordResetDoneView(PasswordResetDoneView):
    template_name = "users/password_reset_done.html"


class UserPasswordResetConfirmView(PasswordResetConfirmView):
    form_class = UserSetPasswordForm
    template_name = "users/password_reset_confirm.html"
    success_url = reverse_lazy("users:password_reset_complete")


class UserPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = "users/password_reset_complete.html"


class UserListView(PermissionRequiredMixin, ListView):
    """Список пользователей сервиса (для менеджеров)."""

    permission_required = "users.view_all_users"
    model = User
    template_name = "users/user_list.html"
    context_object_name = "user_list"
    ordering = ["email"]


class UserToggleActiveView(PermissionRequiredMixin, View):
    """Блокировка и разблокировка пользователя (только POST)."""

    permission_required = "users.block_user"

    def post(self, request, pk):
        target = get_object_or_404(User, pk=pk)
        if target == request.user:
            messages.error(request, "Нельзя заблокировать самого себя")
        elif target.is_superuser:
            messages.error(request, "Нельзя заблокировать суперпользователя")
        else:
            target.is_active = not target.is_active
            target.save(update_fields=["is_active"])
            if target.is_active:
                messages.success(request, f"Пользователь {target.email} разблокирован")
            else:
                messages.success(request, f"Пользователь {target.email} заблокирован")
        return redirect("users:user_list")
