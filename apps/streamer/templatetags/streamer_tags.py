# Universal Subtitles, universalsubtitles.org
#
# Copyright (C) 2011 Participatory Culture Foundation
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

from django import template

register = template.Library()

@register.inclusion_tag('streamer/_transcript-paragraph.html')
def render_transcript(video, subs):
    """
    Groups subs by paragraphs and render subs inside them as set by
    <Subtitle>.start_of_paragraph
    """
    paragraphs = []
    current_p = []
    for i,s in enumerate(subs):
        if i == 0 or s.start_of_paragraph:
            current_p = []
            paragraphs.append(current_p)
        current_p.append(s)
    return {
        'video': video,
        'paragraphs': paragraphs
    }

