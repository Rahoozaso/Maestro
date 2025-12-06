import json

from django.contrib import admin
from django.contrib.admin.sites import AdminSite
from django.db import models
from django.db.models import JSONField
from django.test import RequestFactory, TestCase


class JSONModel(models.Model):
    data = JSONField()

    class Meta:
        app_label = "admin_jsonfield_tests"


@admin.register(JSONModel)
class JSONModelAdmin(admin.ModelAdmin):
    readonly_fields = ("data",)


class DummySite(AdminSite):
    pass


class JSONFieldReadonlyDisplayTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.site = DummySite()
        self.model_admin = JSONModelAdmin(JSONModel, self.site)

    def test_readonly_jsonfield_display_is_valid_json(self):
        instance = JSONModel.objects.create(data={"foo": "bar"})
        request = self.factory.get("/")
        field = JSONModel._meta.get_field("data")

        # Use the admin readonly_fields machinery to obtain the rendered value
        # for the JSONField. We don't assert on the surrounding HTML here; the
        # key point is that the inner value is valid JSON rather than a Python
        # dict representation.
        form = self.model_admin.get_form(request, obj=instance)()
        value = instance.data

        from django.contrib.admin.utils import display_for_field

        rendered = display_for_field(value, field, empty_value_display="")

        # The rendered value should be parseable JSON and should round-trip to
        # the original data structure.
        parsed = json.loads(rendered)
        self.assertEqual(parsed, {"foo": "bar"})

    def test_readonly_jsonfield_display_for_string_value(self):
        # If the JSONField stores a JSON string already, ensure we don't
        # double-encode it.
        json_string = "{""foo"": ""bar""}"
        instance = JSONModel.objects.create(data=json.loads(json_string))
        request = self.factory.get("/")
        field = JSONModel._meta.get_field("data")

        from django.contrib.admin.utils import display_for_field

        rendered = display_for_field(instance.data, field, empty_value_display="")

        # Should be valid JSON and equivalent to the original serialized form.
        parsed = json.loads(rendered)
        self.assertEqual(parsed, json.loads(json_string))