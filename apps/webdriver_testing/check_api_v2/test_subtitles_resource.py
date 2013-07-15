import os
import time
import codecs
from apps.webdriver_testing.webdriver_base import WebdriverTestCase
from apps.webdriver_testing.pages.site_pages import video_language_page
from apps.webdriver_testing import data_helpers
from apps.webdriver_testing.data_factories import UserFactory
from apps.webdriver_testing.data_factories import TeamMemberFactory
from apps.webdriver_testing.data_factories import TeamVideoFactory
from apps.webdriver_testing.data_factories import WorkflowFactory
from apps.webdriver_testing.data_factories import TaskFactory
from apps.webdriver_testing.pages.editor_pages import subtitle_editor 
from apps.webdriver_testing.pages.site_pages.teams import tasks_tab
class TestCaseSubtitlesUpload(WebdriverTestCase):
    """TestSuite for uploading subtitles via the api.

    """
    NEW_BROWSER_PER_TEST_CASE = False

    @classmethod
    def setUpClass(cls):
        super(TestCaseSubtitlesUpload, cls).setUpClass()
        cls.data_utils = data_helpers.DataHelpers()
        cls.user = UserFactory.create()
        cls.data_utils.create_user_api_key(cls.user)
      
        #Create some test data and set subtitle data dir
        cls.test_video = cls.data_utils.create_video()
        cls.subs_data_dir = os.path.join(os.getcwd(), 'apps', 
            'webdriver_testing', 'subtitle_data')

        cls.video_language_pg = video_language_page.VideoLanguagePage(cls)
        cls.video_language_pg.set_skiphowto()



    def api_upload_subs(self, test_format, test_lang_code):
        """Create the language and upload the subtitles.

        Return the subtitle_language object of the test video for verification.
        
        Tests assume that we are using the Timed_text.<lang>.<format> files
        in the subtitle_data directory.
        """

        #Create the language for the test video
        create_url = ('videos/%s/languages/'  % self.test_video.video_id)
        create_data = {'language_code': test_lang_code,
                       'is_complete': True 
                      }
        status, response = self.data_utils.post_api_request(self.user,  
            create_url, 
            create_data)
        self.assertEqual(201, status)
        #Create the url for uploading subtitles of give format and lang.
        upload_url = ('videos/{0}/languages/{1}/subtitles/'.format(
            self.test_video.video_id, test_lang_code))

        #Get the appropriate subtitle data file.
        if test_format == 'ttml':
            sub_data = codecs.open(os.path.join(self.subs_data_dir, 
                'Timed_text.{0}.{1}'.format(test_lang_code, 'xml')),
                encoding = 'utf-8'
                )
            test_format = 'dfxp'
        else:
            sub_data = codecs.open(os.path.join(self.subs_data_dir, 
                'Timed_text.{0}.{1}'.format(test_lang_code, test_format)),
                encoding = 'utf-8')

        #Create the url for uploading subtitles of give format and lang.
        upload_url = ('videos/{0}/languages/{1}/subtitles/'.format(
            self.test_video.video_id, test_lang_code))

        upload_data = {'subtitles': sub_data.read(), 
                       'sub_format': test_format} 

        #Upload the subtitles via api post request
        status, response = self.data_utils.post_api_request(self.user,  
            upload_url, 
            upload_data)
        self.assertEqual(202, status)
        self.video_language_pg.open_video_lang_page(self.test_video.video_id, 
            test_lang_code)
        subtitle_lang = self.test_video.subtitle_language(test_lang_code) 
        return subtitle_lang


    def test_upload__fork_dependents(self):
        video = self.data_utils.create_video()
        auth_creds = dict(username=self.user.username, password='password')
        subs_dir = os.path.join(os.getcwd(), 'apps', 'webdriver_testing', 
                                'subtitle_data') 
        en_rev1 = os.path.join(subs_dir, 'Timed_text.en.srt')
        en_rev2 = os.path.join(subs_dir, 'Timed_text.rev2.en.srt')
        sv = os.path.join(subs_dir, 'Timed_text.sv.dfxp')
        complete = True
        draft_data = {'language_code': 'en',
                     'video': video.pk,
                     'primary_audio_language_code': 'en',
                     'draft': open(en_rev1),
                     'complete': int(complete),
                     'is_complete': complete,
                    }
        self.data_utils.upload_subs(video, draft_data, user=auth_creds)

        draft_data = {'language_code': 'sv',
                     'video': video.pk,
                     'from_language_code': 'en',
                     'draft': open(sv),
                     'complete': int(complete),
                     'is_complete': complete,
                    }
        self.data_utils.upload_subs(video, draft_data, user=auth_creds)
        sl_sv = video.subtitle_language('sv')
        self.assertFalse(sl_sv.is_forked)

        #Upload a new set of subs via the api
        upload_url = ( 'videos/%s/languages/en/subtitles/' 
            % video.video_id )
        upload_data = { 'subtitles': open(en_rev2).read(), 'sub_format': 'srt' } 
        status, response = self.data_utils.post_api_request(self.user,
                                                            upload_url, 
                                                            upload_data)
        sl_sv = video.subtitle_language('sv')
        self.assertTrue(sl_sv.is_forked)





    def test_upload__display(self):
        """Upload subs via api and check display on language page. """
        #Create the language for the test video
        create_url = ( 'videos/%s/languages/'  % self.test_video.video_id  )
        create_data = { 'language_code': 'en', 'is_original': True }
        status, response = self.data_utils.post_api_request(self.user,  
            create_url, 
            create_data)

        #Upload the subtitles via api request
        upload_url = ( 'videos/%s/languages/en/subtitles/' 
            % self.test_video.video_id )
        sub_data =  open(os.path.join(self.subs_data_dir, 'Untimed_text.srt'))
        upload_data = { 'subtitles': sub_data.read(), 'sub_format': 'srt' } 
        status, response = self.data_utils.post_api_request(self.user,
                                                            upload_url, 
                                                            upload_data )
        self.video_language_pg.open_video_lang_page(self.test_video.video_id, 
            'en')
         
        verification_file = os.path.join(self.subs_data_dir,'Untimed_lines.txt')
        expected_list = [line.strip() for line in codecs.open(
                verification_file, encoding='utf-8')]
        displayed_list = self.video_language_pg.displayed_lines()
        #f = codecs.open('myworkfile', 'w', encoding="utf-8")
        #for line in displayed_list:
        #    f.write(line)

        #f.close()
        self.logger.info([(i,j) for i,j in zip(expected_list, displayed_list) if i!=j])
        self.assertEqual(expected_list, displayed_list) 

    def test_upload__resource_uri(self):
        """Check we are returing the correct resource uri fo subs.

        """
        #Create the language for the test video
        create_url = ( 'videos/%s/languages/'  % self.test_video.video_id  )
        create_data = { 'language_code': 'en', 'is_original': True }
        status, response = self.data_utils.post_api_request(self.user,  
            create_url, 
            create_data)

        #Upload the subtitles via api request
        upload_url = ( 'videos/%s/languages/en/subtitles/' 
            % self.test_video.video_id )
        sub_data =  open(os.path.join(self.subs_data_dir, 'Untimed_text.srt'))
        upload_data = { 'subtitles': sub_data.read(), 'sub_format': 'srt' } 
        _, r = self.data_utils.post_api_request(self.user, upload_url, upload_data)
        
        #Compare the returned uri
        expected_uri = ('/api2/partners/videos/%s/languages/en/subtitles/' 
                        % self.test_video.video_id)
        self.assertEqual(expected_uri, r['resource_uri'])


    def test_upload__srt(self):
        """Upload srt format subs via api.

        """
        test_lang_code = 'en'
        test_format = 'srt'
        subtitle_language = self.api_upload_subs(test_format, 
           test_lang_code)
        self.assertEqual(72, subtitle_language.get_subtitle_count())


    def test_upload__ssa(self):
        """Upload ssa format subs via api.

        """

        test_lang_code = 'hu'
        test_format = 'ssa'
        subtitle_language = self.api_upload_subs(test_format, 
           test_lang_code)
        self.video_language_pg.open_video_lang_page(self.test_video.video_id, 
            test_lang_code)

        self.assertEqual(243, subtitle_language.get_subtitle_count())


    def test_upload__sbv(self):
        """Upload sbv format subs via api.

        """

        test_lang_code = 'zh-cn'
        test_format = 'sbv'
        subtitle_language = self.api_upload_subs(test_format, 
           test_lang_code)
        self.video_language_pg.open_video_lang_page(self.test_video.video_id, 
            test_lang_code)

        self.assertEqual(243, subtitle_language.get_subtitle_count())

    def test_upload__ttml(self):
        """Upload xml (ttml) format subs via api.

        """

        test_lang_code = 'ar'
        test_format = 'ttml'
        subtitle_language = self.api_upload_subs(test_format, 
           test_lang_code)
        self.video_language_pg.open_video_lang_page(self.test_video.video_id, 
            test_lang_code)

        self.assertEqual(243, subtitle_language.get_subtitle_count())

    def test_upload__dfxp(self):
        """Upload dfxp format subs via api.

        """

        test_lang_code = 'sv'
        test_format = 'dfxp'
        subtitle_language = self.api_upload_subs(test_format, 
           test_lang_code)
        self.video_language_pg.open_video_lang_page(self.test_video.video_id, 
            test_lang_code)
        self.assertEqual(72, subtitle_language.get_subtitle_count())

    def test_upload__edit(self):
        """Subs uploaded via api are editable in the subtitle editor.

        """
        #Create the language for the test video
        create_url = ('videos/%s/languages/'  % self.test_video.video_id)
        create_data = { 'language_code': 'en', 'is_original': True }
        status, response = self.data_utils.post_api_request(self.user,  
            create_url, 
            create_data)

        #Upload the subtitles via api request
        upload_url = ( 'videos/%s/languages/en/subtitles/' 
            % self.test_video.video_id )
        sub_data =  open(os.path.join(self.subs_data_dir, 'Untimed_text.srt'))
        upload_data = { 'subtitles': sub_data.read(), 'sub_format': 'srt' } 
        status, response = self.data_utils.post_api_request(self.user,  
            upload_url, 
            upload_data)
        self.video_language_pg.open_video_lang_page(self.test_video.video_id, 
            'en')
        #Open the language page for the video and click Edit Subtitles 
        verification_file = os.path.join(self.subs_data_dir, 
            'Untimed_lines.txt')
        expected_list = [line.strip() for line in codecs.open(
            verification_file, encoding='utf-8')]
        self.video_language_pg.log_in(self.user.username, 'password')
        self.video_language_pg.set_skiphowto()
        self.video_language_pg.open_video_lang_page(
            self.test_video.video_id, 'en')
        self.video_language_pg.edit_subtitles()
        sub_editor = subtitle_editor.SubtitleEditor(self)
        editor_sub_list = sub_editor.subtitles_list()

        #Verify uploaded subs are displayed and editable
        self.assertLess(0, len(editor_sub_list))
        typed_subs = sub_editor.edit_subs()
        sub_editor.save_and_exit()
        self.video_language_pg.open_video_lang_page(
            self.test_video.video_id, 'en')
        displayed_list = self.video_language_pg.displayed_lines()

        #Verify the edited text is in the sub list
        self.assertIn("I'd like to be", displayed_list[0])

        #Verify the origal unedited text is still present in the sub list.
        self.assertEqual(expected_list[-1], displayed_list[-1])


