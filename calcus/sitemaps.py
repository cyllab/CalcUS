from django.contrib import sitemaps


class CalcUSSitemap(sitemaps.Sitemap):
    priority = 0.5
    changefreq = "monthly"

    def items(self):
        return ["home", "pricing"]

    def location(self, item):
        return f"/{item}/"
