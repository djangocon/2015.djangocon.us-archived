import json
import os
import StringIO
import unicodecsv

from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.contrib.sites.models import get_current_site
from django.contrib.sites.models import Site
from django.core.urlresolvers import reverse
from django.http import Http404, HttpResponse
from symposion.proposals.models import ProposalBase
from symposion.reviews.models import ProposalResult
from symposion.reviews.views import access_not_permitted
from symposion.schedule.models import Slot
from symposion.sponsorship.models import Sponsor
from zipfile import ZipFile, ZIP_DEFLATED


def json_serializer(obj):
    if isinstance(obj, datetime.time):
        return obj.strftime("%H:%M")
    raise TypeError


def duration(start, end):
    start_dt = datetime.strptime(start.isoformat(), "%H:%M:%S")
    end_dt = datetime.strptime(end.isoformat(), "%H:%M:%S")
    delta = end_dt - start_dt
    return delta.seconds // 60


@login_required
def proposal_export(request):
    if not request.user.is_superuser:
        return access_not_permitted(request)

    content_type = 'text/csv'
    response = HttpResponse(content_type=content_type)
    response['Content-Disposition'] = 'attachment; filename="proposal_export.csv"'

    domain = get_current_site(request).domain
    writer = unicodecsv.writer(response, quoting=unicodecsv.QUOTE_ALL)
    writer.writerow([
        'id',
        'proposal_type',
        'speaker',
        'speaker_email',
        'title',
        'audience_level',
        'kind',
        'recording_release',
        'comment_count',
        'plus_one',
        'plus_zero',
        'minus_zero',
        'minus_one',
        'review_detail'
    ])

    proposals = ProposalBase.objects.all().select_subclasses().order_by('id')
    for proposal in proposals:
        try:
            proposal.result
        except ProposalResult.DoesNotExist:
            ProposalResult.objects.get_or_create(proposal=proposal)

        writer.writerow([
            proposal.id,
            proposal._meta.module_name,
            proposal.speaker,
            proposal.speaker.email,
            proposal.title,
            proposal.get_audience_level_display(),
            proposal.kind,
            proposal.recording_release,
            proposal.result.comment_count,
            proposal.result.plus_one,
            proposal.result.plus_zero,
            proposal.result.minus_zero,
            proposal.result.minus_one,
            'https://{0}{1}'.format(domain, reverse('review_detail',
                                                    args=[proposal.pk])),
        ])
    return response


def schedule_json(request):
    slots = Slot.objects.all().order_by("start")
    data = []
    for slot in slots:
        if slot.kind.label in ["talk", "tutorial", "plenary"] and slot.content and slot.content.proposal.kind.slug in ["talk", "tutorial"]:
            if hasattr(slot.content.proposal, "recording_release"):
                slot_data = {
                    "name": slot.content.title,
                    "room": ", ".join(room["name"] for room in slot.rooms.values()),
                    "start": datetime.combine(slot.day.date, slot.start).isoformat(),
                    "end": datetime.combine(slot.day.date, slot.end).isoformat(),
                    "duration": duration(slot.start, slot.end),
                    "authors": [s.name for s in slot.content.speakers()],
                    "released": slot.content.proposal.recording_release,
                    "license": "",
                    "contact": [s.email for s in slot.content.speakers()] if request.user.is_staff else ["redacted"],
                    "abstract": slot.content.abstract.raw,
                    "description": slot.content.description.raw,
                    "conf_key": slot.pk,
                    "conf_url": "https://%s%s" % (
                        Site.objects.get_current().domain,
                        reverse("schedule_presentation_detail", args=[slot.content.pk])
                    ),

                    "kind": slot.content.proposal.kind.slug,
                    "tags": "",
                }
        elif slot.kind.label == "lightning":
            slot_data = {
                "name": slot.content_override.raw if slot.content_override else "Lightning Talks",
                "room": ", ".join(room["name"] for room in slot.rooms.values()),
                "start": datetime.combine(slot.day.date, slot.start).isoformat(),
                "end": datetime.combine(slot.day.date, slot.end).isoformat(),
                "duration": duration(slot.start, slot.end),
                "authors": None,
                "released": True,
                "license": "",
                "contact": None,
                "abstract": "Lightning Talks",
                "description": "Lightning Talks",
                "conf_key": slot.pk,
                "conf_url": None,
                "kind": slot.kind.label,
                "tags": "",
            }
        else:
            continue
        data.append(slot_data)

    return HttpResponse(
        json.dumps(data, default=json_serializer),
        content_type="application/json"
    )


# with print logos and json reformat
@login_required
def export_sponsors(request):
    if not request.user.is_staff:
        raise Http404()

    # use StringIO to make zip in memory, rather than on disk
    f = StringIO.StringIO()
    z = ZipFile(f, 'w', ZIP_DEFLATED)
    data = []

    # collect the data and write web and print logo assets for each sponsor
    for sponsor in Sponsor.objects.all():
        data.append({
            'name': sponsor.name,
            'website': sponsor.external_url,
            'description': sponsor.listing_text,
            'contact name': sponsor.contact_name,
            'contact email': sponsor.contact_email,
            'level': str(sponsor.level),
        })
        if sponsor.website_logo:
            path = sponsor.website_logo.path
            z.write(path, '{0}_weblogo{1}'.format(
                str(sponsor.name).replace(' ', ''),
                os.path.splitext(path)[1]))
        if sponsor.print_logo:
            path = sponsor.print_logo.path
            z.write(path, '{0}_printlogo{1}'.format(
                str(sponsor.name).replace(' ', ''),
                os.path.splitext(path)[1]))

    # write sponsor data to text file for zip
    with open('sponsor_data.txt', 'wb') as d:
        json.dump(data, d, encoding='utf-8', indent=4)
    z.write('sponsor_data.txt')

    z.close()

    response = HttpResponse(mimetype='application/zip')
    response['Content-Disposition'] = 'attachment; filename=sponsor_file.zip'
    f.seek(0)
    response.write(f.getvalue())
    f.close()
    return response