class TestCaseSubtitlesFetch(WebdriverTestCase):
    """TestSuite for fetching subtitle information via the api.

    """
    NEW_BROWSER_PER_TEST_CASE = False

    @classmethod
    def setUpClass(cls):
        super(TestCaseSubtitlesFetch, cls).setUpClass()
        cls.data_utils = data_helpers.DataHelpers()
        cls.user = UserFactory.create()
        cls.data_utils.create_user_api_key(cls.user)
 
        #Create the test video and path to the sub data directory.
        cls.test_video = cls.data_utils.create_video_with_subs()
        cls.subs_data_dir = os.path.join(os.getcwd(), 'apps', 
            'webdriver_testing', 'subtitle_data')

        #Open the video language page for the test video.
        cls.video_language_pg = video_language_page.VideoLanguagePage(cls)
        cls.video_language_pg.open_video_lang_page(cls.test_video.video_id, 'en')

    def test_fetch__language(self):
        """Fetch the subtitle data for the specified language.

        If no version is specified, the latest public version will be 
        returned. 
        """
        video_id = self.test_video.video_id
        lang_code = 'en'

        #Set the url for fetching.
        url_part = 'videos/{0}/languages/{1}/'.format(
            video_id, lang_code)

        #Verify we get matching lang code in the response data.
        status, response = self.data_utils.api_get_request(self.user, url_part)
        self.assertEqual(lang_code, response['language_code'])
        

    def test_fetch__srt(self):
        """Fetch the subtitle data in srt format.
        
        GET /api2/partners/videos/[video-id]/languages/[lang-identifier]/
            subtitles/?format=srt
        """
        video_id = self.test_video.video_id
        lang_code = 'en'
        lang = self.test_video.subtitle_language(language_code=lang_code)
        self.assertTrue(lang is not None)
        output_format = 'srt'

        url_part = 'videos/{0}/languages/{1}/subtitles/?format={2}'.format(
            video_id, lang_code, output_format)

        status, response = self.data_utils.api_get_request(self.user,  url_part, 
            output_type = 'content') 

        self.assertTrue(response is not None)

        #Verify returned subs are valid - by uploading back to system
        upload_url = ( 'videos/%s/languages/en/subtitles/' 
            % self.test_video.video_id )

        upload_data = { 'subtitles': response, 'sub_format': 'srt' } 
        status, response = self.data_utils.post_api_request(self.user,  
            upload_url, 
            upload_data)

        #Open the language page on the site.        
        self.video_language_pg.open_video_lang_page(self.test_video.video_id, 
            'en')

        self.assertEqual(2, response['version_number'])


    def test_fetch__dfxp(self):
        """Fetch the subtitle data in dfxp format.
        
        GET /api2/partners/videos/[video-id]/languages/[lang-identifier]/
            subtitles/?format=srt
        """
        video_id = self.test_video.video_id
        lang_code = 'en'
        output_format = 'dfxp'

        url_part = 'videos/{0}/languages/{1}/subtitles/?format={2}'.format(
            video_id, lang_code, output_format)
        status, response = self.data_utils.api_get_request(self.user,  url_part, 
            output_type = 'content')  
        self.assertNotEqual(404, status)
        
        #Verify returned subs are valid - by uploading back to system
        upload_url = ( 'videos/%s/languages/en/subtitles/' 
            % self.test_video.video_id )

        upload_data = { 'subtitles': response, 'sub_format': 'dfxp' } 
        status, response = self.data_utils.post_api_request(self.user,  
            upload_url, 
            upload_data)

        #Open the language page on the site.        
        self.video_language_pg.open_video_lang_page(self.test_video.video_id, 
            'en')

        self.assertEqual(2, response['version_number'])

    def test_fetch__ssa(self):
        """Fetch the subtitle data in ssa format.
        
        GET /api2/partners/videos/[video-id]/languages/[lang-identifier]/
            subtitles/?format=srt
        """
        video_id = self.test_video.video_id
        lang_code = 'en'
        output_format = 'ssa'

        url_part = 'videos/{0}/languages/{1}/subtitles/?format={2}'.format(
            video_id, lang_code, output_format)
        status, response = self.data_utils.api_get_request(self.user,  url_part, 
            output_type = 'content') 

        self.assertNotEqual(404, status)

        #Verify returned subs are valid - by uploading back to system
        upload_url = ( 'videos/%s/languages/en/subtitles/' 
            % self.test_video.video_id )

        upload_data = { 'subtitles': response, 'sub_format': 'ssa' } 
        status, response = self.data_utils.post_api_request(self.user,  
            upload_url, 
            upload_data)

        #Open the language page on the site.        
        self.video_language_pg.open_video_lang_page(self.test_video.video_id, 
            'en')

        self.assertEqual(2, response['version_number'])

    def test_fetch__vtt(self):
        """Fetch the subtitle data in vtt format.
        
        GET /api2/partners/videos/[video-id]/languages/[lang-identifier]/
            subtitles/?format=vtt
        """
        video_id = self.test_video.video_id
        lang_code = 'en'
        output_format = 'vtt'

        url_part = 'videos/{0}/languages/{1}/subtitles/?format={2}'.format(
            video_id, lang_code, output_format)
        status, response = self.data_utils.api_get_request(self.user,  url_part, 
            output_type = 'content') 

        self.assertNotEqual(404, status)

        #Verify returned subs are valid - by uploading back to system
        upload_url = ( 'videos/%s/languages/en/subtitles/' 
            % self.test_video.video_id )

        upload_data = { 'subtitles': response, 'sub_format': 'vtt' } 
        status, response = self.data_utils.post_api_request(self.user,  
            upload_url, 
            upload_data)

        #Open the language page on the site.        
        self.video_language_pg.open_video_lang_page(self.test_video.video_id, 
            'en')

        self.assertEqual(2, response['version_number'])


    def test_fetch__sbv(self):
        """Fetch the subtitle data in sbv format'
        
        GET /api2/partners/videos/[video-id]/languages/[lang-identifier]/
            subtitles/?format=srt
        """
        video_id = self.test_video.video_id
        lang_code = 'en'
        output_format = 'sbv'

        url_part = 'videos/{0}/languages/{1}/subtitles/?format={2}'.format(
            video_id, lang_code, output_format)
        status, response = self.data_utils.api_get_request(self.user,  url_part, 
            output_type = 'content') 

        self.assertNotEqual(404, status)

        #Verify returned subs are valid - by uploading back to system
        upload_url = ( 'videos/%s/languages/en/subtitles/' 
            % self.test_video.video_id )

        upload_data = { 'subtitles': response, 'sub_format': 'sbv' } 
        status, response = self.data_utils.post_api_request(self.user,  
            upload_url, 
            upload_data)

        #Open the language page on the site.        
        self.video_language_pg.open_video_lang_page(self.test_video.video_id, 
            'en')

        self.assertEqual(2, response['version_number'])


    def test_fetch__txt(self):
        """Fetch the subtitle data in txt format.
        
        GET /api2/partners/videos/[video-id]/languages/[lang-identifier]/
            subtitles/?format=srt
        """
        video_id = self.test_video.video_id
        lang_code = 'en'
        output_format = 'txt'

        url_part = 'videos/{0}/languages/{1}/subtitles/?format={2}'.format(
            video_id, lang_code, output_format)
        status, response = self.data_utils.api_get_request(self.user,  url_part, 
            output_type = 'content') 

        self.assertNotEqual(404, status)

        #Verify returned subs are valid - by uploading back to system
        upload_url = ( 'videos/%s/languages/en/subtitles/' 
            % self.test_video.video_id )

        upload_data = { 'subtitles': response, 'sub_format': 'txt' } 
        s, r = self.data_utils.post_api_request(self.user,  
                                                upload_url, 
                                                upload_data)
        self.assertEqual(2, r['version_number'])


    def test_fetch__version(self):
        """Fetch a specific version of a video subtitles.

        Versions are listed in the VideoLanguageResouce request.
        GET /api2/partners/videos/asfssd/languages/en/subtitles/
            ?version=<version_no>


        """
        url = 'http://www.youtube.com/watch?v=WqJineyEszo' 
        video_id = self.test_video.video_id
        lang_code = 'en'
        version = 2
        output_format = 'json'
        data = {
            'language_code': lang_code,
            'video_language': lang_code,
            'video': self.test_video.pk,
            'draft': open('apps/webdriver_testing/subtitle_data/'
                          'Timed_text.en.srt'),
            'is_complete': True
            }
        self.data_utils.create_video_with_subs(url, data)
        url_part = ('videos/{0}/languages/{1}/subtitles/?format={2}'
                    '&version={3}'.format(video_id, 
					  lang_code, 
                                          output_format, 
                                          version))
        status, response = self.data_utils.api_get_request(self.user,  url_part) 
        self.assertNotEqual(404, status)
        self.assertIs(2, response['version_number'])



