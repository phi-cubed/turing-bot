from django import forms

class IntegerMultiWidget(forms.MultiWidget):
    def __init__(self, attrs=None):
        widgets = [forms.TextInput(attrs={'size': 2, 'class': 'multi-form-control'}) for x in range(10)]
        super().__init__(widgets, attrs)

    def decompress(self, value):
        if value is None:
            return ['']*10
        return value.split(',')
