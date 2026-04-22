from django import forms

from engine.widgets import IntegerMultiWidget


class IntegerMultiField(forms.MultiValueField):
    widget = IntegerMultiWidget

    def __init__(self, *args, **kwargs):
        list_fields = [forms.IntegerField(required=False, min_value=0) for x in range(10)]
        super(IntegerMultiField, self).__init__(list_fields, *args, **kwargs)

    def compress(self, data_list):
        if data_list:
            return ','.join(str(x if x is not None else 0) for x in data_list)
        return ""
