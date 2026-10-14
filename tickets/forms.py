from django import forms
from django.contrib.auth import get_user_model
from .models import Ticket, TicketComment

User = get_user_model()


class TicketCreateForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ["title", "description", "category", "priority"]
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "Briefly describe the issue"}),
            "description": forms.Textarea(attrs={"rows": 5, "placeholder": "What happened? What did you expect? Include any useful details."}),
            "category": forms.TextInput(attrs={"placeholder": "e.g. IT & Access, Facilities, HR"}),
        }


class TicketUpdateForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ["status", "priority", "assigned_to"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["assigned_to"].queryset = User.objects.filter(is_staff=True, is_active=True).order_by("first_name", "username")
        self.fields["assigned_to"].required = False
        self.fields["assigned_to"].empty_label = "Unassigned"


class TicketCommentForm(forms.ModelForm):
    class Meta:
        model = TicketComment
        fields = ["message"]
        widgets = {"message": forms.Textarea(attrs={"rows": 3, "placeholder": "Share an update or ask a question..."})}
        labels = {"message": "Add to the conversation"}
