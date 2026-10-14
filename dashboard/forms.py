from django import forms
from .models import KnowledgeArticle


class KnowledgeArticleForm(forms.ModelForm):
    class Meta:
        model = KnowledgeArticle
        fields = ["title", "category", "summary", "body", "is_published"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Reset your company password"}),
            "category": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Account access"}),
            "summary": forms.TextInput(attrs={"class": "form-control", "placeholder": "A short summary to help employees choose this guide"}),
            "body": forms.Textarea(attrs={"class": "form-control", "rows": 12, "placeholder": "Write the guide, steps, and troubleshooting notes..."}),
            "is_published": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }
