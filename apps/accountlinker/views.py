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

import json
import urllib

import requests
from django.conf import settings
from django.contrib.sites.models import Site
from django.core.urlresolvers import reverse
from django.shortcuts import get_object_or_404, redirect, render_to_response

from accountlinker.models import ThirdPartyAccount
from localeurl.utils import universal_url

from teams.models import Team
from videos.models import VIDEO_TYPE_YOUTUBE
from videos.types.youtube import YouTubeApiBridge

import logging
logger = logging.getLogger("authbelt.views")


def _generate_youtube_oauth_request_link(state_str=None):
    state_str = state_str or ""
    base =  "https://accounts.google.com/o/oauth2/auth?"
    state = state_str
    
    params = {
        "client_id": settings.YOUTUBE_CLIENT_ID,
        "redirect_uri": 
            universal_url("accountlinker:youtube-oauth-callback"),
        "scope": "https://gdata.youtube.com",
        "state": state,
        "response_type": "code",
        "approval_prompt": "force",
        "access_type": "offline",
        
    }
    return "%s%s" % (base, urllib.urlencode(params))

def youtube_oauth_callback(request):
    """
    Stores the oauth tokes. We identify which team this belongs to
    since we've passed the pk on the state param for the authorize request
    """
    import atom
    code = request.GET.get("code", None)
    if code is None:
        raise Exception("No code in youtube oauth callback")
    state = request.GET.get("state", None)
    if state is None:
        raise Exception("No state in youtube oauth callback")
    values = state.split("-")
    team_pk = values[0]
    if len(values) > 1:
        project_pk = values[1]
    team = Team.objects.get(pk=team_pk)
    
    base =  "https://accounts.google.com/o/oauth2/token"
    state = team.pk
    
    params = {
        "client_id": settings.YOUTUBE_CLIENT_ID,
        "client_secret": settings.YOUTUBE_CLIENT_SECRET,
        "redirect_uri": universal_url("accountlinker:youtube-oauth-callback"),
        "code": code,
        "grant_type": "authorization_code",
        
    }
    
    response = requests.post(base, data=params, headers={
        "Content-Type": "application/x-www-form-urlencoded"
    })
    if response.status_code != 200:
        logger.error("Error on requesting Youtube Oauth token", extra={
                    "data": {
                        "sent_params": params,
                        "original_request": request,
                    },
                })
                    
    content = json.loads(response.content)
    bridge = YouTubeApiBridge(content['access_token'], content['refresh_token'], None) 
    feed = bridge.GetUserFeed(username='default')
    author = [x for x in feed.get_elements() if type(x) == atom.data.Author][0]
    
    # make sure we don't store multiple auth tokes for the same account
    account, created  = ThirdPartyAccount.objects.get_or_create(
        type = VIDEO_TYPE_YOUTUBE,
        username = author.name.text,
        defaults = {
            
        'oauth_refresh_token' : content['refresh_token'],
        'oauth_access_token' : content['access_token'],
        }
    )
    team.third_party_accounts.add(account)
    return redirect(reverse("teams:third-party-accounts", kwargs={"slug":team.slug}))
