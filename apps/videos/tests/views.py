# -*- coding: utf-8 -*-
# Amara, universalsubtitles.org
#
# Copyright (C) 2013 Participatory Culture Foundation
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see
# http://www.gnu.org/licenses/agpl-3.0.html.

from datetime import datetime
import json
from BeautifulSoup import BeautifulSoup

from babelsubs.storage import SubtitleSet, diff
from django.core import mail
from django.core.cache import cache
from django.core.urlresolvers import reverse
from django.db.models import ObjectDoesNotExist
from django.test import TestCase
from vidscraper.sites import blip

from apps.auth.models import CustomUser as User
from apps.subtitles import pipeline
from apps.teams.models import Task
from apps.teams.permissions_const import ROLE_ADMIN
from apps.videos.share_utils import _make_email_url
from apps.videos.tasks import video_changed_tasks
from apps.videos.templatetags.subtitles_tags import format_sub_time
from apps.videos.tests.videotestutils import (
    WebUseTest, create_langs_and_versions
)
from apps.videos.views import LanguageList, LanguageListItem
from apps.videos.models import (
    Video, VideoUrl, Action, VIDEO_TYPE_YOUTUBE, SubtitleVersion,
    SubtitleLanguage, Subtitle, UserTestResult
)
from apps.videos.tests.data import (
    get_video, make_subtitle_language, make_subtitle_version
)
from apps.widget import video_cache
from apps.widget.tests import create_two_sub_session, RequestMockup
from utils import test_factories

class TestViews(WebUseTest):
    fixtures = ['test.json', 'subtitle_fixtures.json']

    def setUp(self):
        self._make_objects("iGzkk7nwWX8F")
        cache.clear()

    def tearDown(self):
        mail.outbox = []

    def test_video_url_make_primary(self):
        self._login()
        v = Video.objects.get(video_id='iGzkk7nwWX8F')
        self.assertNotEqual(len(VideoUrl.objects.filter(video=v)), 0)
        # add another url
        secondary_url = 'http://www.youtube.com/watch?v=po0jY4WvCIc'
        data = {
            'url': secondary_url,
            'video': v.pk
        }
        url = reverse('videos:video_url_create')
        response = self.client.post(url, data)
        self.assertNotIn('errors', json.loads(response.content))
        vid_url = 'http://www.youtube.com/watch?v=rKnDgT73v8s'
        # test make primary
        vu = VideoUrl.objects.filter(video=v)
        vu[0].make_primary()
        self.assertEqual(VideoUrl.objects.get(video=v, primary=True).url, vid_url)
        # check for activity
        self.assertEqual(len(Action.objects.filter(video=v, action_type=Action.EDIT_URL)), 1)
        vu[1].make_primary()
        self.assertEqual(VideoUrl.objects.get(video=v, primary=True).url, secondary_url)
        # check for activity
        self.assertEqual(len(Action.objects.filter(video=v, action_type=Action.EDIT_URL)), 2)
        # assert correct VideoUrl is retrieved
        self.assertEqual(VideoUrl.objects.filter(video=v)[0].url, secondary_url)

    def test_video_url_make_primary_team_video(self):
        v = Video.objects.get(video_id='KKQS8EDG1P4')
        self.assertNotEqual(VideoUrl.objects.filter(video=v).count(), 0)
        # add another url
        secondary_url = 'http://www.youtube.com/watch?v=tKTZoB2Vjuk'
        data = {
            'url': secondary_url,
            'video': v.pk
        }
        url = reverse('videos:video_url_create')
        response = self.client.post(url, data)
        # before logging in, this should not work
        self.assertEqual(302, response.status_code)
        self.client.login(**self.auth)
        response = self.client.post(url, data)
        self.assertNotIn('errors', json.loads(response.content))
        vid_url = 'http://www.youtube.com/watch?v=KKQS8EDG1P4'
        # test make primary
        vu = VideoUrl.objects.filter(video=v)
        self.assertTrue(vu.count() > 1)
        vu[0].make_primary()
        self.assertEqual(VideoUrl.objects.get(video=v, primary=True).url, vid_url)
        # check for activity
        self.assertEqual(len(Action.objects.filter(video=v, action_type=Action.EDIT_URL)), 1)
        vu[1].make_primary()
        self.assertEqual(VideoUrl.objects.get(video=v, primary=True).url, secondary_url)
        # check for activity
        self.assertEqual(len(Action.objects.filter(video=v, action_type=Action.EDIT_URL)), 2)
        # assert correct VideoUrl is retrieved
        self.assertEqual(VideoUrl.objects.filter(video=v)[0].url, secondary_url)

    def test_index(self):
        self._simple_test('videos.views.index')

    def test_feedback(self):
        data = {
            'email': 'test@test.com',
            'message': 'Test',
            'math_captcha_field': 100500,
            'math_captcha_question': 'test'
        }
        response = self.client.post(reverse('videos:feedback'), data)
        self.assertEqual(response.status_code, 200)

    def test_create(self):
        self._login()
        url = reverse('videos:create')

        self._simple_test('videos:create')

        data = {
            'video_url': 'http://www.youtube.com/watch?v=osexbB_hX4g&feature=popular'
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)

        try:
            video = Video.objects.get(videourl__videoid='osexbB_hX4g',
                                      videourl__type=VIDEO_TYPE_YOUTUBE)
        except Video.DoesNotExist:
            self.fail()

        self.assertEqual(response['Location'], 'http://testserver' +
                                               video.get_absolute_url())

        len_before = Video.objects.count()
        data = {
            'video_url': 'http://www.youtube.com/watch?v=osexbB_hX4g'
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len_before, Video.objects.count())
        self.assertEqual(response['Location'], 'http://testserver' +
                                               video.get_absolute_url())

    def test_video_url_create(self):
        self._login()
        v = Video.objects.all()[:1].get()

        user = User.objects.exclude(id=self.user.id)[:1].get()
        user.notify_by_email = True
        user.is_active = True
        user.valid_email = True
        user.save()
        v.followers.add(user)
        initial_count = len(mail.outbox)

        data = {
            'url': u'http://www.youtube.com/watch?v=po0jY4WvCIc&feature=grec_index',
            'video': v.pk
        }
        url = reverse('videos:video_url_create')
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 200)
        try:
            v.videourl_set.get(videoid='po0jY4WvCIc')
        except ObjectDoesNotExist:
            self.fail()
        self.assertEqual(len(mail.outbox), initial_count + len(v.notification_list()))

    def test_video_url_remove(self):
        self._login()
        v = Video.objects.get(video_id='iGzkk7nwWX8F')
        # add another url since primary can't be removed
        data = {
            'url': 'http://www.youtube.com/watch?v=po0jY4WvCIc',
            'video': v.pk
        }
        url = reverse('videos:video_url_create')
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 200)
        vid_urls = VideoUrl.objects.filter(video=v)
        self.assertEqual(len(vid_urls), 2)
        vurl_id = vid_urls[1].id
        # check cache
        self.assertEqual(len(video_cache.get_video_urls(v.video_id)), 2)
        response = self.client.get(reverse('videos:video_url_remove'), {'id': vurl_id})
        # make sure get is not allowed
        self.assertEqual(response.status_code, 405)
        # check post
        response = self.client.post(reverse('videos:video_url_remove'), {'id': vurl_id})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(VideoUrl.objects.filter(video=v)), 1)
        self.assertEqual(len(Action.objects.filter(video=v, \
            action_type=Action.DELETE_URL)), 1)
        # assert cache is invalidated
        self.assertEqual(len(video_cache.get_video_urls(v.video_id)), 1)

    def test_video_url_deny_remove_primary(self):
        self._login()
        v = Video.objects.get(video_id='iGzkk7nwWX8F')
        vurl_id = VideoUrl.objects.filter(video=v)[0].id
        # make primary
        vu = VideoUrl.objects.filter(video=v)
        vu[0].make_primary()
        response = self.client.post(reverse('videos:video_url_remove'), {'id': vurl_id})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(len(VideoUrl.objects.filter(video=v)), 1)

    def test_video(self):
        self.video.title = 'title'
        self.video.save()
        response = self.client.get(self.video.get_absolute_url(), follow=True)
        self.assertEqual(response.status_code, 200)

        self.video.title = ''
        self.video.save()
        response = self.client.get(self.video.get_absolute_url(), follow=True)
        self.assertEqual(response.status_code, 200)

    def test_access_video_page_no_original(self):
        request = RequestMockup(User.objects.all()[0])

        session = create_two_sub_session(request)
        video_pk = session.language.video.pk
        video = Video.objects.get(pk=video_pk)

        video.primary_audio_language_code = ''
        video.save()

        video_changed_tasks.delay(video_pk)

        response = self.client.get(reverse('videos:history', args=[video.video_id]))
        # Redirect for now, until we remove the concept of SubtitleLanguages
        # with blank language codes.
        self.assertEqual(response.status_code, 302)

    def test_bliptv_twice(self):
        VIDEO_FILE = 'http://blip.tv/file/get/Kipkay-AirDusterOfficeWeaponry223.m4v'
        old_video_file_url = blip.video_file_url
        blip.video_file_url = lambda x: VIDEO_FILE
        Video.get_or_create_for_url('http://blip.tv/file/4395490')
        blip.video_file_url = old_video_file_url
        # this test passes if the following line executes without throwing an error.
        Video.get_or_create_for_url(VIDEO_FILE)

    def test_legacy_history(self):
        # TODO: write tests
        pass

    def test_stop_notification(self):
        # TODO: write tests
        pass

    def test_subscribe_to_updates(self):
        # TODO: write test
        pass

    def test_email_friend(self):
        self._simple_test('videos:email_friend')

        data = {
            'from_email': 'test@test.com',
            'to_emails': 'test1@test.com,test@test.com',
            'subject': 'test',
            'message': 'test',
            'math_captcha_field': 100500,
            'math_captcha_question': 'test'
        }
        response = self.client.post(reverse('videos:email_friend'), data)
        self.assertEqual(response.status_code, 302)
        self.assertEquals(len(mail.outbox), 1)

        self._login()
        data['link'] = 'http://someurl.com'
        mail.outbox = []
        response = self.client.post(reverse('videos:email_friend'), data)
        self.assertEqual(response.status_code, 302)
        self.assertEquals(len(mail.outbox), 1)

        msg = u'Hey-- just found a version of this video ("Tú - Jennifer Lopez") with captions: http://unisubs.example.com:8000/en/videos/OcuMvG3LrypJ/'
        url = _make_email_url(msg)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_history(self):
        # Redirect for now, until we remove the concept of SubtitleLanguages
        # with blank language codes.
        self._simple_test('videos:history',
            [self.video.video_id], status=302)

        self._simple_test('videos:history',
            [self.video.video_id], data={'o': 'user', 'ot': 'asc'}, status=302)

        sl = self.video.subtitlelanguage_set.all()[:1].get()
        sl.language = 'en'
        sl.save()
        self._simple_test('videos:translation_history',
            [self.video.video_id, sl.language, sl.id])

    def _test_rollback(self):
        #TODO: Seems like roll back is not getting called (on models)
        self._login()

        version = self.video.version(0)
        last_version = self.video.version(public_only=False)

        self._simple_test('videos:rollback', [version.id], status=302)

        new_version = self.video.version()
        self.assertEqual(last_version.version_no+1, new_version.version_no)

    def test_model_rollback(self):
        video = get_video()

        sl_en = make_subtitle_language(video, 'en')
        en1 = make_subtitle_version(sl_en, [])
        en2 = make_subtitle_version(sl_en, [(1, 2, "foo")])

        self._login()

        def _assert_tip_subs(subs):
            self.assertEqual([(start, end, txt) for start, end, txt, meta in
                              list(sl_en.get_tip().get_subtitles())],
                             subs)

        # Ensure the rollback works through the view.
        self.client.get(reverse('videos:rollback', args=[en1.id]))
        _assert_tip_subs([])

        self.client.get(reverse('videos:rollback', args=[en2.id]))
        _assert_tip_subs([(1, 2, 'foo')])

        self.assertEqual(sl_en.subtitleversion_set.full().count(), 4)

    def test_diffing(self):
        create_langs_and_versions(self.video, ['en'])

        eng = self.video.newsubtitlelanguage_set.get(language_code='en')
        subtitles = SubtitleSet.from_list('en', [
            (10000, 20000, "1 - :D"),
            (20000, 30000, "2 - :D"),
            (30000, 40000, "3 - :D"),
            (40000, 50000, "4 - :D"),
            (50000, 60000, "5 - :D"),
        ])
        subtitles2 = SubtitleSet.from_list('en', [
            (10000, 20000, "1 - :D"),
            (20000, 25000, "2 - :D"), # time change,
            (30000, 40000, "Three - :D"), # text change,
            # multiple lines replaced by a single line
            (40000, 60000, "45 - :D"),
        ])
        first_version = eng.add_version(subtitles=subtitles)
        second_version = eng.add_version(subtitles=subtitles2)
        # Note on the argument order to diff: we always diff the more recent
        # version against the less recent
        diff_result = diff(subtitles2, subtitles)

        response = self._simple_test('videos:diffing', [first_version.id, second_version.id])
        self.assertEquals(diff_result, response.context['diff_data'])

        diff_sub_data = diff_result['subtitle_data']

        html = BeautifulSoup(response.content)
        diff_list = html.find('ol', {"class":'subtitles-diff'})
        diff_items = diff_list.findAll('li')
        # check number of lines
        self.assertEquals(len(diff_items), len(diff_sub_data))
        def check_column_data(column, sub_data):
            """Check the data in the HTML for a column against the data in
            from diff()
            """
            # special check for empty lines
            if sub_data.text is None:
                self.assertEquals(column.string.strip(), "")
                return
            time_span, text_span = column.findAll('span', recursive=False)
            self.assertEquals(text_span.string.strip(),
                              sub_data.text)
            time_child_spans = time_span.findAll('span',
                                                 {'class': 'stamp_text'})
            self.assertEquals(time_child_spans[0].string.strip(),
                              format_sub_time(sub_data.start_time))
            self.assertEquals(time_child_spans[1].string.strip(),
                              format_sub_time(sub_data.end_time))

        for li, diff_sub_data_item in zip(diff_items, diff_sub_data):
            # Intuitively, left_column should be compared against
            # ['subtitles'][0], but we do the opposite.  This is because of
            # the way things are ordered:
            #  - diff() was passed (older_version, newer_version)
            #  - The rendered HTML has the newer version on the left and the
            #  older version on the right
            check_column_data(li.find('div', {'class': 'left_column'}),
                              diff_sub_data_item['subtitles'][1])
            check_column_data(li.find('div', {'class': 'right_column'}),
                              diff_sub_data_item['subtitles'][0])
            # we use the time_change class for either text or time changes.
            time_changes = li.findAll('span', {'class': 'time_change'})
            if (diff_sub_data_item['time_changed'] or
                diff_sub_data_item['text_changed']):
                self.assertNotEqual(len(time_changes), 0)
            else:
                self.assertEquals(len(time_changes), 0)

    def test_test_form_page(self):
        self._simple_test('videos:test_form_page')

        data = {
            'email': 'test@test.ua',
            'task1': 'test1',
            'task2': 'test2',
            'task3': 'test3'
        }
        response = self.client.post(reverse('videos:test_form_page'), data)
        self.assertEqual(response.status_code, 302)

        try:
            UserTestResult.objects.get(**data)
        except UserTestResult.DoesNotExist:
            self.fail()

    def test_search(self):
        self._simple_test('search:index')

    def test_counter(self):
        self._simple_test('counter')

    def test_test_mp4_page(self):
        self._simple_test('test-mp4-page')

    def test_test_ogg_page(self):
        self._simple_test('test-ogg-page')

    def test_opensubtitles2010_page(self):
        self._simple_test('opensubtitles2010_page')

    def test_faq_page(self):
        self._simple_test('faq_page')

    def test_about_page(self):
        self._simple_test('about_page')

    def test_policy_page(self):
        self._simple_test('policy_page')

    def test_volunteer_page_category(self):
        self._login()
        categories = ['featured', 'popular', 'requested', 'latest']
        for category in categories:
            url = reverse('videos:volunteer_category',
                          kwargs={'category': category})

            response = self.client.post(url)
            self.assertEqual(response.status_code, 200)


