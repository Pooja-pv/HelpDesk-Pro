from django.conf import settings
from django.db import models
from django.utils.text import slugify


class KnowledgeArticle(models.Model):
    title = models.CharField(max_length=180)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    category = models.CharField(max_length=80, default="Getting started")
    summary = models.CharField(max_length=300)
    body = models.TextField()
    is_published = models.BooleanField(default=False)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="knowledge_articles")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "title"]

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title)[:180] or "article"
            candidate = base
            suffix = 2
            while KnowledgeArticle.objects.filter(slug=candidate).exclude(pk=self.pk).exists():
                candidate = f"{base}-{suffix}"
                suffix += 1
            self.slug = candidate
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title
