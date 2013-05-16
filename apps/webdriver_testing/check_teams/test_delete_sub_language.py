import os

from django.core import management

from apps.webdriver_testing.webdriver_base import WebdriverTestCase
from apps.webdriver_testing import data_helpers
from apps.webdriver_testing.pages.site_pages.teams.tasks_tab import TasksTab
from apps.webdriver_testing.pages.site_pages import video_language_page
from apps.webdriver_testing.pages.site_pages import video_page
from apps.webdriver_testing.pages.site_pages import watch_page
from apps.webdriver_testing.data_factories import TeamVideoFactory
from apps.webdriver_testing.data_factories import TeamMemberFactory
from apps.webdriver_testing.data_factories import TeamAdminMemberFactory
from apps.webdriver_testing.data_factories import TeamManagerMemberFactory
from apps.webdriver_testing.data_factories import TeamContributorMemberFactory
from apps.webdriver_testing.data_factories import WorkflowFactory
from apps.webdriver_testing.data_factories import TeamLangPrefFactory
from apps.webdriver_testing.data_factories import UserFactory
from apps.webdriver_testing.pages.editor_pages import subtitle_editor


class TestCaseWorkflows(WebdriverTestCase):
    """TestSuite for display of Delete Subtitle Language button. """
    NEW_BROWSER_PER_TEST_CASE = False

    @classmethod
    def setUpClass(cls):
        super(TestCaseWorkflows, cls).setUpClass()
        cls.data_utils = data_helpers.DataHelpers()
        cls.video_lang_pg = video_language_page.VideoLanguagePage(cls)
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
        lang_list = ['en', 'ru', 'pt-br', 'de', 'sv']
        for language in lang_list:
            TeamLangPrefFactory.create(team=cls.team, language_code=language,
                                       preferred=True)

        cls.admin = TeamAdminMemberFactory(team=cls.team).user
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
        cls.data_utils.complete_review_task(cls.tv, 20, cls.admin)
        cls.data_utils.complete_approve_task(cls.tv, 20, cls.admin)
       
        #Add sv translation, reviewed
        cls._upload_translation(cls.video, 'sv', cls.sv, cls.contributor)
        cls.data_utils.complete_review_task(cls.tv, 20, cls.admin)

        #Add de translation complete waiting review
        cls._upload_translation(cls.video, 'de', cls.sv, cls.contributor)

        #Add ru translation, incomplete.
        cls._upload_translation(cls.video, 'ru', cls.sv, cls.contributor, 
                                complete=False)

        cls.video_lang_pg.open_video_lang_page(cls.video.video_id, 'en')


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

    def test_delete_button__team_admins(self):
        """Team Admins can Delete Subtitle Language.

        """
        self.video_lang_pg.log_in(self.admin.username, 'password')
        self.video_lang_pg.open_video_lang_page(self.video.video_id, 'en')
        self.assertTrue(self.video_lang_pg.delete_subtitles_language_exists())
        self.video_lang_pg.open_video_lang_page(self.video.video_id, 'sv')
        self.assertTrue(self.video_lang_pg.delete_subtitles_language_exists())


    def test_delete_button__team_owners(self):
        """Team Owners can Delete Subtitle Language.

        """
        self.video_lang_pg.log_in(self.owner.username, 'password')
        self.video_lang_pg.open_video_lang_page(self.video.video_id, 'en')
        self.assertTrue(self.video_lang_pg.delete_subtitles_language_exists())
        self.video_lang_pg.open_video_lang_page(self.video.video_id, 'sv')
        self.assertTrue(self.video_lang_pg.delete_subtitles_language_exists())


    def test_delete_button__is_staff(self):
        """Site admin (staff) can Delete Subtitle Language.

        """
        staff = UserFactory.create(is_staff=True)
        self.video_lang_pg.log_in(staff.username, 'password')
        self.video_lang_pg.open_video_lang_page(self.video.video_id, 'en')
        self.assertTrue(self.video_lang_pg.delete_subtitles_language_exists())
        self.video_lang_pg.open_video_lang_page(self.video.video_id, 'sv')
        self.assertTrue(self.video_lang_pg.delete_subtitles_language_exists())

    def test_delete_button__non_team(self):
        """Non-team videos have no Delete Subtitle Language button.

        """
        staff = UserFactory.create(is_staff=True)
        self.video_lang_pg.log_in(staff.username, 'password')
        video = self.data_utils.create_video_with_subs()

        self.video_lang_pg.open_video_lang_page(video.video_id, 'en')
        self.assertFalse(self.video_lang_pg.delete_subtitles_language_exists())

    def test_delete_button__non_workflow_team(self):
        """Non workflow team videos have Delete Subtitle Language button.

        """
        video = self.data_utils.create_video()
        tv = TeamVideoFactory(team=self.basic_team, added_by=self.owner, video=video)

        self._upload_subtitles(video, 'en', self.rev1, self.contributor)
        staff = UserFactory.create(is_staff=True)
        self.video_lang_pg.log_in(self.owner.username, 'password')

        self.video_lang_pg.open_video_lang_page(video.video_id, 'en')
        self.assertTrue(self.video_lang_pg.delete_subtitles_language_exists())


        video, tv = self._add_team_video()
        self._upload_subtitles(self.video, 'en', self.rev1, self.contributor)


    def test_delete_button__members(self):
        """Members do not see the Delete Subtitle Language button.

        """
        self.video_lang_pg.log_in(self.contributor.username, 'password')
        self.video_lang_pg.open_video_lang_page(self.video.video_id, 'en')
        self.assertFalse(self.video_lang_pg.delete_subtitles_language_exists())
        self.video_lang_pg.open_video_lang_page(self.video.video_id, 'sv')
        self.assertFalse(self.video_lang_pg.delete_subtitles_language_exists())


    def test_delete_button__non_members(self):
        """Non-members do not see the Delete Subtitle Language button.

        """
        siteuser = UserFactory.create()
        self.video_lang_pg.log_in(siteuser.username, 'password')
        self.video_lang_pg.open_video_lang_page(self.video.video_id, 'en')
        self.assertFalse(self.video_lang_pg.delete_subtitles_language_exists())
        self.video_lang_pg.open_video_lang_page(self.video.video_id, 'sv')
        self.assertFalse(self.video_lang_pg.delete_subtitles_language_exists())



    def test_dependent_languages(self):
        """Option to delete depedendent languages of source.

        """
        self.video_lang_pg.log_in(self.owner.username, 'password')
        self.video_lang_pg.open_video_lang_page(self.video.video_id, 'en')
        dsl_button = self.video_lang_pg.delete_subtitles_language_exists()
        dsl_button.click()
        self.logger.info(self.video_lang_pg.dependent_langs())
        langs, _  = self.video_lang_pg.dependent_langs()
        self.assertEqual(['Swedish', 'German', 'Russian'], langs)


    def test_forked_languages_not_listed(self):
        """Forked languages not included in delete list.

        """
        self._upload_translation(self.video, 'it', self.sv, self.contributor)
        it = self.video.subtitle_language('it')
        it.is_forked = True
        it.save()
        self.video_lang_pg.log_in(self.owner.username, 'password')
        self.video_lang_pg.open_video_lang_page(self.video.video_id, 'en')
        dsl_button = self.video_lang_pg.delete_subtitles_language_exists()
        dsl_button.click()
        langs, _  = self.video_lang_pg.dependent_langs()

        self.assertNotIn('Italian', langs)




