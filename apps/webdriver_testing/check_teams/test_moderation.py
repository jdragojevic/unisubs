# -*- coding: utf-8 -*-
import os

from apps.webdriver_testing.webdriver_base import WebdriverTestCase
from apps.webdriver_testing.data_factories import TeamMemberFactory
from apps.webdriver_testing.data_factories import TeamContributorMemberFactory
from apps.webdriver_testing.data_factories import TeamManagerMemberFactory
from apps.webdriver_testing.data_factories import TeamVideoFactory
from apps.webdriver_testing.data_factories import WorkflowFactory
from apps.webdriver_testing.data_factories import UserFactory
from apps.webdriver_testing import data_helpers
from apps.webdriver_testing.pages.site_pages import video_page
from apps.webdriver_testing.pages.site_pages import video_language_page
from apps.webdriver_testing.pages.editor_pages import unisubs_menu
from apps.webdriver_testing.pages.editor_pages import dialogs


class TestCasePublishedVideos(WebdriverTestCase):    
    NEW_BROWSER_PER_TEST_CASE = False

    @classmethod
    def setUpClass(cls):
        super(TestCasePublishedVideos, cls).setUpClass()
        cls.data_utils = data_helpers.DataHelpers()
        cls.video_pg = video_page.VideoPage(cls)
        cls.video_lang_pg = video_language_page.VideoLanguagePage(cls)
        cls.menu = unisubs_menu.UnisubsMenu(cls)
        cls.create_modal = dialogs.CreateLanguageSelection(cls)


        cls.user = UserFactory(username = 'user', is_partner=True)
        cls.data_utils.create_user_api_key(cls.user)
        #Add a team with workflows, tasks and preferred languages
        cls.logger.info('setup: Create a team with tasks enabled')
        cls.team = TeamMemberFactory.create(team__workflow_enabled=True,
                                            team__translate_policy=20,
                                            team__subtitle_policy=20,
                                            user = cls.user,
                                            ).team
        cls.team_workflow = WorkflowFactory(team = cls.team,
                                            autocreate_subtitle=True,
                                            autocreate_translate=True,
                                            approve_allowed = 10,
                                            review_allowed = 10,
                                           )
        cls.member = TeamContributorMemberFactory.create(
                team = cls.team,
                user = UserFactory(username='member')
                ).user
        cls.nonmember = UserFactory()

        #Add video to team with published subtitles
        cls.logger.info('Setup: Add video to team with published subs.')
        vid = cls.data_utils.create_video()
        cls.data_utils.upload_subs(vid)
        cls.published = TeamVideoFactory.create(
                team=cls.team, 
                video=vid,
                added_by=cls.user).video

        cls.video_pg.open_video_page(cls.published.video_id)
        cls.video_pg.set_skiphowto()


    def setUp(self):
        if self.team.subtitle_policy != 20:
            self.team.subtitle_policy=20
            self.team.save()
        if self.team.translate_policy != 20:
            self.team.translate_policy=20
            self.team.save()


    def test_subtitleme(self):
        """Subtitle Me button displayed on published transcript. """
        self.video_pg.open_video_page(self.published.video_id)
        self.assertTrue(self.video_pg.displays_subtitle_me())


    def test_video__add_subtitles(self):
        """No Add Subtitles option in the video view for moderated videos"""

        self.video_pg.open_video_page(self.published.video_id)
        self.assertFalse(self.video_pg.displays_add_subtitles())

    def test_video__upload_subtitles(self):
        """No Upload Subtitles option in the video view for moderated videos"""

        self.video_pg.open_video_page(self.published.video_id)
        self.assertFalse(self.video_pg.displays_upload_subtitles())

    def test_video__add_translation(self):
        """No Add Translation in the video view for moderated videos"""

        self.video_pg.open_video_page(self.published.video_id)
        self.assertFalse(self.video_pg.displays_add_translation())

    def test_playback(self):
        """Published version can be played on the video page."""
        self.video_pg.open_video_page(self.published.video_id)
        self.video_pg.log_in(self.member, 'password')
        self.menu.open_menu()
        self.menu.select_language('English')
        self.assertEqual('English', self.menu.visible_menu_text())

    def test_published__guest_display(self):
        """Published version is visible to guests in subtitle view"""
        self.video_pg.open_video_page(self.published.video_id)
        self.video_lang_pg.open_video_lang_page(self.published.video_id, 'en')
        self.assertTrue(self.video_lang_pg.displays_subtitles())

    def test_published__nonmember_display(self):
        """Published version is visible to non-members in subtitle view"""
        self.video_pg.open_video_page(self.published.video_id)
        self.video_pg.log_in(self.nonmember.username, 'password')
        self.video_lang_pg.open_video_lang_page(self.published.video_id, 'en')
        self.assertTrue(self.video_lang_pg.displays_subtitles())

    def test_sub_policy_members__guest(self):
        """Subtitle policy: members, guest has no improve subtitles in menu."""
        self.video_pg.open_video_page(self.published.video_id)
        self.menu.open_menu()
        self.assertFalse(self.menu.displays_improve_subtitles())

    def test_trans_policy_members__guest(self):
        """Translate policy: members, guest has no new translation in menu.

        """
        self.video_pg.log_out()
        self.video_pg.open_video_page(self.published.video_id)
        self.menu.open_menu()
        self.assertFalse(self.menu.displays_new_translation())
        self.assertTrue(self.menu.displays_moderated_message())


    def test_sub_policy_members__nonmember(self):
        """Subtitle policy: members, non-member has no improve subtitles menu.

        """
        self.video_pg.log_in(self.nonmember.username, 'password')
        self.video_pg.open_video_page(self.published.video_id)
        self.menu.open_menu()
        self.assertFalse(self.menu.displays_improve_subtitles())

    def test_trans_policy_members__nonmember(self):
        """Translate policy: members, non-member has no new translation menu.

        """
        self.video_pg.log_in(self.nonmember.username, 'password')
        self.video_pg.open_video_page(self.published.video_id)
        self.menu.open_menu()
        self.assertFalse(self.menu.displays_new_translation())

    def test_trans_policy_members__member(self):
        """Translate policy: members, member has new translation menu."""

        self.video_pg.log_in(self.member.username, 'password')
        self.video_pg.open_video_page(self.published.video_id)
        self.menu.open_menu()
        self.assertTrue(self.menu.displays_new_translation())

    def test_sub_policy_manager__member(self):
        """Subtitle policy: members, member has improve subtitles menu."""
        self.team.subtitle_policy=30
        self.team.save()
        self.video_pg.log_in(self.member.username, 'password')
        self.video_pg.open_video_page(self.published.video_id)
        self.menu.open_menu()
        self.assertFalse(self.menu.displays_improve_subtitles())

    def test_trans_policy_manager__member(self):
        """Translate policy: members, member has new translation menu."""
        self.team.translate_policy=30
        self.team.save()
        self.video_pg.log_in(self.member.username, 'password')
        self.video_pg.open_video_page(self.published.video_id)
        self.menu.open_menu()
        self.assertFalse(self.menu.displays_new_translation())


