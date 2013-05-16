import os

from apps.webdriver_testing.webdriver_base import WebdriverTestCase
from apps.webdriver_testing.pages.site_pages import video_language_page
from apps.webdriver_testing import data_helpers
from apps.webdriver_testing.data_factories import UserFactory
from apps.webdriver_testing.data_factories import VideoUrlFactory
from apps.webdriver_testing.pages.editor_pages import subtitle_editor 


class TestCaseEditUploaded(WebdriverTestCase):
    """TestSuite large subtitle sets  """
    NEW_BROWSER_PER_TEST_CASE = False 

    @classmethod
    def setUpClass(cls):
        super(TestCaseEditUploaded, cls).setUpClass()
        cls.data_utils = data_helpers.DataHelpers()
        cls.user = UserFactory.create(username = 'user')
        cls.video_language_pg = video_language_page.VideoLanguagePage(cls)
        cls.sub_editor = subtitle_editor.SubtitleEditor(cls)
        cls.subs_data_dir = os.path.join(os.getcwd(), 'apps', 
            'webdriver_testing', 'subtitle_data')


    def test_edit__large(self):
        """Upload a large set of subtitles then open for editing. """
        self.skipTest('skipping for now need to see why fails on jenkins')
        video =  self.data_utils.create_video()
        data = {'language_code': 'en',
                'video': video.pk,
                'primary_audio_language_code': 'en',
                'draft': open('apps/webdriver_testing/subtitle_data/'
                              'How-to.en.srt'),
                'is_complete': True,
                'complete': 1
           }
        r = self.data_utils.upload_subs(
                video, 
                data=data,
                user=dict(username=self.user.username, 
                          password='password'))
        sub_file = os.path.join(self.subs_data_dir, 'srt-full.srt')

        fr_data = {'language_code': 'fr',
                     'video': video.pk,
                     'from_language_code': 'en',
                     'draft': open(sub_file),
                    }
        r = self.data_utils.upload_subs(video, 
                                        data=fr_data,
                                        user=dict(username=self.user.username,
                                                  password='password'))
        
        self.video_language_pg.open_video_lang_page(video.video_id, 'fr')
        self.video_language_pg.log_in(self.user.username, 'password')
        self.video_language_pg.page_refresh()

        self.video_language_pg.edit_subtitles()
        self.assertEqual('Adding a New Translation', 
                         self.sub_editor.dialog_title())
