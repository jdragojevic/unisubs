# -*- coding: utf-8 -*-

from apps.webdriver_testing.webdriver_base import WebdriverTestCase
from apps.webdriver_testing.pages.site_pages.teams_dir_page import TeamsDirPage
from apps.webdriver_testing.pages.site_pages.teams import members_tab
from apps.webdriver_testing.pages.site_pages import user_messages_page
from apps.webdriver_testing.data_factories import TeamMemberFactory
from apps.webdriver_testing.data_factories import TeamContributorMemberFactory
from apps.webdriver_testing.data_factories import TeamManagerMemberFactory
from apps.webdriver_testing.data_factories import TeamAdminMemberFactory
from apps.webdriver_testing.data_factories import TeamProjectFactory
from apps.webdriver_testing.data_factories import UserFactory

class TestCaseMembersTab(WebdriverTestCase):
    """Verify edit of member roles and restrictions.  """
    NEW_BROWSER_PER_TEST_CASE = False

    @classmethod
    def setUpClass(cls):
        super(TestCaseMembersTab, cls).setUpClass()
        cls.team_dir_pg = TeamsDirPage(cls)
        cls.user_message_pg = user_messages_page.UserMessagesPage(cls)

        cls.members_tab = members_tab.MembersTab(cls)
        cls.team_owner =  UserFactory.create()
        cls.team = TeamMemberFactory.create(team__name='Members tab roles Test',
                                            user = cls.team_owner).team
        cls.promoted_manager = TeamContributorMemberFactory.create(
                               team=cls.team,
                               user = UserFactory()).user
        cls.promoted_admin = TeamContributorMemberFactory.create(
                             team=cls.team,
                             user = UserFactory()).user
        cls.project = TeamProjectFactory.create(team=cls.team, 
                                                workflow_enabled=True,)
        cls.members_tab.open_members_page(cls.team.slug)


    def test_invitation_form(self):
        """Send an invitation via the form on the members tab.

        """
        user = UserFactory.create()
        self.members_tab.log_in(self.team_owner.username, 'password')
        self.members_tab.open_members_page(self.team.slug)
        self.members_tab.invite_user_via_form(username = user.username,
                                              message = 'Join my team',
                                              role = 'Contributor')
        self.members_tab.log_in(user.username, 'password')
        self.assertEqual(1, user.team_invitations.count())
        self.assertEqual(1, self.team.invitations.count())
        #Verify the user gets the message displayed.
        self.user_message_pg.open_messages()
        self.assertTrue('has invited you' in 
            self.user_message_pg.message_text())


    def test_assign__manager(self):
        """Asign a manager with no restrictions.

           Verify the display of the roles in the members tab.
        """
 
        self.members_tab.log_in(self.team_owner.username, 'password')
        self.members_tab.member_search(self.team.slug, 
                                       self.promoted_manager.username)
        self.members_tab.edit_user(role="Manager")
        self.members_tab.member_search(self.team.slug, 
                                       self.promoted_manager.username)
        self.assertEqual(self.members_tab.user_role(), 'Manager')

    def test_assign__manager_lang_restrictions(self):
        self.members_tab.log_in(self.team_owner, 'password')
        self.members_tab.member_search(self.team.slug, 
                                       self.promoted_manager.username)
        self.members_tab.edit_user(
            role="Manager", languages=['English', 'French'])
        self.members_tab.member_search(self.team.slug, 
                                       self.promoted_manager.username)

        self.assertEqual(self.members_tab.user_role(), 
                      'Manager for French, and English languages')

    def test_assign__manager_project_lang_restrictions(self):
        """Assign a manager with project restrictions.

           Verify the display of the roles in the members tab.
        """
        self.members_tab.log_in(self.team_owner.username, 'password')
        self.members_tab.member_search(self.team.slug, 
                                       self.promoted_manager.username)
        self.members_tab.edit_user(
            role="Manager", projects=self.project.name,
            languages=['English', 'French'])
        self.members_tab.member_search(self.team.slug, 
                                       self.promoted_manager.username)
        self.assertEqual(self.members_tab.user_role(), ('Manager for %s project '
                    'and for French, and English languages' % self.project.name))


    def test_assign__manager_project_restrictions(self):
        """Assign a manager with project restrictions.

           Verify the display of the roles in the members tab.
        """
        self.members_tab.log_in(self.team_owner.username, 'password')
        self.members_tab.member_search(self.team.slug, 
                                       self.promoted_manager.username)
        self.members_tab.edit_user(
            role="Manager", projects=self.project.name)
        self.members_tab.member_search(self.team.slug, 
                                       self.promoted_manager.username)
        self.assertEqual(self.members_tab.user_role(), 
                      'Manager for %s project' % self.project.name)


    def test_assign__admin(self):
        """Assign another admin with no restrictions.

           Verify the display of the roles in the members tab.
        """
        self.members_tab.log_in(self.team_owner.username, 'password')
        self.members_tab.member_search(self.team.slug, 
                                       self.promoted_admin.username)
        self.members_tab.edit_user(role="Admin")
        self.members_tab.member_search(self.team.slug, 
                                       self.promoted_admin.username)
        self.assertEqual(self.members_tab.user_role(), 
                      'Admin')


    def test_assign__admin_project_restrictions(self):
        """Assign an admin with project restrictions.

           Verify the display of the roles in the members tab.
        """
        self.members_tab.log_in(self.team_owner.username, 'password')
        self.members_tab.member_search(self.team.slug, 
                                       self.promoted_admin.username)
        self.members_tab.edit_user(
            role="Admin", projects=self.project.name)
        self.members_tab.member_search(self.team.slug, 
                                       self.promoted_admin.username)
        self.assertEqual(self.members_tab.user_role(), 
                      'Admin for %s project' % self.project.name)

