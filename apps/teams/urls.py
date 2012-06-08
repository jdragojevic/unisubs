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

from django.conf.urls.defaults import url, patterns
from teams.rpc import rpc_router

urlpatterns = patterns('teams.views',
    url(r'^$', 'index', name='index'),
    url(r'^my/$', 'index', {'my_teams': True}, name='user_teams'),
    url(r'^create/$', 'create', name='create'),
    url(r'^router/$', rpc_router, name='rpc_router'),
    url(r'^router/api/$', rpc_router.api, name='rpc_api'),
    url(r'^tasks/perform/$', 'perform_task', name='perform_task'),
    url(r'^invite/accept/(?P<invite_pk>\d+)/$', 'accept_invite', name='accept_invite'),
    url(r'^invite/deny/(?P<invite_pk>\d+)/$', 'accept_invite', {'accept': False}, name='deny_invite'),
    url(r'^join_team/(?P<slug>[-\w]+)/$', 'join_team', name='join_team'),
    url(r'^leave_team/(?P<slug>[-\w]+)/$', 'leave_team', name='leave_team'),
    url(r'^highlight/(?P<slug>[-\w]+)/$', 'highlight', name='highlight'),
    url(r'^unhighlight/(?P<slug>[-\w]+)/$', 'highlight', {'highlight': False}, name='unhighlight'),
    url(r'^applications/(?P<slug>[-\w]+)/$', 'applications', name='applications'),
    url(r'^application/approve/(?P<slug>[-\w]+)/(?P<user_pk>\d+)/$', 'approve_application', name='approve_application'),
    url(r'^application/deny/(?P<slug>[-\w]+)/(?P<user_pk>\d+)/$', 'deny_application', name='deny_application'),
    url(r'^move/$', 'move_video', name='move_video'),
    url(r'^add/video/(?P<slug>[-\w]+)/$', 'add_video', name='add_video'),
    url(r'^add/videos/(?P<slug>[-\w]+)/$', 'add_videos', name='add_videos'),
    url(r'^edit/video/(?P<team_video_pk>\d+)/$', 'team_video', name='team_video'),
    url(r'^remove/video/(?P<team_video_pk>\d+)/$', 'remove_video', name='remove_video'),
    url(r'^remove/members/(?P<slug>[-\w]+)/(?P<user_pk>\d+)/$', 'remove_member', name='remove_member'),
    url(r'^(?P<slug>[-\w]+)/$', 'dashboard', name='dashboard'),
    url(r'^(?P<slug>[-\w]+)/videos/$', 'videos_list', name='videos_list'),
    url(r'^(?P<slug>[-\w]+)/members/$', 'detail_members', name='detail_members'),
    url(r'^(?P<slug>[-\w]+)/members/role-saved/$', 'role_saved', name='role_saved'),
    url(r'^(?P<slug>[-\w]+)/members/invite/$', 'invite_members', name='invite_members'),
    url(r'^(?P<slug>[-\w]+)/members/search/$', 'search_members', name='search_members'),
    url(r'^(?P<slug>[-\w]+)/members/(?P<role>[-\w]+)/$', 'detail_members', name='detail_members_role'),
    url(r'^(?P<slug>[-\w]+)/activity/$', 'activity', name='activity'),
    url(r'^(?P<slug>[-\w]+)/projects/$', 'project_list', name='project_list'),
    url(r'^(?P<slug>[-\w]+)/tasks/$', 'team_tasks', name='team_tasks'),
    url(r'^(?P<slug>[-\w]+)/create-task/(?P<team_video_pk>\d+)/$', 'create_task', name='create_task'),
    url(r'^(?P<slug>[-\w]+)/delete-task/$', 'delete_task', name='delete_task'),
    url(r'^(?P<slug>[-\w]+)/upload-draft/$', 'upload_draft', name='upload_draft'),
    url(r'^(?P<slug>[-\w]+)/(?P<task_pk>\d+)/download/(?P<type>[-\w]+)/$', 'download_draft', name='download_draft'),
    url(r'^(?P<slug>[-\w]+)/assign-task/$', 'assign_task', name='assign_task'),
    url(r'^(?P<slug>[-\w]+)/assign-task/a/$', 'assign_task_ajax', name='assign_task_ajax'),
    url(r'^(?P<slug>[-\w]+)/tasks/(?P<task_pk>\d+)/perform/$', 'perform_task', name='perform_task'),
    url(r'^(?P<slug>[-\w]+)/settings/$', 'settings_basic', name='settings_basic'),
    url(r'^(?P<slug>[-\w]+)/settings/guidelines/$', 'settings_guidelines', name='settings_guidelines'),
    url(r'^(?P<slug>[-\w]+)/settings/permissions/$', 'settings_permissions', name='settings_permissions'),
    url(r'^(?P<slug>[-\w]+)/settings/languages/$', 'settings_languages', name='settings_languages'),
    url(r'^(?P<slug>[-\w]+)/settings/projects/$', 'settings_projects', name='settings_projects'),
    url(r'^(?P<slug>[-\w]+)/settings/projects/add/$', 'add_project', name='add_project'),
    url(r'^(?P<slug>[-\w]+)/settings/projects/(?P<project_slug>[-\w]+)/$', 'edit_project', name='edit_project'),
    # just /p/ will bring all videos on any projects
    url(r'^(?P<slug>[-\w]+)/p/(?P<project_slug>[-\w]+)?/?$', 'videos_list', name='project_video_list'),
    # TODO: Review these...
    url(r'^(?P<slug>[-\w]+)/p/(?P<project_slug>[-\w]+)/tasks/?$', 'team_tasks', name='project_tasks'),
    url(r'^(?P<slug>[-\w]+)/third-party-accounts/$', 'third_party_accounts', name='third-party-accounts'),
    url(r'^(?P<slug>[-\w]+)/unpublish/$', 'unpublish', name='unpublish'),
    url(r'^(?P<slug>[-\w]+)/auto-captions-status/$', 'auto_captions_status', name='auto-captions-status'),
)

urlpatterns += patterns('',
    (r'^t1$', 'django.views.generic.simple.direct_to_template', {
        'template': 'jsdemo/teams_profile.html'
    }),
)

