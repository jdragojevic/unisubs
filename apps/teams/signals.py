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

"""Defines signals relevant to Teams.

There is quite a bit of indirection here, but the goal is to make
dispatching these events as simple as possible, since it might occur
in multiple places.

1) Client codes dispatches a signal listed in this module:
   ex: signals.api_on_subtitles_edited.send(subtitle_version)
2) The signal calls that handler, which chooses the right event name
   for the signal and calls the matching sub method (for videos, languages, etc)
3) The submethod finds all teams that should be notified (since a video)
   can belong to more than on team). For each team:
3a) Puts the right task on queue, if the teams has a TeamNotificationsSettings
3b) The taks querys the TeamNotificationSettings models to fire notifications
3c) The TNS checks if there is available data (e.g. which url to post to)
3d) Instantiates the right notification class (since specific partners must
    have their notification data massaged to their needs - e.g. changing the video
    ids to their own, or the api links to their own endpoints)
3e) The notification class fires the notification
"""

from django import dispatch


def _teams_to_notify(video):
    """
    Returns a list of teams to be notified of events releated to this
    video.
    """
    from teams.models import Team
    return list( Team.objects.filter(teamvideo__video=video, notification_settings__isnull=False))
    
def _execute_video_task(video, event_name):
    from teams import tasks as team_tasks
    from teams.models import  TeamVideo
    tvs =  list( TeamVideo.objects.filter(video=video, team__notification_settings__isnull=False))
    for tv in tvs:
        team_tasks.api_notify_on_video_activity.delay(
            tv.team.pk,
            tv.video.video_id,
            event_name
            )
    
def _execute_language_task(language, event_name):
    from teams import tasks as team_tasks
    video = language.video
    teams = _teams_to_notify(video)
    for team in teams:
        team_tasks.api_notify_on_language_activity.delay(
            team.pk,
            language.pk,
            event_name
            )
 
def _execute_version_task(version, event_name):
    from teams import tasks as team_tasks
    video = version.language.video
    teams = _teams_to_notify(video)
    for team in teams:
        team_tasks.api_notify_on_subtitles_activity.delay(
            team.pk,
            version.pk,
            event_name
            )
    
def api_on_subtitles_edited(sender, **kwargs):
    from teams.models import TeamNotificationSetting
    _execute_version_task(sender, TeamNotificationSetting.EVENT_SUBTITLE_NEW)
   

def api_on_subtitles_approved(sender, **kwargs):
    from teams.models import TeamNotificationSetting
    _execute_version_task(sender, TeamNotificationSetting.EVENT_SUBTITLE_APPROVED)

def api_on_subtitles_rejected(sender, **kwargs):
    from teams.models import TeamNotificationSetting
    _execute_version_task(sender, TeamNotificationSetting.EVENT_SUBTITLE_REJECTED)
   

def api_on_language_edited(sender, **kwargs):
    from teams.models import TeamNotificationSetting
    _execute_language_task(sender, TeamNotificationSetting.EVENT_LANGUAGE_EDITED)
    

def api_on_language_new(sender, **kwargs):
    from teams.models import TeamNotificationSetting
    _execute_language_task(sender, TeamNotificationSetting.EVENT_LANGUAGE_NEW)


def api_on_video_edited(sender, **kwargs):
    from teams.models import TeamNotificationSetting
    _execute_video_task(sender, TeamNotificationSetting.EVENT_VIDEO_EDITED)
    

def api_on_teamvideo_new(sender, **kwargs):
    from teams import tasks as team_tasks
    from teams.models import TeamNotificationSetting
    
    return team_tasks.api_notify_on_video_activity.delay(
            sender.team.pk,
            sender.video.video_id ,
            TeamNotificationSetting.EVENT_VIDEO_NEW)

#: Actual available signals
api_subtitles_edited = dispatch.Signal(providing_args=["version"])
api_subtitles_approved = dispatch.Signal(providing_args=["version"])
api_subtitles_rejected = dispatch.Signal(providing_args=["version"])
api_language_edited = dispatch.Signal(providing_args=["language"])
api_video_edited = dispatch.Signal(providing_args=["video"])
api_language_new = dispatch.Signal(providing_args=["language"])
api_teamvideo_new = dispatch.Signal(providing_args=["video"])
video_moved_from_team_to_team = dispatch.Signal(
        providing_args=["destination_team", "video"])
# connect handlers
api_subtitles_edited.connect(api_on_subtitles_edited)
api_subtitles_approved.connect(api_on_subtitles_approved)
api_subtitles_rejected.connect(api_on_subtitles_rejected)
api_language_edited.connect(api_on_language_edited)
api_language_new.connect(api_on_language_new)
api_video_edited.connect(api_on_video_edited)
api_teamvideo_new.connect(api_on_teamvideo_new)
