import os

from apps.webdriver_testing.webdriver_base import WebdriverTestCase
from apps.webdriver_testing import data_helpers
from apps.webdriver_testing.pages.site_pages import watch_page
from apps.webdriver_testing.pages.site_pages import video_language_page
from apps.webdriver_testing.pages.site_pages import video_page
from apps.webdriver_testing.data_factories import TeamVideoFactory
from apps.webdriver_testing.data_factories import TeamMemberFactory
from apps.webdriver_testing.data_factories import TeamAdminMemberFactory
from apps.webdriver_testing.data_factories import TeamManagerMemberFactory
from apps.webdriver_testing.data_factories import TeamContributorMemberFactory
from apps.webdriver_testing.data_factories import WorkflowFactory
from apps.webdriver_testing.data_factories import TeamLangPrefFactory
from apps.webdriver_testing.data_factories import UserFactory
from apps.webdriver_testing.pages.editor_pages import subtitle_editor


class TestCaseApprovalWorkflow(WebdriverTestCase):
    """TestSuite for display of Edit Subtitles button on a revision. """
    NEW_BROWSER_PER_TEST_CASE = False

    @classmethod
    def setUpClass(cls):
        super(TestCaseApprovalWorkflow, cls).setUpClass()
        cls.data_utils = data_helpers.DataHelpers()
        cls.video_lang_pg = video_language_page.VideoLanguagePage(cls)
        cls.video_pg = video_page.VideoPage(cls)

        cls.user = UserFactory.create()
        cls.owner = UserFactory.create()
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
        lang_list = ['en', 'ru', 'pt-br', 'de', 'sv']
        for language in lang_list:
            TeamLangPrefFactory.create(team=cls.team, language_code=language,
                                       preferred=True)

        cls.admin = TeamAdminMemberFactory(team=cls.team).user
        cls.contributor = TeamMemberFactory(team=cls.team).user
        cls.subs_dir = os.path.join(os.getcwd(), 'apps', 'webdriver_testing', 
                                    'subtitle_data') 


    def _upload_en_draft(self, video, subs, user, complete=False):
        auth_creds = dict(username=user.username, password='password')
        draft_data = {'language_code': 'en',
                     'video': video.pk,
                     'primary_audio_language_code': 'en',
                     'draft': open(subs),
                     'complete': int(complete),
                     'is_complete': complete,
                    }
        self.data_utils.upload_subs(video, draft_data, user=auth_creds)

    def _add_team_video(self):
        video = self.data_utils.create_video()
        tv = TeamVideoFactory(team=self.team, added_by=self.owner, video=video)
        return video, tv

    def _review_and_approve(self, tv):
        """Review and approve version.

        """
        if self.workflow.review_enabled:
            self.data_utils.complete_review_task(tv, 20, self.owner)
        if self.workflow.approve_enabled:
            self.data_utils.complete_approve_task(tv, 20, self.owner)

    def tearDown(self):
        if self.team.task_assign_policy > 10: #reset to default start value
            self.team.task_assign_policy = 10
            self.team.save()
        

    def test_draft__task_assignee(self):
        """Task assignee must Edit Subtitles via task.

        """
        video, tv = self._add_team_video()
        subs = os.path.join(self.subs_dir, 'Timed_text.en.srt')
        self._upload_en_draft(video, subs, user=self.contributor)
        self.video_lang_pg.open_video_lang_page(video.video_id, 'en')
        self.video_lang_pg.log_in(self.contributor.username, 'password')
        self.video_lang_pg.page_refresh()
        self.assertEqual(self.video_lang_pg.EDIT_VIA_TASK_TEXT,
                         self.video_lang_pg.edit_subtitles_active())


    def test_reviewer_sent_back__assignee(self):
        """Assignee must Edit Subtitles via task after transcript fails review.

        """
        video, tv = self._add_team_video()
        subs = os.path.join(self.subs_dir, 'Timed_text.en.srt')
        self._upload_en_draft(video, subs, user=self.contributor, complete=True)
        #Reject transcript in review phase
        self.data_utils.complete_review_task(tv, 30, self.admin)
        self.video_lang_pg.open_video_lang_page(video.video_id, 'en')
        self.video_lang_pg.log_in(self.contributor.username, 'password')
        self.video_lang_pg.page_refresh()
        self.assertEqual(self.video_lang_pg.EDIT_VIA_TASK_TEXT,
                         self.video_lang_pg.edit_subtitles_active())


    def test_approver_sent_back__assignee(self):
        """Edit Subtitles NOT active for transcriber when transcript fails approve.

        """
        video, tv = self._add_team_video()
        subs = os.path.join(self.subs_dir, 'Timed_text.en.srt')
        self._upload_en_draft(video, subs, user=self.contributor, complete=True)
        #Accept transcript in review phase
        self.data_utils.complete_review_task(tv, 20, self.admin)
        #Reject transcript in the approve phase
        self.data_utils.complete_approve_task(tv, 30, self.owner)

        self.video_lang_pg.open_video_lang_page(video.video_id, 'en')
        self.video_lang_pg.log_in(self.contributor.username, 'password')
        self.video_lang_pg.page_refresh()
        self.assertEqual(self.video_lang_pg.EDIT_INACTIVE_TEXT, 
                         self.video_lang_pg.edit_subtitles_active())

    def test_review_not_started__transcriber(self):
        """Transcriber must Edit Subtitles via task when waiting review.

        """
        video, tv = self._add_team_video()
        subs = os.path.join(self.subs_dir, 'Timed_text.en.srt')
        self._upload_en_draft(video, subs, user=self.contributor, complete=True)

        self.video_lang_pg.open_video_lang_page(video.video_id, 'en')
        self.video_lang_pg.log_in(self.contributor.username, 'password')
        self.video_lang_pg.page_refresh()
        self.assertEqual(self.video_lang_pg.EDIT_VIA_TASK_TEXT,
                         self.video_lang_pg.edit_subtitles_active())



    def test_approver_sent_back__reviewer(self):
        """Reviewer must Edit Subtitles via task after fails approve.

        """
        reviewer = TeamContributorMemberFactory(team=self.team).user

        video, tv = self._add_team_video()
        subs = os.path.join(self.subs_dir, 'Timed_text.en.srt')
        self._upload_en_draft(video, subs, user=self.contributor, complete=True)
        #Accept transcript in review phase
        self.data_utils.complete_review_task(tv, 20, reviewer)
        #Reject transcript in the approve phase
        self.data_utils.complete_approve_task(tv, 30, self.owner)

        self.video_lang_pg.open_video_lang_page(video.video_id, 'en')
        self.video_lang_pg.log_in(reviewer.username, 'password')
        self.video_lang_pg.page_refresh()
        self.assertEqual(self.video_lang_pg.EDIT_VIA_TASK_TEXT,
                         self.video_lang_pg.edit_subtitles_active())


    def test_draft__not_task_assignee(self):
        """Edit Subtitles not active for member not assigned with task.

        """
        member2 = TeamContributorMemberFactory(team=self.team).user

        video, tv = self._add_team_video()
        subs = os.path.join(self.subs_dir, 'Timed_text.en.srt')
        self._upload_en_draft(video, subs, user=self.contributor)
        self.video_lang_pg.open_video_lang_page(video.video_id, 'en')
        self.video_lang_pg.log_in(member2.username, 'password')
        self.video_lang_pg.page_refresh()
        self.assertEqual(self.video_lang_pg.EDIT_INACTIVE_TEXT, 
                         self.video_lang_pg.edit_subtitles_active())

    def test_draft__team_admin(self):
        """Edit Subtitles not active for admin when task started by member.

        """
        video, tv = self._add_team_video()
        subs = os.path.join(self.subs_dir, 'Timed_text.en.srt')
        self._upload_en_draft(video, subs, user=self.contributor)
        self.video_lang_pg.open_video_lang_page(video.video_id, 'en')
        self.video_lang_pg.log_in(self.admin.username, 'password')
        self.video_lang_pg.page_refresh()
        self.assertEqual(self.video_lang_pg.EDIT_INACTIVE_TEXT,  
                         self.video_lang_pg.edit_subtitles_active())

    def test_non_member_sees_no_button(self):
        """Edit Subtitles not visible for non-member.
        """
        siteuser = UserFactory.create()
        video, tv = self._add_team_video()
        subs = os.path.join(self.subs_dir, 'Timed_text.en.srt')
        self._upload_en_draft(video, subs, user=self.contributor)
        self.video_lang_pg.open_video_lang_page(video.video_id, 'en')
        self.video_lang_pg.log_in(siteuser.username, 'password')
        self.video_lang_pg.page_refresh()
        self.assertFalse(self.video_lang_pg.edit_subtitles_exists())

    def test_guest_sees_no_button(self):
        """Edit Subtitles not visible for guest.
        """
        video, tv = self._add_team_video()
        subs = os.path.join(self.subs_dir, 'Timed_text.en.srt')
        self._upload_en_draft(video, subs, user=self.contributor)
        self.video_lang_pg.open_video_lang_page(video.video_id, 'en')
        self.video_lang_pg.log_out()
        self.video_lang_pg.page_refresh()
        self.assertFalse(self.video_lang_pg.edit_subtitles_exists())

    def test_public__guest(self):
        """Guest user will not see Edit Subtitles for published version.

        """
        video, tv = self._add_team_video()
        subs = os.path.join(self.subs_dir, 'Timed_text.en.srt')
        self._upload_en_draft(video, subs, user=self.contributor, complete=True)
        self._review_and_approve(tv)
        self.video_lang_pg.open_video_lang_page(video.video_id, 'en')
        self.video_lang_pg.log_out()
        self.video_lang_pg.page_refresh()
        self.assertFalse(self.video_lang_pg.edit_subtitles_exists())

    def test_public__non_member(self):
        """Guest user will not see Edit Subtitles for published version.

        """
        siteuser = UserFactory.create()
        video, tv = self._add_team_video()
        subs = os.path.join(self.subs_dir, 'Timed_text.en.srt')
        self._upload_en_draft(video, subs, user=self.contributor, complete=True)
        self._review_and_approve(tv)
        self.video_lang_pg.open_video_lang_page(video.video_id, 'en')
        self.video_lang_pg.log_in(siteuser.username, 'password')
        self.video_lang_pg.page_refresh()
        self.assertFalse(self.video_lang_pg.edit_subtitles_exists())


    def test_public__member_with_create_tasks(self):
        """Member can edit public version when create tasks is any team member.

        """
        member2 = TeamContributorMemberFactory(team=self.team).user
        video, tv = self._add_team_video()
        subs = os.path.join(self.subs_dir, 'Timed_text.en.srt')
        self._upload_en_draft(video, subs, user=self.contributor, complete=True)
        self._review_and_approve(tv)
        self.video_lang_pg.open_video_lang_page(video.video_id, 'en')
        self.video_lang_pg.log_in(member2.username, 'password')
        self.video_lang_pg.page_refresh()
        self.assertEqual('active', self.video_lang_pg.edit_subtitles_active())

    def test_public__member_with_no_create_tasks(self):
        """Member can't edit public version when create tasks is manager level.

        """
        self.team.task_assign_policy = 30
        self.team.save()
        self.logger.info("Task assign policy: %s" % self.team.task_assign_policy)

        member2 = TeamContributorMemberFactory(team=self.team).user
        self.logger.info('Test user: %s' % member2.username)
        video, tv = self._add_team_video()
        subs = os.path.join(self.subs_dir, 'Timed_text.en.srt')
        self._upload_en_draft(video, subs, user=self.contributor, complete=True)
        self._review_and_approve(tv)
        self.video_pg.open_video_page(video.video_id)
        self.video_lang_pg.log_in(member2.username, 'password')
        self.video_lang_pg.open_video_lang_page(video.video_id, 'en')
        self.assertEqual(self.video_lang_pg.EDIT_INACTIVE_TEXT,
                         self.video_lang_pg.edit_subtitles_active())

    def test_public__manager_with_create_tasks(self):
        """Manager can edit public version when create tasks is manager level.

        """
        self.team.task_assign_policy = 20
        self.team.save()
        self.logger.info(self.team.task_assign_policy)

        teammanager = TeamManagerMemberFactory(team=self.team).user
        video, tv = self._add_team_video()
        subs = os.path.join(self.subs_dir, 'Timed_text.en.srt')
        self._upload_en_draft(video, subs, user=self.contributor, complete=True)
        self._review_and_approve(tv)
        self.video_pg.open_video_page(video.video_id)
        self.video_lang_pg.log_in(teammanager.username, 'password')
        self.video_lang_pg.open_video_lang_page(video.video_id, 'en')
        self.assertEqual('active',
                         self.video_lang_pg.edit_subtitles_active())


    def test_public__manager_with_no_create_tasks(self):
        """Manager can't edit public version when create tasks is admin level.

        """
        self.team.task_assign_policy = 30
        self.team.save()
        self.logger.info('TASK POLICY is %s' % self.team.task_assign_policy)
        tm = TeamManagerMemberFactory(team=self.team).user
        video, tv = self._add_team_video()
        subs = os.path.join(self.subs_dir, 'Timed_text.en.srt')
        self._upload_en_draft(video, subs, user=self.contributor, complete=True)
        self._review_and_approve(tv)
        self.video_pg.log_out()
        self.video_pg.open_video_page(video.video_id)
        self.video_lang_pg.log_in(tm.username, 'password')
        self.video_lang_pg.open_video_lang_page(video.video_id, 'en')
        self.assertEqual(self.video_lang_pg.EDIT_INACTIVE_TEXT,
                         self.video_lang_pg.edit_subtitles_active())

    def test_public__admin_always(self):
        """Admin can always edit public version.

        """
        self.team.task_assign_policy = 30
        self.team.save()
        self.logger.info(self.team.task_assign_policy)

        video, tv = self._add_team_video()
        subs = os.path.join(self.subs_dir, 'Timed_text.en.srt')
        self._upload_en_draft(video, subs, user=self.contributor, complete=True)
        self._review_and_approve(tv)
        self.video_pg.open_video_page(video.video_id)
        self.video_lang_pg.log_in(self.admin.username, 'password')
        self.video_lang_pg.open_video_lang_page(video.video_id, 'en')
        self.assertEqual('active',
                         self.video_lang_pg.edit_subtitles_active())

    def test_public__owner_always(self):
        """Owner can always edit public version.

        """
        self.team.task_assign_policy = 30
        self.team.save()
        self.logger.info(self.team.task_assign_policy)

        video, tv = self._add_team_video()
        subs = os.path.join(self.subs_dir, 'Timed_text.en.srt')
        self._upload_en_draft(video, subs, user=self.contributor, complete=True)
        self._review_and_approve(tv)
        self.video_pg.open_video_page(video.video_id)
        self.video_lang_pg.log_in(self.owner.username, 'password')
        self.video_lang_pg.open_video_lang_page(video.video_id, 'en')
        self.assertEqual('active',
                         self.video_lang_pg.edit_subtitles_active())