class TestCaseDraftVideos(WebdriverTestCase):    
    NEW_BROWSER_PER_TEST_CASE = False

    @classmethod
    def setUpClass(cls):
        super(TestCaseDraftVideos, cls).setUpClass()
        cls.data_utils = data_helpers.DataHelpers()
        cls.video_pg = video_page.VideoPage(cls)
        cls.video_lang_pg = video_language_page.VideoLanguagePage(cls)
        cls.menu = unisubs_menu.UnisubsMenu(cls)
        cls.create_modal = dialogs.CreateLanguageSelection(cls)


        cls.user = UserFactory(username = 'user', is_partner=True)
        cls.data_utils.create_user_api_key(cls.user)
        #Add a team with workflows, tasks and preferred languages
        cls.logger.info('setup: Create a team with tasks enabled')
        cls.team = TeamMemberFactory.create(team__workflow_enabled=True,
                                            team__subtitle_policy=20,
                                            team__translate_policy=20,
                                            user = cls.user,
                                            ).team
        cls.team_workflow = WorkflowFactory(team = cls.team,
                                            autocreate_subtitle=True,
                                            autocreate_translate=True,
                                            approve_allowed = 10,
                                            review_allowed = 10,
                                           )
        cls.member = TeamContributorMemberFactory.create(
                team = cls.team,
                user = UserFactory(username='member')
                ).user
        cls.nonmember = UserFactory()

        #Add video to team with draft subtitles
        cls.logger.info('Setup: Add video to team with draft subs.')
        cls.draft = TeamVideoFactory.create(
                team=cls.team, 
                video=cls.data_utils.create_video(),
                added_by=cls.user).video
        cls.data_utils.upload_subs(
                cls.draft, data=None, 
                user=dict(username=cls.user.username, password='password'))

        cls.video_pg.open_video_page(cls.draft.video_id)
        cls.video_pg.set_skiphowto()

    def setUp(self):
        self.team.translate_policy=20
        self.team.save()
        self.video_pg.open_video_page(self.draft.video_id)


    def test_subtitleme__draft(self):
        """No Subtitle Me button in the video view for draft transcript."""

        self.assertNotIn('Subtitle Me', self.menu.visible_menu_text())


    def test_video__add_subtitles(self):
        """No Add Subtitles option in the video view for moderated videos"""

        self.assertFalse(self.video_pg.displays_add_subtitles())

    def test_video__upload_subtitles(self):
        """No Upload Subtitles option in the video view for moderated videos"""

        self.assertFalse(self.video_pg.displays_upload_subtitles())

    def test_video__add_translation(self):
        """No Add Translation in the video view for moderated videos"""

        self.assertFalse(self.video_pg.displays_add_translation())

    def test_draft__guest_display(self):
        """Draft is not visible to guests in subtitle view."""
        self.video_lang_pg.open_video_lang_page(self.draft.video_id, 'en')
        self.assertFalse(self.video_lang_pg.displays_subtitles())

    def test_draft__nonmember_display(self):
        """Draft is not visible to non-members in subtitle view."""
        self.video_pg.log_in(self.nonmember.username, 'password')
        self.video_lang_pg.open_video_lang_page(self.draft.video_id, 'en')
        self.assertFalse(self.video_lang_pg.displays_subtitles())

    def test_draft__member_display(self):
        """Draft is visible to members in subtitle view."""
        self.video_pg.log_in(self.member.username, 'password')
        self.video_lang_pg.open_video_lang_page(self.draft.video_id, 'en')
        self.assertTrue(self.video_lang_pg.displays_subtitles())

    def test_draft__playback(self):
        """Draft can not be played on the video page."""
        self.video_pg.log_in(self.member, 'password')
        self.assertFalse(self.video_pg.displays_add_subtitles())

    def test_draft__guest_improve(self):
        """Subtitle policy: members, guest has no improve subtitles in menu."""
        self.assertFalse(self.video_pg.displays_add_subtitles())

    def test_draft__translate(self):
        """Draft can not be the source for a new translation.
        
        """
        #Opening up translation permissions, otherwise the menu is hidden
        self.team.translate_policy=10
        self.team.save()
        self.video_pg.log_in(self.member, 'password')
        self.video_pg.open_video_page(self.draft.video_id)
        self.assertFalse(self.video_pg.displays_subtitle_me())



