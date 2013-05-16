#!/usr/bin/env python
import time
from nose.tools import assert_equals
from nose.tools import assert_true
from apps.webdriver_testing.pages.site_pages import UnisubsPage


class ATeamPage(UnisubsPage):
    """Defines the actions for specific teams pages like 'unisubs test team' (default) or others.
    """

    _URL = 'teams/%s/'
    _TEAM_NAME = ".main-title a"
    _DASHBOARD_WELCOME = "div.get-started p"

    _PROJECTS_SECTION = 'div#projects-list'
    _LISTED_PROJECTS = 'ul li a'

    #TEAM METRICS
    _VIDEO_METRIC = ".metrics li:nth-child(1) > a p"
    _MEMBER_METRIC = ".metrics li:nth-child(2) > a p"
    _TASK_METRIC = ".metrics li:nth-child(3) > a p"
    _PROJECT_METRIC = ".metrics li:nth-child(4) > a p"

    #TABS
    _DASHBOARD_TAB = "ul.tabs li a"
    _VIDEOS_TAB = "ul.tabs li a[href*='videos']"
    _MEMBERS_TAB = "ul.tabs li a[href*='members']"
    _ACTIVITY_TAB = "ul.tabs li a[href*='activity']"
    _SETTINGS_TAB = "ul.tabs li a[href*='settings']"
    _TASKS_TAB = "ul.tabs li a[href*='tasks']"


    _ERROR = '.errorlist li'

    #JOIN / APPLY
    _JOIN_TEAM = ".join p a"
    _APPLY_TEAM = "a#apply"
    _SIGNIN = "a#signin-join"
    _APPLY_BUTTON = "Apply to Join"
    _APPLICATION = "div#apply-modal"
    _CUSTOM_APPLICATION_MESSAGE = "div.message"
    _APPLICATION_TEXT = "div#apply-modal div.form textarea"
    _SUBMIT_APPLICATION = "div#apply-modal button"

    _REPLACEMENT_TEXT = 'div.join p.action-replacement'

   #FILTER AND SORT

    def open_team_page(self, team):
        self.logger.info('opening the page for the team %s' %team)
        self.open_page(self._URL %team)

    def open_team_project(self, team_slug, project_slug):
        """Open the team project page by constucting the url.

        """
        self.logger.info('opening the {0} project for team {1}'.format(
                         project_slug, team_slug))
        url = 'teams/{0}/videos/?project={1}'.format(team_slug, project_slug)
        self.open_page(url)

    def open_tab(self, tab):
        """Open a tab on the current team page.

        """
        self.logger.info('opening %s tab on the current team page' % tab)
        tab_css = "_".join(['', tab.upper(), 'TAB'])
        self.click_by_css(getattr(self, tab_css))


    def is_team(self, team):
        """Get the name of the team on the current page.

        """
        self.wait_for_element_present(self._TEAM_NAME)
        self.logger.info('Check it is the %s team page.' % team)
        if self.get_text_by_css(self._TEAM_NAME) == team:
            return True

    def team_search(self, team):
        pass

    def join_exists(self):
        if self.is_element_visible(self._JOIN_TEAM):
            return True

    def apply_exists(self):
        button = self._APPLY_TEAM
        join_button = self.get_text_by_css(button)
        if self.logged_in():
            assert_equals(join_button, self._APPLY_BUTTON)
        else:
            assert_equals(join_button, self._JOIN_NOT_LOGGED_IN)

    def application_displayed(self):
        assert_true(self.is_element_present(self._APPLICATION))

    def application_custom_message(self):
        return self.get_text_by_css(self._CUSTOM_APPLICATION_MESSAGE) 

    def submit_application(self, text=None):
        if text is None:
            text = ("Please let me join your team, I'll subtitle hard. "
                    "I promise.")
        self.application_displayed()
        self.type_by_css(self._APPLICATION_TEXT, text)
        self.click_by_css(self._SUBMIT_APPLICATION)

    def join(self, logged_in=True):
        self.click_by_css(self._JOIN_TEAM)
        if logged_in == True:
            self.handle_js_alert(action='accept')

    def join_text(self):
        return self.get_text_by_css(self._JOIN_TEAM)


    def signin(self):
        self.click_by_css(self._SIGNIN)

    def apply(self):
        self.click_by_css(self._APPLY_TEAM)

    def leave_team(self, team_url):
        leave_url = "teams/leave_team/%s/" % team_url
        self.open_page(leave_url)

    def dashboard_welcome_message(self):
        return self.get_text_by_css(self._DASHBOARD_WELCOME)

    def settings_tab_visible(self):
        return self.is_element_visible(self._SETTINGS_TAB)

    def has_project(self, project_slug):
        if not self.is_element_present(self._PROJECTS_SECTION):
            return False
        projects = self.get_sub_elements_list(self._PROJECTS_SECTION, 
                                              self._LISTED_PROJECTS)

        for els in projects:
            print els.get_attribute('href')
            if project_slug in els.get_attribute('href'):
                return True
        else:
            return False

    def error_message(self):
        return self.get_text_by_css(self._ERROR)

    def replacement_text(self):
        return self.get_text_by_css(self._REPLACEMENT_TEXT)


        
