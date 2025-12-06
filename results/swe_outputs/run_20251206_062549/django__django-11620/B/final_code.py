from django.http import Http404
from django.test import SimpleTestCase, override_settings
from django.urls import path, register_converter, resolve, Resolver404


class Http404Converter:
    regex = r"[0-9]+"

    def to_python(self, value):
        # For testing, always raise Http404 to assert propagation.
        raise Http404("Object not found from converter")

    def to_url(self, value):
        return str(value)


class ValueErrorConverter:
    regex = r"[0-9]+"

    def to_python(self, value):
        # For testing, always raise ValueError to assert 'no match' behavior.
        raise ValueError("Invalid value for converter")

    def to_url(self, value):
        return str(value)


register_converter(Http404Converter, "http404")
register_converter(ValueErrorConverter, "valueerr")


urlpatterns = [
    path("obj/<http404:pk>/", lambda request, pk: None, name="obj-404"),
    path("obj/<valueerr:pk>/", lambda request, pk: None, name="obj-value-error"),
]


class ConverterHttp404Tests(SimpleTestCase):
    # Use the urlpatterns defined above.
    urls = __name__

    def test_value_error_in_converter_causes_no_match(self):
        """ValueError should keep current behavior: URL pattern is treated
        as not matching and Resolver404 is raised after trying remaining
        patterns.
        """
        with self.assertRaises(Resolver404):
            resolve("/obj/123/")

    @override_settings(DEBUG=True)
    def test_http404_in_converter_debug_true(self):
        """Under DEBUG=True, Http404 from the converter should propagate and
        ultimately result in a technical 404 if used via the client.
        At the resolver level, we expect Http404 to bubble up.
        """
        with self.assertRaises(Http404):
            resolve("/obj/1/")

    @override_settings(DEBUG=False)
    def test_http404_in_converter_debug_false(self):
        """Under DEBUG=False, the resolver still propagates Http404, which
        the handler converts into a normal 404 response. This test simply
        asserts the propagation behavior at the resolver layer.
        """
        with self.assertRaises(Http404):
            resolve("/obj/1/")