class MakeLanguageListTestCase(TestCase):
    def setUp(self):
        self.video = test_factories.create_video(
            primary_audio_language_code='en')

    def setup_team(self):
        self.team = test_factories.create_team(workflow_enabled=True)
        workflow = self.team.get_workflow()
        workflow.review_allowed = workflow.REVIEW_IDS['Admin must review']
        workflow.approve_allowed = workflow.APPROVE_IDS['Admin must approve']
        workflow.save()
        self.user = test_factories.create_team_member(self.team).user
        self.team_video = test_factories.create_team_video(self.team,
                                                           self.user,
                                                           self.video)

    def add_completed_subtitles(self, language, subtitles, **kwargs):
        language = self.add_not_completed_subtitles(language, subtitles,
                                                    **kwargs)
        language.subtitles_complete = True
        language.save()
        return language

    def add_not_completed_subtitles(self, language, subtitles, **kwargs):
        v = pipeline.add_subtitles(self.video, language, subtitles, **kwargs)
        return v.subtitle_language

    def test_original(self):
        lang = self.add_completed_subtitles('en', [
            (0, 1000, "Hello, ", {'new_paragraph':True}),
            (1500, 2500, "World"),
        ])
        self.assertEquals(LanguageList(self.video).items, [
            ('English', 'complete', ['original'], lang.get_absolute_url()),
        ])

    def test_original_incomplete(self):
        lang = self.add_not_completed_subtitles('en', [
            (0, 1000, "Hello, ", {'new_paragraph':True}),
            (1500, 2500, "World"),
        ])
        self.assertEquals(LanguageList(self.video).items, [
            ('English', 'incomplete', ['original', 'incomplete'],
             lang.get_absolute_url()),
        ])

    def test_complete(self):
        lang = self.add_completed_subtitles('ar', [
            (0, 1000, "Hello, ", {'new_paragraph':True}),
            (1500, 2500, "World"),
        ])
        self.assertEquals(LanguageList(self.video).items, [
            ('Arabic', 'complete', [], lang.get_absolute_url()),
        ])

    def test_not_marked_complete(self):
        lang = self.add_not_completed_subtitles('fr', [
            (0, 1000, "Hello, ", {'new_paragraph':True}),
            (1500, 2500, "World"),
        ])
        self.assertEquals(LanguageList(self.video).items, [
            ('French', 'incomplete', ['incomplete'], lang.get_absolute_url()),
        ])

    def test_timing_incomplete(self):
        lang = self.add_not_completed_subtitles('ja', [
            (0, 1000, "Hello, ", {'new_paragraph':True}),
            (None, None, "World"),
        ])
        self.assertEquals(LanguageList(self.video).items, [
            ('Japanese', 'needs-timing', ['incomplete'], lang.get_absolute_url()),
        ])

    def test_needs_review(self):
        self.setup_team()
        # go through the subtitle task phase
        task = Task(team=self.team, team_video=self.team_video,
             language='en', type=Task.TYPE_IDS['Subtitle'],
             assignee=self.user)
        lang = self.add_completed_subtitles('en', [
            (0, 1000, "Hello, ", {'new_paragraph':True}),
            (1500, 2500, "World"),
        ], visibility='private')
        task.new_subtitle_version = lang.get_tip(public=False)
        review_task = task.complete()
        # now in the review phase
        self.assertEquals(review_task.type, Task.TYPE_IDS['Review'])
        self.assertEquals(LanguageList(self.video).items, [
            ('English', 'needs-review', ['original', 'needs review'],
             lang.get_absolute_url()),
        ])

    def test_needs_approval(self):
        self.setup_team()
        # go through the subtitle task phase
        task = Task(team=self.team, team_video=self.team_video,
             language='en', type=Task.TYPE_IDS['Subtitle'],
             assignee=self.user)
        lang = self.add_completed_subtitles('en', [
            (0, 1000, "Hello, ", {'new_paragraph':True}),
            (1500, 2500, "World"),
        ], visibility='private')
        task.new_subtitle_version = lang.get_tip(public=False)
        review_task = task.complete()
        # go through the review phase
        self.assertEquals(review_task.type, Task.TYPE_IDS['Review'])
        review_task.assignee = self.user
        review_task.approved = Task.APPROVED_IDS['Approved']
        approve_task = review_task.complete()
        # now in the approval phase
        self.assertEquals(approve_task.type, Task.TYPE_IDS['Approve'])
        self.assertEquals(LanguageList(self.video).items, [
            ('English', 'needs-review', ['original', 'needs approval'],
             lang.get_absolute_url()),
        ])

    def test_sent_back(self):
        self.setup_team()
        # go through the subtitle task phase
        task = Task(team=self.team, team_video=self.team_video,
             language='en', type=Task.TYPE_IDS['Subtitle'],
             assignee=self.user)
        lang = self.add_completed_subtitles('en', [
            (0, 1000, "Hello, ", {'new_paragraph':True}),
            (1500, 2500, "World"),
        ], visibility='private')
        task.new_subtitle_version = lang.get_tip(public=False)
        review_task = task.complete()
        # have the video get sent back in the review phase
        self.assertEquals(review_task.type, Task.TYPE_IDS['Review'])
        review_task.assignee = self.user
        review_task.approved = Task.APPROVED_IDS['Rejected']
        new_subtitle_task = review_task.complete()
        # now in the approval phase
        self.assertEquals(new_subtitle_task.type, Task.TYPE_IDS['Subtitle'])
        self.assertEquals(LanguageList(self.video).items, [
            ('English', 'needs-review', ['original', 'needs editing'],
             lang.get_absolute_url()),
        ])

    def test_no_lines(self):
        pipeline.add_subtitles(self.video, 'pt', None)
        self.assertEquals(LanguageList(self.video).items, [ ])

    def test_multiple_languages(self):
        # english is the original, completed language
        en = self.add_completed_subtitles('en', [
            (0, 1000, "Hello, ", {'new_paragraph':True}),
            (1500, 2500, "World"),
        ])
        # Kurdish is completed
        ar = self.add_completed_subtitles('ar', [
            (0, 1000, "Hello, ", {'new_paragraph':True}),
            (1500, 2500, "World"),
        ])
        # french is incomplete
        fr = self.add_not_completed_subtitles('fr', [
            (0, 1000, "Hello, ", {'new_paragraph':True}),
            (1500, 2500, "World"),
        ])
        # japanese is incomplete, and timing is missing
        ja = self.add_not_completed_subtitles('ja', [
            (0, 1000, "Hello, ", {'new_paragraph':True}),
            (None, None, "World"),
        ])
        # portuguese shouldn't be listed because there are no lines
        pipeline.add_subtitles(self.video, 'pt', None)

        # LanguageList should return lines for all the languages, with
        # the original first, then the rest in alphabetical order.
        self.assertEquals(LanguageList(self.video).items, [
            ('English', 'complete', ['original'], en.get_absolute_url()),
            ('Arabic', 'complete', [], ar.get_absolute_url()),
            ('French', 'incomplete', ['incomplete'], fr.get_absolute_url()),
            ('Japanese', 'needs-timing', ['incomplete'], ja.get_absolute_url()),
        ])
