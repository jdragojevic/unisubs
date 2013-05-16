#!/usr/bin/env python

from apps.webdriver_testing.pages.site_pages import UnisubsPage
from urlparse import urlsplit


class VideoPage(UnisubsPage):
    """
     Video Page contains the common elements in the video page.
    """

    _URL = "videos/%s"  # %s is the unique onsite video id
    _VIDEO_TITLE = "div.content h2.main-title a.title-container"
    _DESCRIPTION = "div#description"
    _EMBEDDED_VIDEO = "div.unisubs-widget div.unisubs-videoTab-container"
    _SUBTITLE_MENU = "a.unisubs-subtitleMeLink span.unisubs-tabTextchoose"
    _LIKE_FACEBOOK = "li.unisubs-facebook-like button"
    _POST_FACEBOOK = "a.facebook"
    _POST_TWITTER = "a.twittter"
    _EMAIL_FRIENDS = "a.email"
    _FOLLOW = "button.follow-button"
    #FOLLOW CONFIRMATION
    _UNFOLLOW_ALL = 'input#unfollow-all-languages-button'
    _SUBTITLES_OK = 'input#popup_ok'

    _EMBED_HELP = "div.unisubs-share h3 a.embed_options_link"
    _EMBED_CODE = ("div#embed-modal.modal div.modal-body form fieldset "
        "textarea")

    #TOP TABS
    _URLS_TAB = 'a[href="#urls-tab"]'
    _VIDEO_TAB = 'a[href="#video-tab"]'
    _COMMENTS_TAB = 'a[href="#comments-tab"]'
    _ACTIVITY_TAB = 'a[href="#activity-tab"]'


    _ADD_SUBTITLES = "a.add_subtitles"

    #VIDEO SIDE SECTION
    _INFO = "ul#video-menu.left_nav li:nth-child(1) > a"
    _ADD_TRANSLATION = "li.contribute a#add_translation"
    _UPLOAD_SUBTITLES = "a#upload-subtitles-link"

    #SUBTITLES_SIDE_SECTION
    _SUB_LANGUAGES = "ul#subtitles-menu li"
    _STATUS_TAGS = "span.tags"

    #TEAM_SIDE_SECTION
    _ADD_TO_TEAM_PULLDOWN = ("ul#moderation-menu.left_nav li div.sort_button "
        "div.arrow")
    _TEAM_LINK = ("ul#moderation-menu.left_nav li div.sort_button ul li "
        "a[href*='%s']")

    #ADMIN_SIDE_SECTION
    _DEBUG_INFO = ""
    _EDIT = ""

    #UPLOAD SUBTITLES DIALOG
    _SELECT_LANGUAGE = 'select#id_language_code'
    _TRANSLATE_FROM = 'select#id_from_language_code'
    _PRIMARY_AUDIO = 'select#id_primary_audio_language_code'
    _SUBTITLES_FILE = 'input#subtitles-file-field'
    _IS_COMPLETE = 'input#updload-subtitles-form-is_complete' #checked default

    _UPLOAD_SUBMIT = 'form#upload-subtitles-form button.green_button'
    _FEEDBACK_MESSAGE = 'p.feedback-message'
    _CLOSE = 'div#upload_subs-div a.close'
    UPLOAD_SUCCESS_TEXT = ('Thank you for uploading. It may take a minute or '
                           'so for your subtitles to appear.')

    

    def open_video_page(self, video_id):
        self.open_page(self._URL % video_id)

    def add_translation(self):
        self.click_by_css(self._ADD_TRANSLATION)

    def upload_subtitles(self, 
                         sub_lang, 
                         sub_file,
                         audio_lang = None,
                         translated_from = None, 
                         is_complete = True):
        #Open the dialog
        self.click_by_css(self._UPLOAD_SUBTITLES)
        #Choose the language
        self.wait_for_element_visible(self._SELECT_LANGUAGE)
        self.select_option_by_text(self._SELECT_LANGUAGE, sub_lang)
        #Set the audio language
        if audio_lang:
            self.select_option_by_text(self._PRIMARY_AUDIO, audio_lang)
        #Set the translation_from field
        if translated_from:
            self.select_option_by_text(self._TRANSLATE_FROM, translated_from)
        #Input the subtitle file
        self.type_by_css(self._SUBTITLES_FILE, sub_file)
        #Set complete
        if not is_complete:
            self.click_by_css(self._IS_COMPLETE)
        #Start the upload
        self.wait_for_element_present(self._UPLOAD_SUBMIT)
        self.click_by_css(self._UPLOAD_SUBMIT)
        #Get the the response message
        self.wait_for_element_present(self._FEEDBACK_MESSAGE, wait_time=20)
        message_text = self.get_text_by_css(self._FEEDBACK_MESSAGE)
        #Close the dialog
        self.click_by_css(self._CLOSE)
        self.wait_for_element_not_visible(self._CLOSE)
        return message_text



    def open_info_page(self):
        self.click_by_css(self._INFO)

    def add_video_to_team(self, team_name):
        self.click_by_css(self._ADD_TO_TEAM_PULLDOWN)
        self.click_by_css(self._TEAM_LINK % team_name)

    def video_id(self):
        page_url = self.browser.current_url
        url_parts = urlsplit(page_url).path
        urlfrag = url_parts.split('/')[3]
        return urlfrag

    def description_text(self):
        return self.get_text_by_css(self._DESCRIPTION)

    def video_embed_present(self):
        if self.is_element_present(self._EMBEDDED_VIDEO):
            return True

    def add_subtitles(self):
        self.click_by_css(self._ADD_SUBTITLES)

    def team_slug(self, slug):
        """Return true if the team stub is linked on the video page.
        """
        team_link = "a[href*='/teams/%s/']" % slug
        if self.is_element_present(team_link):
            return True

    def feature_video(self):
        self.click_link_text('Feature video')

    def unfeature_video(self):
        self.click_link_text('Unfeature video')

    def displays_subtitle_me(self):
        return self.is_element_visible(self._SUBTITLE_MENU)

    def click_subtitle_me(self):
        self.click_by_css(self._SUBTITLE_MENU)

    def displays_add_subtitles(self):
        return self.is_element_visible(self._ADD_SUBTITLES)

    def displays_add_translation(self):
        return self.is_element_visible(self._ADD_TRANSLATION)

    def displays_upload_subtitles(self):
        return self.is_element_visible(self._UPLOAD_SUBTITLES)

    def follow_text(self):
        return self.get_text_by_css(self._FOLLOW)

    def toggle_follow(self, lang=False):
        self.click_by_css(self._FOLLOW)
        if lang:
            self.click_by_css(self._SUBTITLES_OK)
        else:
            self.click_by_css(self._UNFOLLOW_ALL)

    def subtitle_languages(self):
        langs = []
        els = self.get_elements_list(self._SUB_LANGUAGES + " a")
        for el in els:
            langs.append(el.text)
        return langs

    def language_status(self, language):
        els =  self.get_elements_list(self._SUB_LANGUAGES)
        for el in els:
            e = el.find_element_by_css_selector("a")
            self.logger.info(e.text)
            if e.text == language:
                lang_el = el
                break
        else: 
            self.logger.info('language not in list')
            return None, None
        status_img = lang_el.find_element_by_css_selector(
                              "img").get_attribute("src")
        try:
            status_tag = lang_el.find_element_by_css_selector(
                         self._STATUS_TAGS).text
        except:
            status_tag = None

        return status_tag, status_img