class TestCaseManageMembers(WebdriverTestCase):
    """Verify display of invite, delete links.  """
    NEW_BROWSER_PER_TEST_CASE = False

    @classmethod
    def setUpClass(cls):
        super(TestCaseManageMembers, cls).setUpClass()
        cls.members_tab = members_tab.MembersTab(cls)
        cls.team_owner =  UserFactory.create()
        cls.team = TeamMemberFactory.create(team__membership_policy=1,
                                            user = cls.team_owner).team
        cls.manager = TeamManagerMemberFactory.create(
                               team=cls.team).user
        cls.admin = TeamAdminMemberFactory.create(
                             team=cls.team).user
        cls.member = TeamContributorMemberFactory.create(
                             team=cls.team).user
        cls.members_tab.open_members_page(cls.team.slug)

    def test_admin_invite__owner(self):
        """Admin invite team, owner sees invite button."""
        self.team.membership_policy = 5
        self.team.save()
        self.members_tab.log_in(self.team_owner.username, 'password')
        self.members_tab.open_members_page(self.team.slug)
        self.assertTrue(self.members_tab.displays_invite())

    def test_admin_invite__admin(self):
        """Admin invite team, admin sees invite button. """
        self.team.membership_policy = 5
        self.team.save()
        self.members_tab.log_in(self.admin.username, 'password')
        self.members_tab.open_members_page(self.team.slug)
        self.assertTrue(self.members_tab.displays_invite())

    def test_admin_invite__manager(self):
        """Admin invite team, manager does not see invite button."""
        self.team.membership_policy = 5
        self.team.save()
        self.members_tab.log_in(self.manager.username, 'password')
        self.members_tab.open_members_page(self.team.slug)
        self.assertFalse(self.members_tab.displays_invite())

 
    def test_admin_invite__member(self):
        """Admin invite team, member does not see invite button."""

        self.team.membership_policy = 5
        self.team.save()
        self.members_tab.log_in(self.member.username, 'password')
        self.members_tab.open_members_page(self.team.slug)
        self.assertFalse(self.members_tab.displays_invite())

    def test_manager_invite__admin(self):
        """Manager invite team, admin sees invite button. """

        self.team.membership_policy = 2
        self.team.save()
        self.members_tab.log_in(self.admin.username, 'password')
        self.members_tab.open_members_page(self.team.slug)
        self.assertTrue(self.members_tab.displays_invite())

    def test_manager_invite__manager(self):
        """Manager invite team, manager sees invite button. """
        self.team.membership_policy = 2
        self.team.save()
        self.members_tab.log_in(self.manager.username, 'password')
        self.members_tab.open_members_page(self.team.slug)
        self.assertTrue(self.members_tab.displays_invite())

    def test_manager_invite__member(self):
        """Manager invite team, member does not see invite button. """
        self.team.membership_policy = 2
        self.team.save()
        self.members_tab.log_in(self.member.username, 'password')
        self.members_tab.open_members_page(self.team.slug)
        self.assertFalse(self.members_tab.displays_invite())

    def test_all_invite__admin(self):
        """All invite team, admin sees invite button. """

        self.team.membership_policy = 3
        self.team.save()
        self.members_tab.log_in(self.admin.username, 'password')
        self.members_tab.open_members_page(self.team.slug)
        self.assertTrue(self.members_tab.displays_invite())

    def test_all_invite__manager(self):
        """All invite team, manager sees invite button. """
        self.team.membership_policy = 3
        self.team.save()
        self.members_tab.log_in(self.manager.username, 'password')
        self.members_tab.open_members_page(self.team.slug)
        self.assertTrue(self.members_tab.displays_invite())

    def test_all_invite__member(self):
        """All invite team, member sees invite button. """
        self.team.membership_policy = 3
        self.team.save()
        self.members_tab.log_in(self.member.username, 'password')
        self.members_tab.open_members_page(self.team.slug)
        self.assertTrue(self.members_tab.displays_invite())

    def test_open__invite_member(self):
        """Open team any member sees invite button. """
        self.team.membership_policy = 4
        self.team.save()
        self.members_tab.log_in(self.member.username, 'password')
        self.members_tab.open_members_page(self.team.slug)
        self.assertTrue(self.members_tab.displays_invite())

    def test_application__invite_admin(self):
        """In application-only team only admin sees invite button. """
        self.team.membership_policy = 1
        self.team.save()
        self.members_tab.log_in(self.admin.username, 'password')
        self.members_tab.open_members_page(self.team.slug)
        self.assertTrue(self.members_tab.displays_invite())

    def test_application__invite_manager(self):
        """In application-only team only manager does not see invite button. """
        self.team.membership_policy = 1
        self.team.save()
        self.members_tab.log_in(self.manager.username, 'password')
        self.members_tab.open_members_page(self.team.slug)
        self.assertFalse(self.members_tab.displays_invite())

    def test_application__invite_member(self):
        """In application-only team only member does not see invite button. """
        self.team.membership_policy = 1
        self.team.save()
        self.members_tab.log_in(self.member.username, 'password')
        self.members_tab.open_members_page(self.team.slug)
        self.assertFalse(self.members_tab.displays_invite())

    def test_delete_user__admin(self):
        """Admin can delete managers and contributors. """
        self.members_tab.log_in(self.admin.username, 'password')
        self.members_tab.member_search(self.team.slug, self.member.username)
        self.assertTrue(self.members_tab.delete_user_link)








