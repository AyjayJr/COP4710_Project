from typing import Type, Union, cast

from django.core.exceptions import ValidationError
from accounts.models import User
from accounts.forms import CaseInsensitiveEmail
from unievents.models import Event, Tag, Location, RSO, University
from django import forms
from mapwidgets.widgets import GooglePointFieldWidget, GoogleStaticMapWidget
from django.contrib.gis.geos.geometry import GEOSGeometry
from django.contrib.gis.geos.point import Point
import datetime

from unievents.util import download
from cop4710.settings import MEDIA_ROOT


DATE_INPUT_ARGS = {"class": "date-input"}
RRULE_TYPE_CHOICE_INPUT_ATTRS = {"class": "rrule-type-choice-input"}


class DynamicForm(forms.Form):
    def __init__(self, extra: dict, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for key, value in extra.items():
            self.fields[key] = value


class CaseInsensitiveCharField(forms.CharField):
    def clean(self, value):
        return super().clean(value.lower())


class CreateLocationForm(forms.ModelForm):
    point = forms.fields.Field(widget=GooglePointFieldWidget, label="Location")

    class Meta:
        model = Location
        exclude = ("latitude", "longitude", "image")

    def save(self, **kwargs):
        instance = super().save(commit=False)
        point = cast(Point, GEOSGeometry(self.cleaned_data["point"]))
        instance.longitude, instance.latitude = point.x, point.y
        existing_locations = self.Meta.model.objects.filter(longitude=point.x, latitude=point.y)
        if len(existing_locations):
            return existing_locations[0]
        fname = (MEDIA_ROOT / "location" / f"{instance.longitude}|{instance.latitude}").with_suffix(".png")
        download(GoogleStaticMapWidget().get_image_url(point), fname)
        instance.image = "location/" + fname.name
        return instance


class FormWithLocationMixin:
    location_form: CreateLocationForm

    def __init__(self, *args, **kwargs):
        self.location_form = CreateLocationForm(*args, **kwargs)
        super().__init__(*args, **kwargs)

    def _html_output(self, *args, **kwargs):
        return self.location_form._html_output(*args, **kwargs) + super()._html_output(*args, **kwargs)

    def is_valid(self):
        return super().is_valid() and self.location_form.is_valid()

    @property
    def media(self, *args, **kwargs):
        return self.location_form.media + super().media

    def save(self, commit=True):
        location = self.location_form.save()
        instance = super().save(False)
        instance.location_id = location.id
        if commit:
            instance.save()
        return instance


class CreateUniversityForm(FormWithLocationMixin, forms.ModelForm):
    name = forms.fields.CharField(widget=forms.TextInput)
    description = forms.fields.CharField(widget=forms.Textarea)
    email_domain = CaseInsensitiveCharField(widget=forms.TextInput)
    avatar_image = forms.fields.ImageField(max_length=10000, allow_empty_file=False)

    class Meta:
        model = University
        fields = ("name", "email_domain", "avatar_image", "description")

    def clean_image(self):
        image = self.cleaned_data.get("avatar_image", False)
        if image:
            if image._size > University.max_avatar_size:
                raise ValidationError("Image file too large ( > 5mb )")
            return image
        else:
            raise ValidationError("Couldn't read uploaded image")


class ModelMultipleChoiceFieldWithMinNumberOfChoices(forms.ModelMultipleChoiceField):
    def __init__(self, min_choices, *args, **kwargs):
        self.min_choices = min_choices
        super().__init__(*args, **kwargs)

    def clean(self, value):
        if len(value) < self.min_choices:
            raise ValidationError(f"{len(value)} choices provided. {self.min_choices} required.")
        return super().clean(value)


class CreateRSOForm(forms.ModelForm):
    members = ModelMultipleChoiceFieldWithMinNumberOfChoices(
        min_choices=4,
        widget=forms.widgets.CheckboxSelectMultiple,
        help_text="Pick 4 more students to create the RSO.",
        queryset=None,
    )
    name = forms.fields.CharField(widget=forms.TextInput)

    class Meta:
        model = RSO
        fields = ("name", "description", "members")

    def __init__(self, future_admin, university_students, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.future_admin = future_admin
        self.fields["members"].queryset = university_students

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.admin_id = self.future_admin.id
        instance.university_id = self.future_admin.university_id
        if commit:
            instance.save()
            # Very important for saving members
            self.cleaned_data["members"] |= User.objects.filter(pk=self.future_admin.id)
            self.save_m2m()
        return instance


class TagFormField(forms.CharField):
    def clean(self, value):
        value = super().clean(value)
        return [t.lower().strip() for t in value.split(",") if t.strip()]


class CreateEventForm(FormWithLocationMixin, forms.ModelForm):
    phone = forms.fields.CharField(widget=forms.TextInput, label="Contact phone")
    dtstart = forms.fields.SplitDateTimeField(
        widget=forms.SplitDateTimeWidget(time_format="%H:%M", date_attrs=DATE_INPUT_ARGS),
        initial=datetime.datetime.now,
        label="From",
    )
    dtend = forms.fields.SplitDateTimeField(
        widget=forms.SplitDateTimeWidget(time_format="%H:%M", date_attrs=DATE_INPUT_ARGS),
        initial=lambda: datetime.datetime.now() + datetime.timedelta(hours=1),
        label="To",
    )
    until = forms.DateField(
        label="Last occurrence",
        widget=forms.DateInput(attrs=DATE_INPUT_ARGS),
        required=False,
    )
    summary = forms.fields.CharField(widget=forms.TextInput, label="Name")
    email = CaseInsensitiveEmail(widget=forms.TextInput, label="Contact email")
    tags = TagFormField(required=False)

    class Meta:
        model = Event
        exclude = ("location", "rso", "university")
        widgets = {"freq": forms.widgets.Select(attrs=RRULE_TYPE_CHOICE_INPUT_ATTRS)}

    # Am I breaking Liskov substitution principle? HELL YEAH.
    def __init__(self, university_id, rso_id, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.university_id = university_id
        self.rso_id = rso_id

    def clean(self):
        if self.cleaned_data["freq"] == "WEEKLY":
            if not (self.cleaned_data["until"] and self.cleaned_data["byday"]):
                raise forms.ValidationError('"Last occurrence" and "Repeat on" must be speficied for weekly events.')
        return self.cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)

        instance.university_id = self.university_id
        instance.rso_id = self.rso_id
        if commit:
            instance.save()
            for t in self.cleaned_data["tags"]:
                tag = Tag.objects.filter(text=t).first() or Tag.objects.create(text=t)
                tag.events.add(instance)
        return instance
