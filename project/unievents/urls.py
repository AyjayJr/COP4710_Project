"""cop4710 URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import path
from unievents.views import (
    EventView,
    RSOView,
    UniversityView,
    UniversityListView,
    create_comment_view,
    create_event_view,
    create_rso_view,
    home_view,
    join_rso_view,
    leave_rso_view,
    event_list_view,
    CreateUniversityView,
)
from django.views.generic import RedirectView

urlpatterns = [
    path("", RedirectView.as_view(pattern_name="home")),
    path("home", home_view, name="home"),
    path("universities/create", CreateUniversityView.as_view(), name="universities_create"),
    path("universities/list", UniversityListView.as_view(), name="universities_list"),
    path("universities/<pk>/", UniversityView.as_view(), name="universities_view"),
    path("rso/<university_id>/create", create_rso_view, name="rso_create"),
    path("rso/<pk>/", RSOView.as_view(), name="rso_view"),
    path("rso/<pk>/join", join_rso_view, name="rso_join"),
    path("rso/<pk>/leave", leave_rso_view, name="rso_leave"),
    path("events/<pk>/create_comment", create_comment_view, name="comment_create"),
    path("events/list/", event_list_view, name="events_list"),
    path("events/list/<int:year>", event_list_view, name="events_list"),
    path("events/list/<int:year>/<int:month>", event_list_view, name="events_list"),
    path("events/list/<int:year>/<int:month>/<int:day>/", event_list_view, name="events_list"),
    path(
        "events/list/upcoming/<int:year>/<int:month>/<int:day>/",
        lambda *a, **kw: event_list_view(upcoming=True, *a, **kw),
        name="events_list_upcoming",
    ),
    path("events/<rso_id>/create", create_event_view, name="events_create"),
    path("events/<pk>/", EventView.as_view(), name="events_view"),
]
