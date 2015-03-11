from django.conf import settings
from django.conf.urls import include, patterns, url
from django.conf.urls.static import static
from django.views.generic import TemplateView

from django.contrib import admin
admin.autodiscover()

import symposion.views
import djangocon.views

# from pinax.apps.account.openid_consumer import PinaxConsumer

WIKI_SLUG = r"(([\w-]{2,})(/[\w-]{2,})*)"
urlpatterns = patterns("")

if 'comps' in settings.INSTALLED_APPS:
    urlpatterns += patterns('', url(r'^', include('comps.urls')))

urlpatterns += patterns(
    "",
    url(r"^$",
        # TemplateView.as_view(template_name="splash.html"),
        TemplateView.as_view(template_name="homepage.html"),
        name="home"),
    url(r"^admin/", include(admin.site.urls)),

    url(r"^account/signup/$", symposion.views.SignupView.as_view(), name="account_signup"),
    url(r"^account/login/$", symposion.views.LoginView.as_view(), name="account_login"),
    url(r"^account/", include("account.urls")),
    url(r'^contact/', include('contact_form.urls')),
    url(r"^schedule/json/$", djangocon.views.schedule_json, name="schedule_json"),

    url(r"^blog/", include("biblion.urls")),
    url(r"^dashboard/", symposion.views.dashboard, name="dashboard"),
    url(r"^speaker/", include("symposion.speakers.urls")),
    url(r"^proposals/", include("symposion.proposals.urls")),
    url(r"^sponsors/", include("symposion.sponsorship.urls")),
    url(r"^boxes/", include("symposion.boxes.urls")),
    url(r"^teams/", include("symposion.teams.urls")),
    url(r"^reviews/", include("symposion.reviews.urls")),
    url(r"^schedule/", include("symposion.schedule.urls")),
    url(r"^markitup/", include("markitup.urls")),

    url(r"^", include("symposion.cms.urls")),
)


urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