class TestCaseNoReviews(WebdriverTestCase):
    """TestSuite for display of Edit Subtitles button on a revision. """
    NEW_BROWSER_PER_TEST_CASE = False

    @classmethod
    def setUpClass(cls):
        super(TestCaseNoReviews, cls).setUpClass()
        cls.data_utils = data_helpers.DataHelpers()
        cls.video_lang_pg = video_language_page.VideoLanguagePage(cls)
        cls.video_pg = video_page.VideoPage(cls)

        cls.user = UserFactory.create()
        cls.owner = UserFactory.create()
        cls.team = TeamMemberFactory.create(team__workflow_enabled=True,
                                            team__translate_policy=20, #any team
                                            team__subtitle_policy=20, #any team
                                            team__task_assign_policy=10, #any team
                                            user = cls.owner,
                                            ).team
        cls.workflow = WorkflowFactory(team = cls.team,
                                       autocreate_subtitle=True,
                                       autocreate_translate=True,
                                       )
        lang_list = ['en', 'ru', 'pt-br', 'de', 'sv']
        for language in lang_list:
            TeamLangPrefFactory.create(team=cls.team, language_code=language,
                                       preferred=True)

        cls.admin = TeamAdminMemberFactory(team=cls.team).user
        cls.contributor = TeamMemberFactory(team=cls.team).user
        cls.subs_dir = os.path.join(os.getcwd(), 'apps', 'webdriver_testing', 
                                    'subtitle_data') 


    def _upload_en_draft(self, video, subs, user, complete=False):
        auth_creds = dict(username=user.username, password='password')
        draft_data = {'language_code': 'en',
                     'video': video.pk,
                     'primary_audio_language_code': 'en',
                     'draft': open(subs),
                     'complete': int(complete),
                     'is_complete': complete,
                    }
        self.data_utils.upload_subs(video, draft_data, user=auth_creds)

    def _add_team_video(self):
        video = self.data_utils.create_video()
        tv = TeamVideoFactory(team=self.team, added_by=self.owner, video=video)
        return video, tv

    def tearDown(self):
        if self.team.task_assign_policy > 10: #reset to default start value
            self.team.task_assign_policy = 10
            self.team.save()
        

    def test_draft__task_assignee(self):
        """Edit Subtitles active for task assignee.

        """
        video, tv = self._add_team_video()
        subs = os.path.join(self.subs_dir, 'Timed_text.en.srt')
        self._upload_en_draft(video, subs, user=self.contributor)
        self.video_lang_pg.open_video_lang_page(video.video_id, 'en')
        self.video_lang_pg.log_in(self.contributor.username, 'password')
        self.video_lang_pg.page_refresh()
        self.assertEqual('active', self.video_lang_pg.edit_subtitles_active())


    def test_draft__not_task_assignee(self):
        """Edit Subtitles active for member when task not assigned.

        """
        member2 = TeamContributorMemberFactory(team=self.team).user

        video, tv = self._add_team_video()
        subs = os.path.join(self.subs_dir, 'Timed_text.en.srt')
        self._upload_en_draft(video, subs, user=self.contributor)
        self.video_lang_pg.open_video_lang_page(video.video_id, 'en')
        self.video_lang_pg.log_in(member2.username, 'password')
        self.video_lang_pg.page_refresh()
        self.assertEqual('active', 
                         self.video_lang_pg.edit_subtitles_active())


    def test_public__non_member(self):
        """Guest user will not see Edit Subtitles for published version.

        """
        siteuser = UserFactory.create()
        video, tv = self._add_team_video()
        subs = os.path.join(self.subs_dir, 'Timed_text.en.srt')
        self._upload_en_draft(video, subs, user=self.contributor, complete=True)
        self.video_lang_pg.open_video_lang_page(video.video_id, 'en')
        self.video_lang_pg.log_in(siteuser.username, 'password')
        self.video_lang_pg.page_refresh()
        self.assertFalse(self.video_lang_pg.edit_subtitles_exists())


    def test_public__member_with_create_tasks(self):
        """Member can edit public version when create tasks is any team member.

        """
        member2 = TeamContributorMemberFactory(team=self.team).user
        video, tv = self._add_team_video()
        subs = os.path.join(self.subs_dir, 'Timed_text.en.srt')
        self._upload_en_draft(video, subs, user=self.contributor, complete=True)
        self.video_lang_pg.open_video_lang_page(video.video_id, 'en')
        self.video_lang_pg.log_in(member2.username, 'password')
        self.video_lang_pg.page_refresh()
        self.assertEqual('active', self.video_lang_pg.edit_subtitles_active())

    def test_public__member_with_no_create_tasks(self):
        """Member can't edit public version when create tasks is manager level.

        """
        self.team.task_assign_policy = 30
        self.team.save()
        self.logger.info("Task assign policy: %s" % self.team.task_assign_policy)

        member2 = TeamContributorMemberFactory(team=self.team).user
        self.logger.info('Test user: %s' % member2.username)
        video, tv = self._add_team_video()
        subs = os.path.join(self.subs_dir, 'Timed_text.en.srt')
        self._upload_en_draft(video, subs, user=self.contributor, complete=True)
        self.video_pg.open_video_page(video.video_id)
        self.video_lang_pg.log_in(member2.username, 'password')
        self.video_lang_pg.open_video_lang_page(video.video_id, 'en')
        self.assertEqual(self.video_lang_pg.EDIT_INACTIVE_TEXT,
                         self.video_lang_pg.edit_subtitles_active())

    def test_public__manager_with_create_tasks(self):
        """Manager can edit public version when create tasks is manager level.

        """
        self.team.task_assign_policy = 20
        self.team.save()
        self.logger.info(self.team.task_assign_policy)

        teammanager = TeamManagerMemberFactory(team=self.team).user
        video, tv = self._add_team_video()
        subs = os.path.join(self.subs_dir, 'Timed_text.en.srt')
        self._upload_en_draft(video, subs, user=self.contributor, complete=True)
        self.video_pg.open_video_page(video.video_id)
        self.video_lang_pg.log_in(teammanager.username, 'password')
        self.video_lang_pg.open_video_lang_page(video.video_id, 'en')
        self.assertEqual('active',
                         self.video_lang_pg.edit_subtitles_active())


    def test_public__manager_with_no_create_tasks(self):
        """Manager can't edit public version when create tasks is admin level.

        """
        self.team.task_assign_policy = 30
        self.team.save()
        self.logger.info('TASK POLICY is %s' % self.team.task_assign_policy)
        tm = TeamManagerMemberFactory(team=self.team).user
        video, tv = self._add_team_video()
        subs = os.path.join(self.subs_dir, 'Timed_text.en.srt')
        self._upload_en_draft(video, subs, user=self.contributor, complete=True)
        self.video_pg.log_out()
        self.video_pg.open_video_page(video.video_id)
        self.video_lang_pg.log_in(tm.username, 'password')
        self.video_lang_pg.open_video_lang_page(video.video_id, 'en')
        self.assertEqual(self.video_lang_pg.EDIT_INACTIVE_TEXT,
                         self.video_lang_pg.edit_subtitles_active())

    def test_public__admin_always(self):
        """Admin can always edit public version.

        """
        self.team.task_assign_policy = 30
        self.team.save()
        self.logger.info(self.team.task_assign_policy)

        video, tv = self._add_team_video()
        subs = os.path.join(self.subs_dir, 'Timed_text.en.srt')
        self._upload_en_draft(video, subs, user=self.contributor, complete=True)
        self.video_pg.open_video_page(video.video_id)
        self.video_lang_pg.log_in(self.admin.username, 'password')
        self.video_lang_pg.open_video_lang_page(video.video_id, 'en')
        self.assertEqual('active',
                         self.video_lang_pg.edit_subtitles_active())

    def test_public__owner_always(self):
        """Owner can always edit public version.

        """
        self.team.task_assign_policy = 30
        self.team.save()
        self.logger.info(self.team.task_assign_policy)

        video, tv = self._add_team_video()
        subs = os.path.join(self.subs_dir, 'Timed_text.en.srt')
        self._upload_en_draft(video, subs, user=self.contributor, complete=True)
        self.video_pg.open_video_page(video.video_id)
        self.video_lang_pg.log_in(self.owner.username, 'password')
        self.video_lang_pg.open_video_lang_page(video.video_id, 'en')
        self.assertEqual('active',
                         self.video_lang_pg.edit_subtitles_active())



