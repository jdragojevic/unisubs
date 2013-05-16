from apps.videos.models import Video
from django.core.urlresolvers import reverse
from apps.webdriver_testing.data_factories import UserFactory
from apps.webdriver_testing.data_factories import TeamVideoFactory
from apps.webdriver_testing.data_factories import VideoFactory
from apps.webdriver_testing.data_factories import VideoUrlFactory
from apps.teams.models import TeamMember
import simplejson
import requests
from apps.testhelpers.views import _create_videos
from tastypie.models import ApiKey
from django.http import HttpResponse
from django.test.client import RequestFactory, Client
from django.contrib.sites.models import Site
from django.db import IntegrityError
import logging

class DataHelpers(object):
    def __init__(self):
        self.logger = logging.getLogger('test_steps')
        self.logger.setLevel(logging.INFO)


    def create_user_api_key(self, user_obj):
        c = Client()
        c.login(username=user_obj.username, password='password')
        factory = RequestFactory()
        request = factory.get('/profiles/edit')
        key, created = ApiKey.objects.get_or_create(user=user_obj)
        if not created:
            key.key = key.generate_key()
            key.save()
        response =  HttpResponse(simplejson.dumps({"key":key.key}))
        return response


    def response_data(self, r):
        status = r.status_code
        json_resp = r.json
        content_resp = r.content
        if json_resp == None:
            return status, content_resp
        else:
            return status, json_resp

    def api_url(self, url_part):
        base_url = 'http://%s/' % Site.objects.get_current().domain
        if url_part.startswith('http'):
            return url_part
        elif url_part.startswith('/api2/partners'):
            return (base_url + url_part[1:])
        else:
            return (base_url + 'api2/partners/' + url_part)


    def post_api_request(self, user, url_part, data):
        r = requests
        url = self.api_url(url_part)
        headers = { 'Content-Type': 'application/json',
                    'Accept': 'application/json',
                    'X-apikey': user.api_key.key,
                    'X-api-username': user.username,
                  } 
        req = r.post(url, data=simplejson.dumps(data), headers=headers)
        return self.response_data(req) 


    def put_api_request(self, user, url_part, data):
        r = requests
        url = self.api_url(url_part)
        headers = { 'Content-Type': 'application/json',
                    'Accept': 'application/json',
                    'X-apikey': user.api_key.key,
                    'X-api-username': user.username,
                  } 

        req = r.put(url, data=simplejson.dumps(data), headers=headers)
        return self.response_data(req) 

    def delete_api_request(self, user, url_part):
 
        url = self.api_url(url_part)
        headers = { 'Content-Type': 'application/json',
                    'Accept': 'application/json',
                    'X-apikey': user.api_key.key,
                    'X-api-username': user.username,
                  } 

        r = requests.delete(url, headers=headers)
        return r.status_code, r.content

    def api_get_request(self, user, url_part, output_type='json'):
        url = self.api_url(url_part)
    
        headers = { 'Content-Type': 'application/json',
                    'Accept': 'application/json',
                    'X-apikey': user.api_key.key,
                    'X-api-username': user.username,
                  }
        r = requests.get(url, headers=headers)
        return r.status_code, getattr(r, output_type)


    def create_video(self, **kwargs):
        try:         
            v = VideoUrlFactory(**kwargs).video
        except IntegrityError:
            v, _ = Video.get_or_create_for_url(video_url = kwargs['url'])
        self.logger.info('Video: %s' % v.video_id)
        return v
           

    def super_user(self):
        superuser = UserFactory(is_partner=True, 
                                 is_staff=True, 
                                 is_superuser=True) 
        auth = dict(username=superuser.username, password='password')
        return auth


    def upload_subs(self, video, data=None, user=None):
        if not data:
            data = {'language_code': 'en',
                    'video': video.pk,
                    'primary_audio_language_code': 'en',
                    'draft': open('apps/webdriver_testing/subtitle_data/'
                            'Timed_text.en.srt'),
                    'is_complete': True,
                    'complete': 1
                    }
        c = Client()
        if user:
            c.login(**user)
        else:
            c.login(**self.super_user())
        response = c.post(reverse('videos:upload_subtitles'), data)
        self.logger.info('UPLOAD RESPONSE %s' % response)
        return response


    def create_video_with_subs(self, video_url=None, data=None):
        """Create a video and subtitles.
    
        """
        if video_url is None:
            video_url = 'http://qa.pculture.org/amara_tests/Birds_short.webmsd.webm'
        video = self.create_video(url=video_url)
        self.upload_subs(video, data)
        return video


    def create_several_team_videos_with_subs(self, team, teamowner, data=None):
        """Uses the helper data from the apps.videos.fixtures to create data.

           The test vidoes are then assigned to the specified team.
           Returns the list of video.
        """
        if not data:
            testdata = simplejson.load(open('apps/videos/fixtures/teams-list.json'))
        else:
            testdata = simplejson.load(open(data))
        videos = _create_videos(testdata, [])
        for video in videos:
            TeamVideoFactory.create(
                team=team, 
                video=video, 
                added_by=teamowner)
        return videos


    def create_videos_with_fake_subs(self, testdata=None):
        if testdata is None:
            testdata = simplejson.load(open('apps/videos/fixtures/teams-list.json'))
        else:
            testdata = simplejson.load(open(testdata))
        videos = _create_videos(testdata, [])
        return videos

    def complete_review_task(self, tv, status_code, assignee):
        """Complete the review task, 20 for approve, 30 for reject.
 
        Making the assumtion that I have only 1 at a time.

        """
        task = list(tv.task_set.incomplete_review().all())[0]
        task.assignee = assignee
        task.approved = status_code
        task.save()
        task.complete()

    def complete_approve_task(self, tv, status_code, assignee):
        """Complete the approve task, 20 for approve, 30 for reject.
 
        Making the assumtion that I have only 1 at a time.

        """
        task = list(tv.task_set.incomplete_approve().all())[0]
        task.assignee = assignee 
        task.approved = status_code
        task.save()
        task.complete()
