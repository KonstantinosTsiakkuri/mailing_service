from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import ProtectedError
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, DeleteView, DetailView, ListView, TemplateView, UpdateView

from mailing.forms import MailingForm
from mailing.models import Client, Mailing, Message
from mailing.services import MailingSendError, get_home_statistics, send_mailing

# Во всех view ниже get_queryset оставляет только объекты текущего пользователя (owner=self.request.user).
# Чужой объект просто "не найден" в этом наборе, поэтому Django отвечает 404.


class HomeView(TemplateView):
    template_name = "mailing/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(get_home_statistics())
        return context


class ClientListView(LoginRequiredMixin, ListView):
    model = Client
    template_name = "mailing/client_list.html"
    context_object_name = "clients"

    def get_queryset(self):
        return super().get_queryset().filter(owner=self.request.user)


class ClientCreateView(LoginRequiredMixin, CreateView):
    model = Client
    fields = [
        "email",
        "full_name",
        "comment",
    ]
    template_name = "mailing/client_form.html"
    success_url = reverse_lazy("mailing:client_list")

    def form_valid(self, form):
        form.instance.owner = self.request.user
        return super().form_valid(form)


class ClientDetailView(LoginRequiredMixin, DetailView):
    model = Client
    template_name = "mailing/client_detail.html"
    context_object_name = "client"

    def get_queryset(self):
        return super().get_queryset().filter(owner=self.request.user)


class ClientUpdateView(LoginRequiredMixin, UpdateView):
    model = Client
    fields = [
        "email",
        "full_name",
        "comment",
    ]
    template_name = "mailing/client_form.html"
    success_url = reverse_lazy("mailing:client_list")

    def get_queryset(self):
        return super().get_queryset().filter(owner=self.request.user)


class ClientDeleteView(LoginRequiredMixin, DeleteView):
    model = Client
    template_name = "mailing/client_confirm_delete.html"
    success_url = reverse_lazy("mailing:client_list")
    context_object_name = "client"

    def get_queryset(self):
        return super().get_queryset().filter(owner=self.request.user)


class MessageListView(LoginRequiredMixin, ListView):
    model = Message
    template_name = "mailing/message_list.html"
    context_object_name = "message_list"

    def get_queryset(self):
        return super().get_queryset().filter(owner=self.request.user)


class MessageCreateView(LoginRequiredMixin, CreateView):
    model = Message
    fields = ["subject", "body"]
    template_name = "mailing/message_form.html"
    success_url = reverse_lazy("mailing:message_list")

    def form_valid(self, form):
        form.instance.owner = self.request.user
        return super().form_valid(form)


class MessageDetailView(LoginRequiredMixin, DetailView):
    model = Message
    template_name = "mailing/message_detail.html"
    context_object_name = "message"

    def get_queryset(self):
        return super().get_queryset().filter(owner=self.request.user)


class MessageUpdateView(LoginRequiredMixin, UpdateView):
    model = Message
    fields = ["subject", "body"]
    template_name = "mailing/message_form.html"
    success_url = reverse_lazy("mailing:message_list")

    def get_queryset(self):
        return super().get_queryset().filter(owner=self.request.user)


class MessageDeleteView(LoginRequiredMixin, DeleteView):
    model = Message
    template_name = "mailing/message_confirm_delete.html"
    success_url = reverse_lazy("mailing:message_list")
    context_object_name = "message"

    def get_queryset(self):
        return super().get_queryset().filter(owner=self.request.user)

    def form_valid(self, form):
        # В Django 4+ само удаление выполняется здесь, поэтому ProtectedError ловим тоже здесь
        try:
            return super().form_valid(form)
        except ProtectedError:
            messages.error(self.request, "Нельзя удалить сообщение: оно используется в рассылках")
            return redirect("mailing:message_detail", pk=self.object.pk)


class MailingListView(LoginRequiredMixin, ListView):
    model = Mailing
    template_name = "mailing/mailing_list.html"
    context_object_name = "mailings"

    def get_queryset(self):
        mailings = (
            super()
            .get_queryset()
            .filter(owner=self.request.user)
            .select_related("message")
            .prefetch_related("recipients")
        )
        for mailing in mailings:
            mailing.update_status()
        return mailings


class MailingCreateView(LoginRequiredMixin, CreateView):
    model = Mailing
    form_class = MailingForm
    template_name = "mailing/mailing_form.html"
    success_url = reverse_lazy("mailing:mailing_list")

    def get_form_kwargs(self):
        # Передаём пользователя в форму, чтобы в ней были только его сообщения и клиенты
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.owner = self.request.user
        return super().form_valid(form)


class MailingDetailView(LoginRequiredMixin, DetailView):
    model = Mailing
    template_name = "mailing/mailing_detail.html"
    context_object_name = "mailing"

    def get_queryset(self):
        return super().get_queryset().filter(owner=self.request.user)

    def get_object(self, queryset=None):
        mailing = super().get_object(queryset)
        mailing.update_status()
        return mailing


class MailingUpdateView(LoginRequiredMixin, UpdateView):
    model = Mailing
    form_class = MailingForm
    template_name = "mailing/mailing_form.html"
    success_url = reverse_lazy("mailing:mailing_list")

    def get_queryset(self):
        return super().get_queryset().filter(owner=self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        response = super().form_valid(form)
        # Даты могли измениться, поэтому статус пересчитываем сразу после сохранения
        self.object.update_status()
        return response


class MailingDeleteView(LoginRequiredMixin, DeleteView):
    model = Mailing
    template_name = "mailing/mailing_confirm_delete.html"
    success_url = reverse_lazy("mailing:mailing_list")
    context_object_name = "mailing"

    def get_queryset(self):
        return super().get_queryset().filter(owner=self.request.user)


class MailingSendView(LoginRequiredMixin, View):
    """Запуск рассылки кнопкой. Принимает только POST (данные меняются, поэтому GET нельзя)."""

    def post(self, request, pk):
        mailing = get_object_or_404(Mailing, pk=pk, owner=request.user)
        try:
            success, failed = send_mailing(mailing)
        except MailingSendError as error:
            messages.error(request, str(error))
        else:
            messages.success(request, f"Рассылка отправлена: успешно {success}, неуспешно {failed}")
        return redirect("mailing:mailing_detail", pk=mailing.pk)