class TestCaseModeratedSubtitlesUpload(WebdriverTestCase):
    """TestSuite for uploading moderated subtitles via the api.

    """
    NEW_BROWSER_PER_TEST_CASE = False

    @classmethod
    def setUpClass(cls):
        super(TestCaseModeratedSubtitlesUpload, cls).setUpClass()
        cls.data_utils = data_helpers.DataHelpers()
        cls.user = UserFactory.create(username='user')
        cls.data_utils.create_user_api_key(cls.user)
    
        #Create some test data and set subtitle data dir
        cls.test_video = cls.data_utils.create_video()
        cls.subs_data_dir = os.path.join(os.getcwd(), 'apps', 
            'webdriver_testing', 'subtitle_data')


        # self.team_video already has a set of subtitles.
        # Create a team with moderation settings
        cls.my_team = TeamMemberFactory.create(
            team__name='Video Test',
            team__slug='video-test',
            user = cls.user, 
            team__is_moderated = True,
            team__workflow_enabled = True,
            ).team
        
        # Set the team workflow to peer review required.
        workflow = WorkflowFactory(team = cls.my_team)
        workflow.review_allowed = 10
        workflow.save()

        #  Add test_video to the team and create a transcription task.
        cls.lang_code = 'en'
        cls.tv = TeamVideoFactory.create(
            team=cls.my_team, 
            video=cls.test_video, 
            added_by=cls.user)
        subtitle_lang = cls.test_video.subtitle_language(cls.lang_code)
        task = TaskFactory(type = 10, 
                           team = cls.my_team, 
                           team_video = cls.tv, 
                           language = cls.lang_code)

        cls.video_language_pg = video_language_page.VideoLanguagePage(cls)
        cls.tasks_pg = tasks_tab.TasksTab(cls)


    def test_fetch__moderated_public(self):
        """Return public subtitles of a moderated video.

        For videos under moderation only the latest published version is returned. 
        """
        self.skipTest('test is not complete')
        #FIXME Perform the task so there is a new set of complete subs that
        # are unreviewed.
        # Probably easiest to upload a draft, then review it.
       
        # Make a get request for the video language.  Version returned should 
        #be 1, the  original uploaded subtitles 

        self.tasks_pg.log_in(self.user.username, 'password')
        self.tasks_pg.open_tasks_tab(self.my_team.slug)
        #url_part = 'videos/{0}/languages/{1}/?format={2}'.format(
        #    self.test_video.video_id, self.lang_code, output_format, 
        #    #version
        #    )
        #status, response = self.data_utils.api_get_request(self.user,  url_part) 
        
        #self.assertFalse('Needs verification steps added here. '
        #                 'Verify the returned version number and '
        #                 'the sub content.')


    def test_fetch__moderated_none(self):
        """Fetch nothing if moderated and no version has been accepted in review.
        """
        self.skipTest('test is not complete')

        self.tasks_pg.log_in(self.user.username, 'password')
        self.tasks_pg.open_tasks_tab(self.my_team.slug)

        #FIXME Perform the task so there is a new set of complete subs that are unreviewed.
       
        # Make a get request for the video language.  Version returned should
        # be None, since there are no approved subs.
        url_part = 'videos/{0}/languages/{1}/?format={2}'.format(
            self.test_video.video_id, lang_code, output_format) 
            
        status, response = self.data_utils.api_get_request(self.user,  url_part) 