class TestCaseNoWorkflow(WebdriverTestCase):
    """TestSuite for display of Edit Subtitles button on a revision. """
    NEW_BROWSER_PER_TEST_CASE = False

    @classmethod
    def setUpClass(cls):
        super(TestCaseNoWorkflow, cls).setUpClass()
        cls.data_utils = data_helpers.DataHelpers()
        cls.video_lang_pg = video_language_page.VideoLanguagePage(cls)
        cls.video_pg = video_page.VideoPage(cls)

        cls.user = UserFactory.create()
        cls.owner = UserFactory.create()
        cls.team = TeamMemberFactory.create(team__translate_policy=20, #any team
                                            team__subtitle_policy=20, #any team
                                            user = cls.owner,
                                            ).team
        cls.admin = TeamAdminMemberFactory(team=cls.team).user
        cls.contributor = TeamMemberFactory(team=cls.team).user
        cls.subs_dir = os.path.join(os.getcwd(), 'apps', 'webdriver_testing', 
                                    'subtitle_data') 


    def _upload_en_draft(self, video, subs, user, complete=False):
        auth_creds = dict(username=user.username, password='password')
        draft_data = {'language_code': 'en',
                     'video': video.pk,
                     'primary_audio_language_code': 'en',
                     'draft': open(subs),
                     'complete': int(complete),
                     'is_complete': complete,
                    }
        self.data_utils.upload_subs(video, draft_data, user=auth_creds)

    def _add_team_video(self):
        video = self.data_utils.create_video()
        tv = TeamVideoFactory(team=self.team, added_by=self.owner, video=video)
        return video, tv

    def test_draft__task_assignee(self):
        """Edit Subtitles active for task assignee.

        """
        video, tv = self._add_team_video()
        subs = os.path.join(self.subs_dir, 'Timed_text.en.srt')
        self._upload_en_draft(video, subs, user=self.contributor)
        self.video_lang_pg.open_video_lang_page(video.video_id, 'en')
        self.video_lang_pg.log_in(self.contributor.username, 'password')
        self.video_lang_pg.page_refresh()
        self.assertEqual('active', self.video_lang_pg.edit_subtitles_active())


    def test_draft__not_task_assignee(self):
        """Edit Subtitles active for members when no workflows. 

        """
        member2 = TeamContributorMemberFactory(team=self.team).user

        video, tv = self._add_team_video()
        subs = os.path.join(self.subs_dir, 'Timed_text.en.srt')
        self._upload_en_draft(video, subs, user=self.contributor)
        self.video_lang_pg.open_video_lang_page(video.video_id, 'en')
        self.video_lang_pg.log_in(member2.username, 'password')
        self.video_lang_pg.page_refresh()
        self.assertEqual('active',
                         self.video_lang_pg.edit_subtitles_active())

    def test_draft__team_admin(self):
        """Edit Subtitles active for admin when no workflows.

        """
        video, tv = self._add_team_video()
        subs = os.path.join(self.subs_dir, 'Timed_text.en.srt')
        self._upload_en_draft(video, subs, user=self.contributor)
        self.video_lang_pg.open_video_lang_page(video.video_id, 'en')
        self.video_lang_pg.log_in(self.admin.username, 'password')
        self.video_lang_pg.page_refresh()
        self.assertEqual('active',  
                         self.video_lang_pg.edit_subtitles_active())

    def test_public__non_member(self):
        """Guest user will not see Edit Subtitles for published version.

        """
        siteuser = UserFactory.create()
        video, tv = self._add_team_video()
        subs = os.path.join(self.subs_dir, 'Timed_text.en.srt')
        self._upload_en_draft(video, subs, user=self.contributor, complete=True)
        self.video_lang_pg.open_video_lang_page(video.video_id, 'en')
        self.video_lang_pg.log_in(siteuser.username, 'password')
        self.video_lang_pg.page_refresh()
        self.assertFalse(self.video_lang_pg.edit_subtitles_exists())


    def test_public__admin_always(self):
        """Admin can always edit public version.

        """
        self.team.task_assign_policy = 30
        self.team.save()
        self.logger.info(self.team.task_assign_policy)

        video, tv = self._add_team_video()
        subs = os.path.join(self.subs_dir, 'Timed_text.en.srt')
        self._upload_en_draft(video, subs, user=self.contributor, complete=True)
        self.video_pg.open_video_page(video.video_id)
        self.video_lang_pg.log_in(self.admin.username, 'password')
        self.video_lang_pg.open_video_lang_page(video.video_id, 'en')
        self.assertEqual('active',
                         self.video_lang_pg.edit_subtitles_active())

    def test_public__owner_always(self):
        """Owner can always edit public version.

        """
        self.team.task_assign_policy = 30
        self.team.save()
        self.logger.info(self.team.task_assign_policy)

        video, tv = self._add_team_video()
        subs = os.path.join(self.subs_dir, 'Timed_text.en.srt')
        self._upload_en_draft(video, subs, user=self.contributor, complete=True)
        self.video_pg.open_video_page(video.video_id)
        self.video_lang_pg.log_in(self.owner.username, 'password')
        self.video_lang_pg.open_video_lang_page(video.video_id, 'en')
        self.assertEqual('active',
                         self.video_lang_pg.edit_subtitles_active())




