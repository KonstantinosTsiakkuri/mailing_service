from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import ProtectedError
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.cache import cache_control, cache_page, never_cache
from django.views.decorators.vary import vary_on_cookie
from django.views.generic import CreateView, DeleteView, DetailView, ListView, TemplateView, UpdateView

from mailing.forms import MailingForm
from mailing.models import Client, Mailing, Message
from mailing.services import MailingSendError, get_home_statistics, get_user_statistics, send_mailing

# Во всех view ниже get_queryset оставляет только объекты текущего пользователя (owner=self.request.user).
# Чужой объект просто "не найден" в этом наборе, поэтому Django отвечает 404.
# Исключение - просмотр (список и карточка) клиентов и рассылок: тем, у кого есть право
# view_all_clients / view_all_mailings (менеджеры), показываются все объекты. Менять и удалять
# чужие объекты не может никто: в view изменения и удаления фильтр по владельцу остаётся всегда.


# Порядок важен: декораторы применяются снизу вверх, поэтому самый верхний работает "снаружи".
# cache_page не сохраняет ответы с заголовком private, поэтому cache_control стоит снаружи от него.
@method_decorator(cache_control(private=True), name="dispatch")  # браузеру можно кэшировать, общим прокси - нельзя
@method_decorator(cache_page(60), name="dispatch")  # страница целиком хранится в кэше сервера 60 секунд
@method_decorator(vary_on_cookie, name="dispatch")  # у каждого посетителя (по cookie) своя копия страницы
class HomeView(TemplateView):
    template_name = "mailing/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(get_home_statistics())
        return context

    def render_to_response(self, context, **response_kwargs):
        # TemplateResponse рисуется лениво; рисуем сразу, чтобы декораторы кэша работали с готовой страницей
        return super().render_to_response(context, **response_kwargs).render()


@method_decorator(never_cache, name="dispatch")
class StatisticsView(LoginRequiredMixin, TemplateView):
    template_name = "mailing/statistics.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(get_user_statistics(self.request.user))
        return context


@method_decorator(never_cache, name="dispatch")
class ClientListView(LoginRequiredMixin, ListView):
    model = Client
    template_name = "mailing/client_list.html"
    context_object_name = "clients"

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.has_perm("mailing.view_all_clients"):
            return queryset
        return queryset.filter(owner=self.request.user)


@method_decorator(never_cache, name="dispatch")
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


@method_decorator(never_cache, name="dispatch")
class ClientDetailView(LoginRequiredMixin, DetailView):
    model = Client
    template_name = "mailing/client_detail.html"
    context_object_name = "client"

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.has_perm("mailing.view_all_clients"):
            return queryset
        return queryset.filter(owner=self.request.user)


@method_decorator(never_cache, name="dispatch")
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


@method_decorator(never_cache, name="dispatch")
class ClientDeleteView(LoginRequiredMixin, DeleteView):
    model = Client
    template_name = "mailing/client_confirm_delete.html"
    success_url = reverse_lazy("mailing:client_list")
    context_object_name = "client"

    def get_queryset(self):
        return super().get_queryset().filter(owner=self.request.user)


@method_decorator(never_cache, name="dispatch")
class MessageListView(LoginRequiredMixin, ListView):
    model = Message
    template_name = "mailing/message_list.html"
    context_object_name = "message_list"

    def get_queryset(self):
        return super().get_queryset().filter(owner=self.request.user)


@method_decorator(never_cache, name="dispatch")
class MessageCreateView(LoginRequiredMixin, CreateView):
    model = Message
    fields = ["subject", "body"]
    template_name = "mailing/message_form.html"
    success_url = reverse_lazy("mailing:message_list")

    def form_valid(self, form):
        form.instance.owner = self.request.user
        return super().form_valid(form)


@method_decorator(never_cache, name="dispatch")
class MessageDetailView(LoginRequiredMixin, DetailView):
    model = Message
    template_name = "mailing/message_detail.html"
    context_object_name = "message"

    def get_queryset(self):
        return super().get_queryset().filter(owner=self.request.user)


@method_decorator(never_cache, name="dispatch")
class MessageUpdateView(LoginRequiredMixin, UpdateView):
    model = Message
    fields = ["subject", "body"]
    template_name = "mailing/message_form.html"
    success_url = reverse_lazy("mailing:message_list")

    def get_queryset(self):
        return super().get_queryset().filter(owner=self.request.user)


@method_decorator(never_cache, name="dispatch")
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


@method_decorator(never_cache, name="dispatch")
class MailingListView(LoginRequiredMixin, ListView):
    model = Mailing
    template_name = "mailing/mailing_list.html"
    context_object_name = "mailings"

    def get_queryset(self):
        mailings = super().get_queryset().select_related("message", "owner").prefetch_related("recipients")
        if not self.request.user.has_perm("mailing.view_all_mailings"):
            mailings = mailings.filter(owner=self.request.user)
        for mailing in mailings:
            mailing.update_status()
        return mailings


@method_decorator(never_cache, name="dispatch")
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


@method_decorator(never_cache, name="dispatch")
class MailingDetailView(LoginRequiredMixin, DetailView):
    model = Mailing
    template_name = "mailing/mailing_detail.html"
    context_object_name = "mailing"

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.has_perm("mailing.view_all_mailings"):
            return queryset
        return queryset.filter(owner=self.request.user)

    def get_object(self, queryset=None):
        mailing = super().get_object(queryset)
        mailing.update_status()
        return mailing


@method_decorator(never_cache, name="dispatch")
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


@method_decorator(never_cache, name="dispatch")
class MailingDeleteView(LoginRequiredMixin, DeleteView):
    model = Mailing
    template_name = "mailing/mailing_confirm_delete.html"
    success_url = reverse_lazy("mailing:mailing_list")
    context_object_name = "mailing"

    def get_queryset(self):
        return super().get_queryset().filter(owner=self.request.user)


@method_decorator(never_cache, name="dispatch")
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


@method_decorator(never_cache, name="dispatch")
class MailingToggleActiveView(PermissionRequiredMixin, View):
    """Отключение и включение рассылки менеджером (любой рассылки, только POST)."""

    permission_required = "mailing.disable_mailing"

    def post(self, request, pk):
        mailing = get_object_or_404(Mailing, pk=pk)
        mailing.is_active = not mailing.is_active
        mailing.save(update_fields=["is_active"])
        if mailing.is_active:
            messages.success(request, "Рассылка включена")
        else:
            messages.success(request, "Рассылка отключена")
        return redirect("mailing:mailing_detail", pk=mailing.pk)