class TestCaseSubtitlesFormatting(WebdriverTestCase):
    """TestSuite for checking supported subtitle formats are preserved.

    """
    NEW_BROWSER_PER_TEST_CASE = False

    @classmethod
    def setUpClass(cls):
        super(TestCaseSubtitlesFormatting, cls).setUpClass()
        cls.data_utils = data_helpers.DataHelpers()
        cls.user = UserFactory.create()
        cls.data_utils.create_user_api_key(cls.user)
        cls.test_video = cls.data_utils.create_video()
        #Create the test video and path to the sub data directory.
        cls.subs_data_dir = os.path.join(os.getcwd(), 'apps', 
            'webdriver_testing', 'subtitle_data')

        data = {'language_code': 'en',
                'video': cls.test_video.pk,
                'primary_audio_language_code': 'en',
                'draft': open(os.path.join(cls.subs_data_dir, 
                                           'formatted.srt')),
                'is_complete': True,
                'complete': 1
                }
        cls.data_utils.upload_subs(cls.test_video, data=data)
        #Open the video language page for the test video.
        #cls.video_language_pg = video_language_page.VideoLanguagePage(cls)
        #cls.video_language_pg.open_video_lang_page(cls.test_video.video_id, 'en')


    def test_formatted__dfxp(self):
        """Fetch the subtitle data in srt format.
        
        GET /api2/partners/videos/[video-id]/languages/[lang-identifier]/
            subtitles/?format=srt
        """

        expected_dfxp_lines = ["""<p>this is a single line of subtitles</p>""",

                               """<p>this is line 1<br/>this is line 2</p>""",

                               ("""<p><span tts:fontStyle="italic"> line 1 """
                                """is italicized</span><br/>line 2</p>"""),

                               ("""<span tts:fontWeight="bold">line 1 is """
                                """bold</span>""")

                              ]
        video_id = self.test_video.video_id
        lang_code = 'en'
        lang = self.test_video.subtitle_language(language_code=lang_code)
        self.assertTrue(lang is not None)
        output_format = 'dfxp'

        url_part = 'videos/{0}/languages/{1}/subtitles/?format={2}'.format(
            video_id, lang_code, output_format)

        status, response = self.data_utils.api_get_request(self.user,  url_part, 
            output_type = 'content') 
        self.logger.info(response)

        for line in expected_dfxp_lines:
            self.assertIn(line, response)


    def test_formatted__vtt(self):
        """Fetch the subtitle data in webvtt format.
        
        GET /api2/partners/videos/[video-id]/languages/[lang-identifier]/
            subtitles/?format=srt
        """
        expected_vtt_lines = ["""WEBVTT""",
                              """<i> line 1 is italicized</i>""",
                              """<b>line 1 is bold</b>"""
                             ]
        output_format = 'vtt'

        url_part = 'videos/{0}/languages/{1}/subtitles/?format={2}'.format(
            self.test_video.video_id, 'en', output_format)

        status, response = self.data_utils.api_get_request(self.user,  url_part, 
            output_type = 'content') 
        rlines = response.split("""\n""")
        for line in expected_vtt_lines:
            self.assertIn(line, rlines)

    def test_formatted__srt(self):
        """Fetch the subtitle data in srt format.
        
        GET /api2/partners/videos/[video-id]/languages/[lang-identifier]/
            subtitles/?format=srt
        """
        expected_srt_lines = ["""<i> line 1 is italicized</i>""",
                              """<b>line 1 is bold</b>"""
                             ]
        output_format = 'srt'

        url_part = 'videos/{0}/languages/{1}/subtitles/?format={2}'.format(
            self.test_video.video_id, 'en', output_format)

        status, response = self.data_utils.api_get_request(self.user,  url_part, 
            output_type = 'content') 
        rlines = response.split("""\n""")
        for line in expected_srt_lines:
            self.assertIn(line, rlines)



    def test_formatted__sbv(self):
        """Fetch the subtitle data in srt format.
        
        GET /api2/partners/videos/[video-id]/languages/[lang-identifier]/
            subtitles/?format=srt
        """

        expected_sbv_lines = ["""this is line 1[br]this is line 2""",
                               """line 1 is italicized[br]line 2"""
                              ]
        video_id = self.test_video.video_id
        lang_code = 'en'
        lang = self.test_video.subtitle_language(language_code=lang_code)
        self.assertTrue(lang is not None)
        output_format = 'sbv'

        url_part = 'videos/{0}/languages/{1}/subtitles/?format={2}'.format(
            video_id, lang_code, output_format)

        status, response = self.data_utils.api_get_request(self.user,  url_part, 
            output_type = 'content') 
        self.logger.info(response)

        for line in expected_sbv_lines:
            self.assertIn(line, response)

    def test_formatted__ssa(self):
        """Fetch the subtitle data in srt format.
        
        GET /api2/partners/videos/[video-id]/languages/[lang-identifier]/
            subtitles/?format=ssa
        """

        expected_ssa_lines = [('Dialogue: 0,9:59:59.99,9:59:59.99,Default,,'
                                '0000,0000,0000,,this is line 1\nthis is line 2'),
                               
                               ('Dialogue: 0,9:59:59.99,9:59:59.99,Default,,'
                                '0000,0000,0000,,this is line 1this is line 2'),

                              ]
        video_id = self.test_video.video_id
        lang_code = 'en'
        lang = self.test_video.subtitle_language(language_code=lang_code)
        self.assertTrue(lang is not None)
        output_format = 'ssa'

        url_part = 'videos/{0}/languages/{1}/subtitles/?format={2}'.format(
            video_id, lang_code, output_format)

        status, response = self.data_utils.api_get_request(self.user,  url_part, 
            output_type = 'content') 
        self.logger.info(response)

        for line in expected_ssa_lines:
            self.assertIn(line, response, 
                          ('see https://github.com/pculture/unisubs/issues/692 '
                           'for ssa linebreak issue'))
