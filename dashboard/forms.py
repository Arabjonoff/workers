from django import forms
from main.models import *

class WorkerForm(forms.ModelForm):

    class Meta:
        model = WorkerProfile
        fields = '__all__'