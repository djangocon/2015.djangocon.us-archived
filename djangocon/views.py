import json
import tablib
import unicodecsv

from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.contrib.sites.models import get_current_site
from django.contrib.sites.models import Site
from django.core.urlresolvers import reverse
from django.http import HttpResponse
from symposion.proposals.models import ProposalBase
from symposion.reviews.models import ProposalResult
from symposion.reviews.views import access_not_permitted
from symposion.schedule.models import Slot
from symposion.sponsorship.models import Sponsor
from unidecode import unidecode


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


@login_required
def schedule_guidebook(request):
    headers = (
        'Session Title',
        'Date',
        'Time Start',
        'Time End',
        'Room/Location',
        'Schedule Track (Optional)',
        'Description (Optional)'
    )

    slots = Slot.objects.all().order_by('start')
    data = []
    for slot in slots:
        # authors = slot.content.speakers() if hasattr(slot.content, 'speakers') else []

        if slot.content_override:
            name = slot.content_override.raw
        else:
            name = slot.content.title if hasattr(slot.content, 'title') else ''

        description = slot.content.description.raw if hasattr(slot.content, 'description') else ''
        description = unidecode(description)
        description = description.replace('\r', '')
        description = description.replace('\n', '<br>')
        room_location = ', '.join(room['name'] for room in slot.rooms.values())
        track = slot.content.proposal.get_audience_level_display() if hasattr(slot.content, 'proposal') else ''

        if track == 'Not Applicable':
            track = 'N/A'

        slot_data = [
            name,
            slot.day.date.isoformat(),
            slot.start.isoformat(),
            slot.end.isoformat(),
            room_location,
            track,
            description,
        ]

        data.append(slot_data)

    data = tablib.Dataset(*data, headers=headers)

    response = HttpResponse(
        data.xlsx,
        content_type='application/vnd.ms-excel'
    )
    response['Content-Disposition'] = 'attachment; filename="guidebook_schedule.xls"'
    return response


@login_required
def guidebook_sponsor_export(request):
    content_type = 'text/csv'
    response = HttpResponse(content_type=content_type)
    response['Content-Disposition'] = 'attachment; filename="guidebook_sponsors.csv"'

    writer = unicodecsv.writer(response, quoting=unicodecsv.QUOTE_ALL)
    writer.writerow([
        'Name',
        'Sub-Title (i.e. Location, Table/Booth, or Title/Sponsorship Level)',
        'Description (Optional)',
        'Location/Room',
        'Image (Optional)'
    ])

    sponsors = Sponsor.objects.active()
    for sponsor in sponsors:
        writer.writerow([
            sponsor.name,
            sponsor.level.name,
            sponsor.listing_text,
            '',
            'https://{0}{1}'.format(
                Site.objects.get_current().domain,
                sponsor.website_logo.url
            )
        ])

    return response
