from datetime import datetime, timedelta, date

from django.test import TestCase

from apps.auth.models import CustomUser as User
from apps.teams.models import (
    Team, BillingRecord, BillingReport, Workflow, TeamVideo
)
from apps.subtitles.models import SubtitleLanguage, SubtitleVersion
from apps.subtitles.pipeline import add_subtitles
from apps.videos.models import Video
from apps.videos.tasks import video_changed_tasks
from apps.videos.types.youtube import FROM_YOUTUBE_MARKER
from apps.videos.tests.data import (
    make_subtitle_lines, make_subtitle_language, get_video, get_user,
    make_subtitle_version
)


class BillingTest(TestCase):
    fixtures = [
        "staging_users.json",
        "staging_teams.json"
    ]

    def setUp(self):
        self.video  = get_video()
        self.team =Team.objects.all()[0]
        TeamVideo.objects.get_or_create(video=self.video, team=self.team,
                                        added_by = get_user()
        )
    def test_approved(self):

        self.assertEquals(0, Workflow.objects.count())

        self.team.workflow_enabled = True
        self.team.save()

        Workflow.objects.create(team=self.team, approve_allowed=20)

        self.assertEquals(1, Workflow.objects.count())
        self.assertTrue(self.team.get_workflow().approve_enabled)

        english = make_subtitle_language(self.video, 'en')
        spanish = make_subtitle_language(self.video, 'es')

        for i in range(1, 10):
            add_subtitles(self.video, english.language_code,[],
                          created=datetime(2012, 1, i, 0, 0, 0),
                          visibility='private',
            )


        # make two versions public to be sure we're selecting the very first one
        v1_en = SubtitleVersion.objects.get(subtitle_language=english, version_number=3)
        v2_en = SubtitleVersion.objects.get(subtitle_language=english, version_number=6)

        v1_en.publish()
        v1_en.save()
        v2_en.publish()
        v2_en.save()

        b = BillingReport.objects.create(team=self.team,
                                         start_date=date(2012, 1, 1), end_date=date(2012, 1, 2))

        past_date = self.team.created - timedelta(days=5)
        make_subtitle_version(spanish, created=past_date, note=FROM_YOUTUBE_MARKER)


        langs = self.video.newsubtitlelanguage_set.all()
        self.assertEqual(len(langs) , 2)
        created, imported, _ = b._get_lang_data(langs, datetime(2012, 1, 1, 13, 30, 0))
        print created

        self.assertEqual(len(created) , 1)

        v = created[0][1]
        self.assertEquals(v.version_number, 3)
        self.assertEqual(v.subtitle_language , english)


    def test_get_imported(self):

        team = Team.objects.all()[0]
        video = Video.objects.all()[0]

        team_created = team.created

        b = BillingReport.objects.create(team=team,
                                         start_date=date(2012, 1, 1), end_date=date(2012, 1, 2))

        SubtitleLanguage.objects.all().delete()

        sl_en = SubtitleLanguage.objects.create(video=video, language_code='en')
        sl_cs = SubtitleLanguage.objects.create(video=video, language_code='cs')
        sl_fr = SubtitleLanguage.objects.create(video=video, language_code='fr')
        sl_es = SubtitleLanguage.objects.create(video=video, language_code='es')
        SubtitleLanguage.objects.create(video=video, language_code='ru')

        before_team_created = team_created - timedelta(days=10)
        after_team_created = team_created + timedelta(days=10)

        # Imported
        add_subtitles(video, 'fr', [], created=before_team_created, note=FROM_YOUTUBE_MARKER)
        # Created
        add_subtitles(video, 'fr', [], created=after_team_created)
        add_subtitles(video, 'en', [], created=before_team_created, note=FROM_YOUTUBE_MARKER)
        # Imported
        add_subtitles(video, 'es', [], created=before_team_created)
        # Imported
        add_subtitles(video, 'cs', [], created=after_team_created, note=FROM_YOUTUBE_MARKER)

        # Done with setup, let's test things

        languages = SubtitleLanguage.objects.all()
        imported, crowd_created = b._separate_languages(languages)

        self.assertEquals(len(imported), 3)
        imported_pks = [i.pk for i in imported]
        self.assertTrue(sl_fr.pk in imported_pks)
        self.assertTrue(sl_es.pk in imported_pks)
        self.assertTrue(sl_cs.pk in imported_pks)

    def test_record_insertion(self):

        BillingRecord.objects.all().delete()

        user = User.objects.all()[0]

        video = Video.objects.filter(teamvideo__isnull=False)[0]
        video.primary_audio_language_code = 'en'
        video.user = user
        video.save()

        now = datetime.now()

        sv = add_subtitles(video, 'en', make_subtitle_lines(4), complete=True,
                          author=user, created=now)
        sl = sv.subtitle_language

        video_changed_tasks(video.pk, sv.pk)

        self.assertEquals(1, BillingRecord.objects.all().count())

        br = BillingRecord.objects.all()[0]

        self.assertEquals(br.video.pk, video.pk)
        self.assertEquals(br.team.pk, video.get_team_video().team.pk)
        self.assertEquals(br.created, now)
        self.assertEquals(br.is_original, sl.is_primary_audio_language())
        self.assertEquals(br.user.pk, user.pk)
        self.assertEquals(br.new_subtitle_language.pk, sl.pk)

        team = video.get_team_video().team
        start = datetime(2013, 1, 1, 0, 0)
        end = datetime.now() + timedelta(days=1)

        csv_data = BillingRecord.objects.csv_report_for_team(team, start, end)

        self.assertEquals(2, len(csv_data))
        self.assertEquals(8, len(csv_data[1]))

        # 2
        sv = add_subtitles(video, 'en', make_subtitle_lines(4), author=user, created=now)
        sl = sv.subtitle_language
                          
        video_changed_tasks(video.pk, sv.pk)

        # A new one shouldn't be created for the same language
        self.assertEquals(1, BillingRecord.objects.all().count())

    def test_update_language_complete(self):
        """
        https://unisubs.sifterapp.com/issues/2225
        Create a version not synced.
        Then later
        """
        BillingRecord.objects.all().delete()

        user = User.objects.all()[0]

        video = Video.objects.filter(teamvideo__isnull=False)[0]
        video.user = user
        video.save()

        first_version = add_subtitles(video, 'en', make_subtitle_lines(4,  is_synced=False), complete=False, author=user)

        # create a transla
        video_changed_tasks(video.pk, first_version.pk)
        self.assertEquals(0, BillingRecord.objects.all().count())
        second_version = add_subtitles(video, 'en', make_subtitle_lines(4), complete=True, author=user)
        video_changed_tasks(video.pk, second_version.pk)

        self.assertEquals(1, BillingRecord.objects.all().count())


    def test_update_source_language(self):
        """
        https://unisubs.sifterapp.com/issues/2225
        Create a version not synced.
        Create a translation.
        Then later finish the original one
        """
        BillingRecord.objects.all().delete()

        user = User.objects.all()[0]

        video = Video.objects.filter(teamvideo__isnull=False)[0]
        video.user = user
        video.save()

        original_version = add_subtitles(
            video, 'en', make_subtitle_lines(4, is_synced=False),
            complete=False, author=user )
        original_lang = original_version.subtitle_language

        video_changed_tasks(video.pk, original_version.pk)
        self.assertEquals(0, BillingRecord.objects.all().count())

        translation_version = add_subtitles(
            video, 'pt', make_subtitle_lines(4, is_synced=False),
                author=user, parents=[original_version])
        translation_language = translation_version.subtitle_language
        # no billing for this one, because it isn't synced!
        self.assertEquals(0, BillingRecord.objects.all().count())


        # now sync them
        original_version = add_subtitles(
            video, 'en', make_subtitle_lines(4, is_synced=True),
                complete=True, author=user)
        original_lang = original_version.subtitle_language
        video_changed_tasks(video.pk, original_version.pk)
        bl_original = BillingRecord.objects.filter(new_subtitle_language=original_lang)
        self.assertEquals(1, bl_original.count())

        translation_version = add_subtitles(
            video, 'pt', make_subtitle_lines(5),
            author=user, parents=[original_version], complete=True)
        video_changed_tasks(video.pk, translation_version.pk)
        bl_translation = BillingRecord.objects.filter(new_subtitle_language=translation_language)
        self.assertEquals(1, bl_translation.count())


    def test_two_languages(self):
        from apps.teams.models import BillingRecord
        from apps.videos.tasks import video_changed_tasks

        BillingRecord.objects.all().delete()

        user = User.objects.all()[0]

        video = Video.objects.filter(teamvideo__isnull=False)[0]
        video.user = user
        video.save()

        sv_en = add_subtitles(video, 'en', make_subtitle_lines(4), author=user, complete=True)
        video_changed_tasks(video.pk, sv_en.pk)

        sv_cs = add_subtitles(video, 'cs', make_subtitle_lines(4), complete=True, author=user)
        video_changed_tasks(video.pk, sv_cs.pk)

        self.assertEquals(2, BillingRecord.objects.all().count())

    def test_incomplete_language(self):
        from apps.teams.models import BillingRecord
        from apps.videos.tasks import video_changed_tasks

        BillingRecord.objects.all().delete()

        user = User.objects.all()[0]

        video = Video.objects.filter(teamvideo__isnull=False)[0]
        video.user = user
        video.save()

        sv_en = add_subtitles(video, 'en', make_subtitle_lines(4), complete=False)

        video_changed_tasks(video.pk, sv_en.pk)

        self.assertEquals(0, BillingRecord.objects.all().count())

    def test_original_language(self):
        from apps.teams.models import BillingRecord
        from apps.videos.tasks import video_changed_tasks

        BillingRecord.objects.all().delete()

        user = User.objects.all()[0]

        video = Video.objects.filter(teamvideo__isnull=False)[0]
        video.user = user
        video.primary_audio_language_code = ''
        video.save()

        sv_en = add_subtitles(video, 'en', make_subtitle_lines(4), complete=True)
        video_changed_tasks(video.pk, sv_en.pk)

        self.assertEquals(1, BillingRecord.objects.all().count())

        br = BillingRecord.objects.all()[0]
        self.assertFalse(br.is_original)
