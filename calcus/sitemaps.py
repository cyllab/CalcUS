from django.contrib import sitemaps
from django.urls import reverse


class CalcUSSitemap(sitemaps.Sitemap):
    priority = 0.5
    changefreq = "monthly"

    def items(self):
        return ["frontend:home", "frontend:pricing"]

    def location(self, item):
        return reverse(item)
