# Amara, universalsubtitles.org
#
# Copyright (C) 2012 Participatory Culture Foundation
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see
# http://www.gnu.org/licenses/agpl-3.0.html.

import re

from utils.subtitles import MAX_SUB_TIME, strip_tags, DEFAULT_ALLOWED_TAGS
import markdown2

UNSYNCED_MARKER = -1
BOLD_TAG_RE = re.compile("</?s*b\s*>", re.IGNORECASE)
ITALIC_TAG_RE = re.compile("</?s*i\s*>", re.IGNORECASE)

def markdown_to_html(text):
    """
    This is, unfortunately, not as direct as traslating to html.
    Subs expect B tags (not STRONG) and so forth.
    This is pretty naive, but we shouldn't be accepting complex
    or broken input.
    """
    html = markdown2.markdown(text)
    html = html.replace("<strong>", "<b>")
    html = html.replace("</strong>", "</b>")
    html = html.replace("<em>", "<i>")
    html = html.replace("</em>", "</i>")
    return strip_tags(html)

def html_to_markdown(text):
    """
    Very naive html to markdown converter. No parsing just
    a regex hack, since we don't need actual an actual tree, our
    content can be 1 depth level only. Should look into a more
    robust solution in the near future.
    """
    safe_html = strip_tags(text)
    safe_html = BOLD_TAG_RE.sub("**", safe_html)
    safe_html = ITALIC_TAG_RE.sub("*", safe_html)
    return safe_html

def is_synced_value(v):
    return v != UNSYNCED_MARKER and v != None and v < MAX_SUB_TIME

def is_synced(obj):
    if obj.start_time is None or obj.end_time is None:
        return False
    return is_synced_value(obj.start_time) and is_synced_value(obj.start_time)

def format_time(time):
    if not is_synced_value(time):
         return ""
    t = int(round(time))
    s = t % 60
    s = s > 9 and s or '0%s' % s
    return '%s:%s' % (t / 60, s)


class EffectiveSubtitle:
    def __init__(self, subtitle_id, text, start_time, end_time, sub_order, pk, start_of_paragraph=False):
        self.subtitle_id = subtitle_id
        self.text = text
        if start_time is None:
            start_time = UNSYNCED_MARKER
        self.start_time = start_time
        if end_time is None:
            end_time = UNSYNCED_MARKER

        self.end_time = end_time
        self.sub_order = sub_order
        self.pk = pk
        self.start_of_paragraph = start_of_paragraph

    def as_dict(self):
        return {
            'subtitle_id': self.subtitle_id,
            'text': self.text,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'start_of_paragraph': self.start_of_paragraph,
            'sub_order': self.sub_order
        }

    def has_complete_timing(self):
        return is_synced(self)

    def for_generator(self):
        """
        This is used in serializers for download (srt, dxfp)
        """
        return {
            'text': markdown_to_html(self.text),
            'start': self.start_time,
            'end': self.end_time,
            'id': self.pk,
            'start_of_paragraph': self.start_of_paragraph,
        }

    def has_same_timing(self, subtitle):
        return self.start_time == subtitle.start_time and \
            self.end_time == subtitle.end_time

    @classmethod
    def for_subtitle(cls, subtitle):
        return EffectiveSubtitle(
            subtitle.subtitle_id,
            subtitle.subtitle_text,
            subtitle.start_time,
            subtitle.end_time,
            subtitle.subtitle_order,
            subtitle.pk,
            subtitle.start_of_paragraph,
        )

    @classmethod
    def for_dependent_translation(cls, original, translation):
        """
        Return a EffectiveSubtitle from a pair of
        videos.Subtitle instance with the id borrowed from the original
        """
        return EffectiveSubtitle(
            original.subtitle_id,
            translation.subtitle_text,
            original.start_time,
            original.end_time,
            original.subtitle_order,
            original.pk,
            original.start_of_paragraph,
        )

    def duplicate_for(self):
        from videos.models import Subtitle
        return Subtitle(
            subtitle_id=self.subtitle_id,
            subtitle_order=self.sub_order,
            subtitle_text=self.text,
            start_time=self.start_time,
            end_time=self.end_time,
            start_of_paragraph = self.start_of_paragraph,
        )

    @property
    def has_start_time(self):
        return self.start_time != UNSYNCED_MARKER

    @property
    def has_end_time(self):
        return self.end_time != UNSYNCED_MARKER
