# -*- coding: utf-8 -*-
# Amara, universalsubtitles.org
#
# Copyright (C) 2013 Participatory Culture Foundation
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU Affero General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more
# details.
#
# You should have received a copy of the GNU Affero General Public License along
# with this program.  If not, see http://www.gnu.org/licenses/agpl-3.0.html.
import simplejson as json
from django.contrib.auth.decorators import login_required

from videos.models import Video
from teams.models import Task
from subtitles.models import SubtitleLanguage, SubtitleVersion
from subtitles.shims import get_widget_url
from subtitles.templatetags.new_subtitles_tags import visibility_display

from django.http import HttpResponse
from django.db.models import Count
from django.contrib import messages
from django.template import RequestContext
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext as _
from django.views.decorators.http import require_POST
from django.shortcuts import render_to_response, get_object_or_404, redirect


from teams.permissions import can_add_version


def _version_data(version):
    '''
    Creates a dict with version info, suitable for encoding
    into json and bootstrapping the editor.
    '''
    return {
        'number': version.version_number,
        'subtitlesXML': version.get_subtitles().to_xml(),
        'title': version.title,
        'description': version.description,
    }

def _language_data(language, editing_version, translated_from_version):
    '''
    Creates a dict with language info, suitable for encoding
    into json and bootstrapping the editor. Includes
    the version data for the version being edited and the
    original translation source, if any.
    '''
    versions_data = []

    for version in language.subtitleversion_set.full():
        version_data = {
            'version_no':version.version_number,
            'visibility': visibility_display(version)
        }
        if editing_version and editing_version == version and \
            editing_version.subtitle_language == language:
            version_data.update(_version_data(editing_version))
        elif translated_from_version and translated_from_version == version and \
            translated_from_version.subtitle_language == language:
            version_data.update(_version_data(translated_from_version))

        versions_data.append(version_data)


    subtitle_language = editing_version.subtitle_language if editing_version else ''

    return {
        'translatedFrom': translated_from_version and {
            'language_code': translated_from_version.subtitle_language.language_code,
            'version_number': translated_from_version.version_number,
        },
        'editingLanguage': language == subtitle_language,
        'code': language.language_code,
        'name': language.get_language_code_display(),
        'pk': language.pk,
        'numVersions': language.num_versions,
        'versions': versions_data,
        'is_primary_audio_language': language.is_primary_audio_language()
    }

def regain_lock(request, video_id, language_code):
    video = get_object_or_404(Video, video_id=video_id)
    language = video.subtitle_language(language_code)

    if not language.can_writelock(request.browser_id):
        return HttpResponse(json.dumps({'ok': False}))

    language.writelock(request.user, request.browser_id, save=True)
    return HttpResponse(json.dumps({'ok': True}))

@login_required
@require_POST
def release_lock(request, video_id, language_code):
    video = get_object_or_404(Video, video_id=video_id)
    language = video.subtitle_language(language_code)

    if language.can_writelock(request.browser_id):
        language.release_writelock()

    return HttpResponse(json.dumps({'url': reverse('videos:video', args=(video_id,))}))

@login_required
def subtitle_editor(request, video_id, language_code, task_id=None):
    '''
    Renders the subtitle-editor page, with all data neeeded for the UI
    as a json object on the html document.
    If the language does not exist, it will create one and lock it.
    Also decides what source version should be shown initially (if
    it is a translation).
    '''
    # FIXME: permissions
    video = get_object_or_404(Video, video_id=video_id)

    try:
        editing_language = video.newsubtitlelanguage_set.get(language_code=language_code)
    except SubtitleLanguage.DoesNotExist:
        editing_language = SubtitleLanguage(video=video,language_code=language_code)

    if not editing_language.can_writelock(request.browser_id):
        messages.error(request, _("You can't edit this subtitle because it's locked"))
        return redirect(video)

    check_result = can_add_version(request.user, video, language_code)
    if not check_result:
        messages.error(request, check_result.message)
        return redirect(video)

    editing_language.writelock(request.user, request.browser_id, save=True)

    # if this language is a translation, show both
    editing_version = editing_language.get_tip(public=False)
    # we ignore forking because even if it *is* a fork, we still want to show
    # the user the rererence languages:
    translated_from_version = editing_language.\
        get_translation_source_version(ignore_forking=True)

    languages = video.newsubtitlelanguage_set.having_nonempty_versions().annotate(
        num_versions=Count('subtitleversion'))

    video_urls = []
    for v in video.get_video_urls():

        # Force controls for YouTube players.
        if 'youtube.com' in v.url:
            v.url = v.url + '&controls=1'

        video_urls.append(v.url)

    editor_data = {
        'allowsSyncing': bool(request.GET.get('allowsSyncing', False)),
        # front end needs this to be able to set the correct
        # api headers for saving subs
        'authHeaders': {
            'x-api-username': request.user.username,
            'x-apikey': request.user.get_api_key()
        },
        'video': {
            'id': video.video_id,
            'primaryVideoURL': video.get_video_url(),
            'videoURLs': video_urls,
        },
        'languages': [_language_data(lang, editing_version, translated_from_version) for lang in languages],
        'languageCode': request.LANGUAGE_CODE,
        'oldEditorURL': get_widget_url(editing_language)
    }

    task = task_id and Task.objects.get(pk=task_id)
    if task:
        editor_data['task_id'] = task.id
        editor_data['task_needs_pane'] = task.get_type_display() in ('Review', 'Approve')
        editor_data['team_slug'] = task.team.slug

    return render_to_response("subtitles/subtitle-editor.html", {
        'video': video,
        'language': editing_language,
        'other_languages': languages,
        'version': editing_version,
        'translated_from_version': translated_from_version,
        'task': task,
        'editor_data': json.dumps(editor_data, indent=4)
    }, context_instance=RequestContext(request))