class TestCaseViewSubtitles(WebdriverTestCase):    
    NEW_BROWSER_PER_TEST_CASE = False

    @classmethod
    def setUpClass(cls):
        super(TestCaseViewSubtitles, cls).setUpClass()
        cls.data_utils = data_helpers.DataHelpers()
        cls.video_pg = video_page.VideoPage(cls)
        cls.user = UserFactory.create()
        cls.owner = UserFactory.create()
        cls.basic_team = TeamMemberFactory.create(team__workflow_enabled=False,
                                            team__translate_policy=20, #any team
                                            team__subtitle_policy=20, #any team
                                            user = cls.owner,
                                            ).team

        cls.team = TeamMemberFactory.create(team__workflow_enabled=True,
                                            team__translate_policy=20, #any team
                                            team__subtitle_policy=20, #any team
                                            team__task_assign_policy=10, #any team
                                            user = cls.owner,
                                            ).team
        cls.workflow = WorkflowFactory(team = cls.team,
                                       autocreate_subtitle=True,
                                       autocreate_translate=True,
                                       approve_allowed = 10, # manager
                                       review_allowed = 10, # peer
                                       )
        cls.contributor = TeamContributorMemberFactory(team=cls.team).user
        cls.subs_dir = os.path.join(os.getcwd(), 'apps', 'webdriver_testing', 
                                    'subtitle_data') 
        cls.rev1 = os.path.join(cls.subs_dir, 'Timed_text.en.srt')
        cls.rev2 = os.path.join(cls.subs_dir, 'Timed_text.rev2.en.srt')
        de = os.path.join(cls.subs_dir, 'Timed_text.rev3.en.srt')

        cls.sv = os.path.join(cls.subs_dir, 'Timed_text.sv.dfxp')

        #Create en source language 2 revisions - approved.
        cls.video, cls.tv = cls._add_team_video()
        cls._upload_subtitles(cls.video, 'en', cls.rev1, cls.contributor, 
                              complete=False)
        cls._upload_subtitles(cls.video, 'en', cls.rev2, cls.contributor)
        cls.data_utils.complete_review_task(cls.tv, 20, cls.owner)
        cls.data_utils.complete_approve_task(cls.tv, 20, cls.owner)
       
        #Add sv translation, reviewed
        cls._upload_translation(cls.video, 'sv', cls.sv, cls.contributor)
        cls.data_utils.complete_review_task(cls.tv, 20, cls.owner)

        #Add de translation complete waiting review
        cls._upload_translation(cls.video, 'de', cls.sv, cls.contributor)

        #Add ru translation, incomplete.
        cls._upload_translation(cls.video, 'ru', cls.sv, cls.contributor, 
                                complete=False)

    @classmethod
    def _upload_subtitles(cls, video, lc, subs, user, complete=True):
        auth_creds = dict(username=user.username, password='password')
        draft_data = {'language_code': lc,
                     'video': video.pk,
                     'primary_audio_language_code': 'en',
                     'draft': open(subs),
                     'complete': int(complete),
                     'is_complete': complete,
                    }
        cls.data_utils.upload_subs(video, draft_data, user=auth_creds)

    @classmethod
    def _upload_translation(cls, video, lc, subs, user, complete=True):
        auth_creds = dict(username=user.username, password='password')
        draft_data = {'language_code': lc,
                     'video': video.pk,
                     'from_language_code': 'en',
                     'draft': open(subs),
                     'complete': int(complete),
                     'is_complete': complete,
                    }
        cls.data_utils.upload_subs(video, draft_data, user=auth_creds)

    @classmethod
    def _add_team_video(cls):
        video = cls.data_utils.create_video()
        tv = TeamVideoFactory(team=cls.team, added_by=cls.owner, video=video)
        return video, tv

    def setUp(self):
        self.video_pg.open_video_page(self.video.video_id)

    def tearDown(self):
        self.browser.get_screenshot_as_file('MYTMP/%s.png' % self.id())

    def test_status_img__original_complete(self):
        """Orignal lang complete, shows complete status button.

        """
        _, en_status = self.video_pg.language_status('English')
        self.assertIn('status-complete', en_status)

    def test_tags__original(self):
        """Orignal lang has original tag.

        """
        en_tag, _ = self.video_pg.language_status('English')
        self.assertEqual('original', en_tag)

    def test_tags__needs_approval(self):
        """Language awaiting approval, shows needs approval tag.

        """
        sv_tag, _ = self.video_pg.language_status('Swedish')
        self.assertEqual('needs approval', sv_tag)

    def test_tags__needs_review(self):
        """Language awaiting review, shows needs review tag.

        """
        de_tag, _ = self.video_pg.language_status('German')
        self.assertEqual('needs review', de_tag)

    def test_tags__incomplete(self):
        """Incomplete language, shows incomplete tag.

        """
        ru_tag, _ = self.video_pg.language_status('Russian')
        self.assertEqual('incomplete', ru_tag)

    def test_status_img__translation_review(self):
        """Translation lang complete, shows needs review status button.

        """
        _, sv_status = self.video_pg.language_status('Swedish')
        self.assertIn('status-needs-review', sv_status)


    def test_status_img__incomplete(self):
        """Incomplete translation displays incomplete status button.

        """
        _, ru_status = self.video_pg.language_status('Russian')
        self.assertIn('status-incomplete', ru_status)

    def test_tags__original_review(self):
        """Tag display for original language needs review."""

        vid, tv = self._add_team_video()
        self._upload_subtitles(vid, 'en', self.rev1, self.contributor, 
                              complete=True)
        self.video_pg.open_video_page(vid.video_id)
        en_tag, _ = self.video_pg.language_status('English')
        self.assertEqual('original | needs review', en_tag)

    def test_tags__original_approve(self):
        """Tag display for original language needs approval."""
        vid, tv = self._add_team_video()
        self._upload_subtitles(vid, 'en', self.rev1, self.contributor, 
                              complete=True)
        self.data_utils.complete_review_task(tv, 20, self.owner)

        self.video_pg.open_video_page(vid.video_id)
        en_tag, _ = self.video_pg.language_status('English')
        self.assertEqual('original | needs approval', en_tag)

    def test_tags__original_incomplete(self):
        vid, tv = self._add_team_video()
        self._upload_subtitles(vid, 'en', self.rev1, self.contributor, 
                              complete=False)
        self.video_pg.open_video_page(vid.video_id)
        en_tag, _ = self.video_pg.language_status('English')
        self.assertEqual('original | incomplete', en_tag)
