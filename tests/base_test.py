from django.urls import resolve, reverse
from django.core.exceptions import ImproperlyConfigured
from inspect import isfunction, isclass
from model_mommy import mommy


# CODE START

class BaseViewTest():
    url_name_space = None
    url_path = None
    view = None
    status_code = 200

    def get_url_name_space(self):
        if self.url_name_space:
            return self.url_name_space
        raise ImproperlyConfigured("Attribute url_name_space not assigned or incorrect name space defined")
    
    def get_url_path(self):
        if self.url_path:
            return self.url_path
        raise ImproperlyConfigured("Attribute url_path not assigned or incorrect url_path defined")
    
    def test_status_code(self):
        url_name = self.get_url_name_space()
        url = reverse(url_name)
        response = self.client.get(url)
        self.assertEquals(response.status_code, self.status_code)
    
    def get_view(self):
        if self.view:
            return self.view
        raise ImproperlyConfigured("Attribute view not assigned or incorrect view defined")

    def test_url_resolved(self):
        path = self.get_url_path()
        path_view = resolve(path)
        view = self.get_view()
        if isclass(view):
            self.assertEquals(path_view.func.view_class, view)
        elif isfunction(view):
            self.assertEquals(path_view.func, view)


class BaseModelTest():
    model = None

    def get_model(self):
        if self.model:
            return self.model
        raise ImproperlyConfigured("Attribute model not assigned or incorrect model defined")

    def test_create_model_object(self):
        obj = mommy.make(self.get_model())
        self.assertTrue(isinstance(obj, self.get_model()))