class TestCaseAdminUnpublish(WebdriverTestCase):
    """Edit Subtitles button display on a revision after latest version set private. """
    NEW_BROWSER_PER_TEST_CASE = False

    @classmethod
    def setUpClass(cls):
        super(TestCaseAdminUnpublish, cls).setUpClass()
        cls.data_utils = data_helpers.DataHelpers()
        cls.video_lang_pg = video_language_page.VideoLanguagePage(cls)
        cls.video_pg = video_page.VideoPage(cls)

        cls.user = UserFactory.create()
        cls.owner = UserFactory.create()
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
        lang_list = ['en', 'ru', 'pt-br', 'de', 'sv']
        for language in lang_list:
            TeamLangPrefFactory.create(team=cls.team, language_code=language,
                                       preferred=True)

        cls.admin = TeamAdminMemberFactory(team=cls.team).user
        cls.contributor = TeamMemberFactory(team=cls.team).user
        cls.subs_dir = os.path.join(os.getcwd(), 'apps', 'webdriver_testing', 
                                    'subtitle_data') 
        cls.video, cls.tv = cls._create_source_with_multiple_revisions()


    def tearDown(self):
        if self.team.task_assign_policy > 10: #reset to default start value
            self.team.task_assign_policy = 10
            self.team.save()

    @classmethod
    def _upload_en_draft(cls, video, subs, user, complete=False):
        auth_creds = dict(username=user.username, password='password')
        draft_data = {'language_code': 'en',
                     'video': video.pk,
                     'primary_audio_language_code': 'en',
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

    @classmethod
    def _create_source_with_multiple_revisions(cls):
        cls.logger.info("Create a team video with 4 revisions:")
        cls.logger.info("""
                            v1: private (draft version only)
                            v2: private (draft version only)
                            v3: public (reviewed and approved)
                            v4: public 
                        """)
        video, tv = cls._add_team_video()

        #REV1 (draft)
        rev1_subs = os.path.join(cls.subs_dir, 'Timed_text.en.srt')
        cls._upload_en_draft(video, rev1_subs, user=cls.contributor)

        #REV2 (draft - marked complete)
        rev2_subs = os.path.join(cls.subs_dir, 'Timed_text.rev2.en.srt')
        cls._upload_en_draft(video, rev2_subs, user=cls.contributor, complete=True)

        #REV3, reviewed (private)
        rev3_subs = os.path.join(cls.subs_dir, 'Timed_text.rev3.en.srt')
        cls._upload_en_draft(video, rev3_subs, user=cls.admin, complete=True)
        cls.data_utils.complete_review_task(tv, 20, cls.admin)
        cls.data_utils.complete_approve_task(tv, 20, cls.owner)


        #REV4, approved (public)
        rev4_subs = os.path.join(cls.subs_dir, 'Timed_text.rev4.en.srt')
        cls._upload_en_draft(video, rev4_subs, user=cls.owner, complete=True)
        cls.en = video.subtitle_language('en')
        en_v4 = cls.en.get_tip(public=True)
        en_v4.visibility_override = 'private'
        en_v4.save() 
        cls.video_lang_pg.open_video_lang_page(video.video_id, 'en')

        return video, tv


    def test_unpublished__member_with_create_tasks(self):
        self.logger.info(self.en.get_tip(full=True).visibility_override)
        """Unpublished version has Edit Subtitles active for member with permission.

        """
        self.video_lang_pg.log_in(self.contributor.username, 'password')
        self.video_lang_pg.open_video_lang_page(self.video.video_id, 'en')
        self.assertEqual('active', self.video_lang_pg.edit_subtitles_active())

    def test_unpublished__admin(self):
        """Admin can always edit unpublished version.

        """
        self.video_lang_pg.log_in(self.admin.username, 'password')
        self.video_lang_pg.open_video_lang_page(self.video.video_id, 'en')
        self.assertEqual('active',
                         self.video_lang_pg.edit_subtitles_active())

    def test_unpublished__owner(self):
        """Owner can always edit unpublished version.

        """
        self.video_lang_pg.log_in(self.owner.username, 'password')
        self.video_lang_pg.open_video_lang_page(self.video.video_id, 'en')
        self.assertEqual('active',
                         self.video_lang_pg.edit_subtitles_active())

    def test_unpublished__member_with_no_create_tasks(self):
        """Member can't edit unpublished version when create tasks is manager level.

        """
        self.team.task_assign_policy = 30
        self.team.save()
        team_member = TeamContributorMemberFactory(team=self.team).user
        self.video_lang_pg.log_in(team_member.username, 'password')
        self.video_lang_pg.open_video_lang_page(self.video.video_id, 'en')
        
        self.assertEqual(self.video_lang_pg.EDIT_INACTIVE_TEXT,
                         self.video_lang_pg.edit_subtitles_active())

    def test_unpublished__guest_sees_no_button(self):
        """Guest sees no Edit Subtitles button after version unpublished.

        """
        self.video_lang_pg.log_out()
        self.video_lang_pg.open_video_lang_page(self.video.video_id, 'en')
        self.assertFalse(self.video_lang_pg.edit_subtitles_exists())

    def test_unpublished__non_member_sees_no_button(self):
        """Edit Subtitles not visible for non-member.
        """
        siteuser = UserFactory.create()
        self.video_lang_pg.log_in(siteuser.username, 'password')
        self.video_lang_pg.open_video_lang_page(self.video.video_id, 'en')
        self.assertFalse(self.video_lang_pg.edit_subtitles_exists())