class TestCaseDeletion(WebdriverTestCase):
    """TestSuite for display of Delete Subtitle Language button. """
    NEW_BROWSER_PER_TEST_CASE = False

    @classmethod
    def setUpClass(cls):
        super(TestCaseDeletion, cls).setUpClass()
        cls.data_utils = data_helpers.DataHelpers()
        cls.video_lang_pg = video_language_page.VideoLanguagePage(cls)
        cls.video_pg = video_page.VideoPage(cls)
        cls.tasks_tab = TasksTab(cls)
        cls.watch_pg = watch_page.WatchPage(cls)
        cls.sub_editor = subtitle_editor.SubtitleEditor(cls)

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
        cls.contributor = TeamContributorMemberFactory(team=cls.team).user
        cls.subs_dir = os.path.join(os.getcwd(), 'apps', 'webdriver_testing', 
                                    'subtitle_data') 
        cls.rev1 = os.path.join(cls.subs_dir, 'Timed_text.en.srt')
        cls.rev2 = os.path.join(cls.subs_dir, 'Timed_text.rev2.en.srt')

        cls.sv = os.path.join(cls.subs_dir, 'Timed_text.sv.dfxp')
        ru = os.path.join(cls.subs_dir, 'less_lines.ssa')



        cls.logger.info("""
                         Create video with en as primary audio lang.
                            Subtitle, review and approve.
                            Translate to: 
                                sv: reviewed
                                de: complete, needs review
                                ru: incomplete
                         Delete Subtitle Language en + sv and de.
                         """)

        #Create en source language 2 revisions - approved.
        cls.video, cls.tv = cls._add_team_video()
        cls._upload_subtitles(cls.video, 'en', cls.rev1, cls.contributor, 
                              complete=False)
        cls._upload_subtitles(cls.video, 'en', cls.rev2, cls.contributor)
        cls.data_utils.complete_review_task(cls.tv, 20, cls.admin)
        cls.data_utils.complete_approve_task(cls.tv, 20, cls.admin)
       
        #Add sv translation, reviewed
        cls._upload_translation(cls.video, 'sv', cls.sv, cls.contributor)
        cls.data_utils.complete_review_task(cls.tv, 20, cls.admin)

        #Add it translation, reviewed
        cls._upload_translation(cls.video, 'it', cls.sv, cls.contributor)
        cls.data_utils.complete_review_task(cls.tv, 20, cls.admin)

        #Add hr translation, needs review
        cls._upload_translation(cls.video, 'hr', cls.sv, cls.contributor)


        #Add de translation complete waiting review
        cls._upload_translation(cls.video, 'de', cls.sv, cls.contributor)

        #Add ru translation, incomplete.
        cls._upload_translation(cls.video, 'ru', cls.sv, cls.contributor, 
                                complete=False)

        cls.video_lang_pg.open_video_lang_page(cls.video.video_id, 'en')
        cls.video_lang_pg.log_in(cls.owner.username, 'password')
        cls.video_lang_pg.page_refresh()

        #Delete English subtitle language + Swedish and German
        cls.video_lang_pg.delete_subtitle_language(['Swedish', 'German'])


    def setUp(self):
        self.video_pg.open_video_page(self.video.video_id)
        self.video_pg.handle_js_alert('accept')

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



    def test_deleted_source__language__ui(self):
        """Deleted source language no longer listed in the ui.

        """
        self.video_pg.open_video_page(self.video.video_id)
        langs = self.video_pg.subtitle_languages()
        self.assertNotIn('English', langs)



    def test_deleted_source__searching(self):
        """Search results don't match deleted transcript text.

        """
        management.call_command('update_index', interactive=False)

        self.watch_pg.open_watch_page()
        test_text = 'This is revision 2'
        results_pg = self.watch_pg.basic_search(test_text)
        self.assertTrue(results_pg.search_has_no_results())

    def test_deleted_source__tasks(self):
        """Tasks related to deleted language are deleted.

        """
        self.tasks_tab.open_page('teams/%s/tasks/&assignee=anyone' 
                                 % self.team.slug)
        task = list(self.tv.task_set.filter(language='en'))
        self.assertEqual(0, len(task))

    def test_deleted_translations__tasks(self):
        """Tasks for deleted translations are deleted.

        """
        self.tasks_tab.open_page('teams/%s/tasks/&assignee=anyone' 
                                 % self.team.slug)

        task = list(self.tv.task_set.filter(language='sv'))
        self.assertEqual(0, len(task))
        task = list(self.tv.task_set.filter(language='de'))
        self.assertEqual(0, len(task))


    def test_deleted_translations__language__ui(self):
        """Deleted translation languages are no longer listed in the ui.

        """
        self.video_pg.open_video_page(self.video.video_id)
        langs = self.video_pg.subtitle_languages()
        self.assertNotIn('German', langs)
        self.assertNotIn('Swedish', langs)


    def test_delete_translations__searching(self):
        """Search results don't match deleted transcript text.

        """
        management.call_command('update_index', interactive=False)

        self.watch_pg.open_watch_page()
        test_text = 'This is revision 3'
        results_pg = self.watch_pg.basic_search(test_text)
        self.assertTrue(results_pg.search_has_no_results())

    def test_recreate__source_language(self):
        """Create a new task for the language after deletion.

        """ 
        self.tasks_tab.log_in(self.admin.username, 'password')
        self.tasks_tab.page_refresh()
        self.tasks_tab.open_page('teams/{0}/tasks/?team_video={1}'
                                 '&assignee=anyone'.format(
                                 self.team.slug, self.tv.pk))
        self.tasks_tab.add_task('Transcribe')
        self.assertTrue(self.tasks_tab.task_present(
                        'Transcribe Subtitles', self.video.title))


    def test_recreate__translation_language(self):
        """Create a new task for translated langauge after deletion.

        """
        video, tv = self._add_team_video()

        self._upload_subtitles(video, 'en', self.rev1, self.contributor, 
                              complete=True)
        self.data_utils.complete_review_task(tv, 20, self.admin)
        self.data_utils.complete_approve_task(tv, 20, self.admin)
       
        #Add sv translation, reviewed, approved
        self._upload_translation(video, 'sv', self.sv, self.contributor)
        self.data_utils.complete_review_task(tv, 20, self.admin)
        self.data_utils.complete_approve_task(tv, 20, self.admin)

        self.video_lang_pg.log_in(self.owner.username, 'password')
        self.video_lang_pg.page_refresh()

        self.video_lang_pg.open_video_lang_page(video.video_id, 'sv')
        #Delete Swedish subtitle language
        self.video_lang_pg.delete_subtitle_language()
        self.tasks_tab.open_page('teams/{0}/tasks/?team_video={1}'
                                 '&assignee=anyone'.format(
                                 self.team.slug, tv.pk))
        self.tasks_tab.add_task(task_type='Translate', task_language='Swedish')
        self.tasks_tab.open_page('teams/{0}/tasks/?team_video={1}'
                                 '&assignee=anyone&lang=sv'.format(
                                 self.team.slug, tv.pk))
        self.assertTrue(self.tasks_tab.task_present(
                        'Translate Subtitles into Swedish', video.title))

    def test_no_over_aggressive_deletion(self):
        """Deleting language for 1 video does not affect other video languages.

        """
        #Create first video and video subtitles
        video1, tv1 = self._add_team_video()

        self._upload_subtitles(video1, 'en', self.rev1, self.contributor, 
                              complete=True)
        self.data_utils.complete_review_task(tv1, 20, self.admin)
        self.data_utils.complete_approve_task(tv1, 20, self.admin)
       
        self._upload_translation(video1, 'sv', self.sv, self.contributor)
        self.data_utils.complete_review_task(tv1, 20, self.admin)
        self.data_utils.complete_approve_task(tv1, 20, self.admin)

        #Create second video and incomplete sv subtitles
        video2, tv2 = self._add_team_video()

        self._upload_subtitles(video2, 'en', self.rev1, self.contributor, 
                              complete=True)
        self.data_utils.complete_review_task(tv2, 20, self.admin)
        self.data_utils.complete_approve_task(tv2, 20, self.admin)
       
        self._upload_translation(video2, 'sv', self.sv, self.contributor, 
                                 complete=False)

        self.video_lang_pg.log_in(self.owner.username, 'password')
        self.video_lang_pg.page_refresh()


        self.video_lang_pg.open_video_lang_page(video1.video_id, 'en')
        #Delete English subtitle language + Swedish for video 1
        self.video_lang_pg.delete_subtitle_language(['Swedish'])
        self.tasks_tab.open_page('teams/{0}/tasks/?team_video={1}'
                                 '&assignee=anyone&lang=sv'.format(
                                 self.team.slug, tv2.pk))
        self.assertTrue(self.tasks_tab.task_present(
                        'Translate Subtitles into Swedish', video2.title))


    def test_forked_dependents(self):
        """Unchecked dependent languages are forked when source deleted.

        """
        ru = self.video.subtitle_language('ru')
        self.assertTrue(ru.is_forked)

    
    def test_forked_translations__tasks(self):
        """Tasks for forked translations are not deleted.

        """
        task = list(self.tv.task_set.filter(language='ru'))
        self.assertEqual(1, len(task), 
                         're: https://unisubs.sifterapp.com/issues/2328')

    def test_forked_review__tasks(self):
        """Review tasks for forked translations are not deleted.

        """
        self.tasks_tab.open_page('teams/{0}/tasks/?team_video={1}'
                                 '&assignee=anyone&lang=hr'.format(
                                 self.team.slug, self.tv.pk))

        task = list(self.tv.task_set.incomplete_review().filter(
                    language='hr'))
        self.assertEqual(1, len(task))
        self.assertTrue(self.tasks_tab.task_present(
                        'Review Croatian Subtitles', self.video.title))


    def test_forked_approve__tasks(self):
        """Approve tasks for forked translations are not deleted.

        """
        self.tasks_tab.open_page('teams/{0}/tasks/?team_video={1}'
                                 '&assignee=anyone&lang=it'.format(
                                 self.team.slug, self.tv.pk))

        task = list(self.tv.task_set.incomplete_approve().filter(
                    language='it'))
        self.assertEqual(1, len(task))
        self.assertTrue(self.tasks_tab.task_present(
                        'Approve Italian Subtitles', self.video.title))


    def test_perform_forked_approve_task(self):
        """Approve tasks for forked translations open in timed dialog.

        """
        self.tasks_tab.open_page('teams/{0}/tasks/?team_video={1}'
                                 '&assignee=anyone&lang=it'.format(
                                 self.team.slug, self.tv.pk))

        self.tasks_tab.perform_and_assign_task('Approve Italian Subtitles', 
                                               self.video.title)
        self.assertEqual('Approve subtitles', self.sub_editor.dialog_title())

    def test_perform_forked_review_task(self):
        """Review tasks for forked translations open in timed dialog.

        """
        self.tasks_tab.open_page('teams/{0}/tasks/?team_video={1}'
                                 '&assignee=anyone&lang=hr'.format(
                                 self.team.slug, self.tv.pk))

        self.tasks_tab.perform_and_assign_task('Review Croatian Subtitles', 
                                               self.video.title)
        self.assertEqual('Review subtitles', self.sub_editor.dialog_title())

