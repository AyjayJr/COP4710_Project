from typing import Any, Dict, Type, Union, cast
from django.db import models
from django.db.models.base import ModelBase
from django.http.response import HttpResponseNotAllowed
from django.shortcuts import redirect, render
from django.http import HttpRequest
from django.views.generic.detail import DetailView
from django.views.generic.list import ListView
from accounts.views import login_required, super_admin_required
from accounts.models import User
from unievents.forms import CreateEventForm, CreateLocationForm, CreateRSOForm, CreateUniversityForm
from django.core.exceptions import PermissionDenied

from unievents.models import Comment, Event, Event_tag, RSO, University
from django.contrib.auth.mixins import LoginRequiredMixin


def being_a_student_required(func):
    @login_required()
    def inner(request, university_id: int, *args, **kwargs):
        if request.user.university_id != university_id:
            raise PermissionError("Being a student at the university is required to view this page.")
        return func(request, university_id, *args, **kwargs)

    return inner


def being_an_admin_required(func):
    @being_a_student_required
    def inner(request, university_id: int, rso_id: int, *args, **kwargs):
        if not request.user.is_admin(rso_id):
            raise PermissionDenied("Admin privileges required to view this page.")
        return func(request, university_id, rso_id, *args, **kwargs)

    return inner


def post_requests_only(func):
    def inner(request, *args, **kwargs):
        if request.method != "POST":
            return HttpResponseNotAllowed("Only POST requests are allowed on this url.")
        return func(request, *args, **kwargs)

    return inner


@login_required()
def home_view(request: HttpRequest):
    return render(request, "unievents/home.html")


@super_admin_required()
def create_university_view(request):
    university_form = CreateUniversityForm(request.POST or None, request.FILES or None)
    location_form = CreateLocationForm(request.POST or None)
    context = {"university_form": university_form, "location_form": location_form}
    if request.method == "GET":
        return render(request, "unievents/university_create.html", context)
    elif request.method == "POST":
        if university_form.is_valid() and location_form.is_valid():
            location = location_form.save()
            university_form.save(location)
            return redirect("home")
        else:
            return render(request, "unievents/university_create.html", context)
    else:
        return render(request, "unievents/university_create.html", context)


class UniversityView(LoginRequiredMixin, DetailView):
    template_name = "unievents/university_view.html"
    model = University


class UniversityListView(LoginRequiredMixin, ListView):
    template_name = "unievents/university_list.html"
    model = University


def add_to_context_decorator(**models: Type[models.Model]):
    """ @decorator(model1, model2, model3_pk_name=model3, ...) """

    def arghandler(cls: Union[Type[DetailView], Type[ListView]]):
        original_get_context_data = cls.get_context_data

        def inner(self, **kwargs: Any) -> Any:
            context = original_get_context_data(self, **kwargs)
            for kwargname, model in models.items():
                context[model._meta.db_table] = model.objects.get(pk=self.kwargs[kwargname])
            return context

        cls.get_context_data = inner
        return cls

    return arghandler


@add_to_context_decorator(university_id=University)
class RSOView(LoginRequiredMixin, DetailView):
    template_name = "unievents/rso_view.html"
    model = RSO

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        ctx = super().get_context_data(**kwargs)
        # There is a liskov problem here...
        user: User = cast(User, self.request.user)
        rso: RSO = ctx["rso"]
        ctx["is_admin"] = user.is_admin(rso.rso_id)
        user_is_already_member = bool(user.rso_memberships.filter(pk=rso.rso_id))
        ctx["user_is_already_member"] = user_is_already_member
        ctx["user_can_join"] = user.university == rso.university and not user_is_already_member
        return ctx


@add_to_context_decorator(university_id=University)
class RSOListView(LoginRequiredMixin, ListView):
    template_name = "unievents/rso_list.html"
    model = RSO


@being_a_student_required
def create_rso_view(request, university_id: int):
    university = University.objects.get(pk=university_id)  # TODO: Handle university_does_not_exist_error
    students = university.students.exclude(pk=request.user.id)
    form = CreateRSOForm(request.user, students, request.POST or None)
    context = {"form": form, "university": university}
    if request.method == "GET":
        return render(request, "unievents/rso_create.html", context)
    elif request.method == "POST":
        if form.is_valid():
            form.save()
            return redirect("home")
        else:
            return render(request, "unievents/rso_create.html", context)
    else:
        return render(request, "unievents/rso_create.html", context)


@post_requests_only
@being_a_student_required
def join_rso_view(request, university_id, rso_id):
    user: User = request.user
    query = user.rso_memberships.filter(pk=rso_id)
    if query:
        raise PermissionError("RSO members cannot join again, duh.")
    rso = RSO.objects.get(pk=rso_id)
    rso.members.add(user)
    return redirect("rso_view", university_id, rso_id)


@post_requests_only
@being_a_student_required
def leave_rso_view(request, university_id, rso_id):
    user: User = request.user
    if user.is_admin(rso_id):
        raise PermissionError("Admin of an RSO cannot leave it.")
    rso = user.rso_memberships.filter(pk=rso_id).first()
    if rso is None:
        raise PermissionError("Only RSO members can leave it, duh.")
    user.rso_memberships.remove(rso)
    return redirect("rso_view", university_id, rso_id)


@being_an_admin_required
def create_event_view(request, university_id: int, rso_id):
    event_form = CreateEventForm(request.POST or None, university_id=university_id, rso_id=rso_id)
    location_form = CreateLocationForm(request.POST or None)
    context = {
        "event_form": event_form,
        "location_form": location_form,
        "is_admin": request.user.is_admin(rso_id),
        "rso": RSO.objects.get(pk=rso_id),
        "university": University.objects.get(pk=university_id),
        "possible_tags": Event_tag.objects.all(),
    }
    if request.method == "GET":
        return render(request, "unievents/event_create.html", context)
    elif request.method == "POST":
        if event_form.is_valid() and location_form.is_valid():
            location = location_form.save()
            event = event_form.save(location)
            return redirect("event_view", university_id, rso_id, event.event_id)
        else:
            return render(request, "unievents/event_create.html", context)
    else:
        return render(request, "unievents/event_create.html", context)


@add_to_context_decorator(university_id=University, rso_id=RSO)
class EventView(LoginRequiredMixin, DetailView):
    template_name = "unievents/event_view.html"
    model = Event


@post_requests_only
def create_comment_view(request, university_id, rso_id, event_id):
    Comment(event_id=event_id, user_id=request.user.id, text=request.POST["text"], rating=request.POST["rating"]).save()
    return redirect("event_view", university_id, rso_id, event_id)