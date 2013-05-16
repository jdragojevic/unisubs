# -*- coding: utf-8 -*-
# Amara, universalsubtitles.org
#
# Copyright (C) 2013 Participatory Culture Foundation
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU Affero General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more
# details.
#
# You should have received a copy of the GNU Affero General Public License along
# with this program.  If not, see http://www.gnu.org/licenses/agpl-3.0.html.

"""Django models represention subtitles."""

import itertools
from datetime import datetime, date, timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import simplejson as json
from django.utils.translation import ugettext_lazy as _

from apps.subtitles import cache
from apps.subtitles import shims
from apps.subtitles import signals
from apps.auth.models import CustomUser as User
from apps.videos.models import Video, Action
from babelsubs.storage import SubtitleSet
from babelsubs.storage import diff as diff_subtitles
from babelsubs.generators.html import HTMLGenerator
from babelsubs import load_from

from utils.compress import compress, decompress
from utils.redis_utils import RedisSimpleField
from utils.translation import is_rtl


ALL_LANGUAGES = sorted([(val, _(name)) for val, name in settings.ALL_LANGUAGES],
                       key=lambda v: v[1])
VALID_LANGUAGE_CODES = [unicode(x[0]) for x in ALL_LANGUAGES]

WRITELOCK_EXPIRATION = 30 # 30 seconds


# Utility functions -----------------------------------------------------------
def mapcat(fn, iterable):
    """Mapcatenate.

    Map the given function over the given iterable.  Each mapping should result
    in an interable itself.  Concatenate these results.

    E.g.:

        foo = lambda i: [i, i+1]
        mapcatenate(foo, [20, 200, 2000])
        [20, 21, 200, 201, 2000, 2001]

    """
    return itertools.chain.from_iterable(itertools.imap(fn, iterable))

def ensure_stringy(val):
    """Ensure the given value is a stringy type, like str or unicode.

    If not, a ValidationError will be raised.

    This method is necessary because Django will often do the wrong thing when
    you pass a non-stringy object to a CharField (it will str() the object which
    probably isn't what you want).

    """
    if val == None:
        return

    if not isinstance(val, basestring):
        raise ValidationError('Value must be a string.')

def graphviz(video):
    """Return the dot code for a Graphviz visualization of a video's history."""

    lines = []

    lines.append("digraph video_%s {" % video.video_id)
    lines.append("rankdir = BT;")

    def _name(sv):
        return '%s%d' % (sv.language_code, sv.version_number)

    for sl in video.newsubtitlelanguage_set.all():
        for sv in sl.subtitleversion_set.full():
            lines.append('%s[label="%s"];' % (_name(sv), _name(sv)))

    for sl in video.newsubtitlelanguage_set.all():
        for sv in sl.subtitleversion_set.full():
            for pv in sv.parents.full():
                lines.append("%s -> %s;" % (_name(pv), _name(sv)))

    lines.append("}")

    return lines

def print_graphviz(video_id):
    video = Video.objects.get(video_id=video_id)
    print '\n'.join(graphviz(video))


# Lineage functions -----------------------------------------------------------
def lineage_to_json(lineage):
    return json.dumps(lineage)

def json_to_lineage(json_lineage):
    return json.loads(json_lineage)

def get_lineage(parents):
    """Return a lineage map for a version that has the given parents."""
    lineage = {}

    # The new version's lineage should be the result of merging the parents'
    # lineages, taking the later version whenever there's a conflict, and adding
    # the parent versions themselves to the map.
    for parent in parents:
        l, v = parent.language_code, parent.version_number

        if l not in lineage or lineage[l] < v:
            lineage[l] = v

        for l, v in parent.lineage.items():
            if l not in lineage or lineage[l] < v:
                lineage[l] = v

    return lineage


# SubtitleLanguages -----------------------------------------------------------
class SubtitleLanguageManager(models.Manager):
    #  _   _                ______       ______
    # | | | |               | ___ \      |  _  \
    # | |_| | ___ _ __ ___  | |_/ / ___  | | | |_ __ __ _  __ _  ___  _ __  ___
    # |  _  |/ _ \ '__/ _ \ | ___ \/ _ \ | | | | '__/ _` |/ _` |/ _ \| '_ \/ __|
    # | | | |  __/ | |  __/ | |_/ /  __/ | |/ /| | | (_| | (_| | (_) | | | \__ \
    # \_| |_/\___|_|  \___| \____/ \___| |___/ |_|  \__,_|\__, |\___/|_| |_|___/
    #                                                      __/ |
    #                                                     |___/
    #
    # This manager's methods use custom SQL to perform efficient queries without
    # denormalizing our data model into a tangled mess.
    #
    # These methods are not fun, and they are not pretty, but they ARE fast.
    #
    # Prepare yourself.

    def having_versions(self):
        """Return a QS of SLs that have at least 1 version.

        TODO: See if we need to denormalize this into a field.  I don't think we
        will (and would strongly prefer not to (see the has_version/had_version
        mess we were in before)).

        """
        return self.get_query_set().extra(where=[
            """
            EXISTS (
                SELECT 1
                  FROM subtitles_subtitleversion AS sv
                 WHERE sv.subtitle_language_id = subtitles_subtitlelanguage.id
               AND NOT sv.visibility_override = 'deleted'
            )
            """,
        ])

    def not_having_versions(self):
        """Return a QS of SLs that have zero versions.

        TODO: See if we need to denormalize this into a field.  I don't think we
        will (and would strongly prefer not to (see the has_version/had_version
        mess we were in before)).

        """
        return self.get_query_set().extra(where=[
            """
            NOT EXISTS (
                SELECT 1
                  FROM subtitles_subtitleversion AS sv
                 WHERE sv.subtitle_language_id = subtitles_subtitlelanguage.id
               AND NOT sv.visibility_override = 'deleted'
            )
            """,
        ])


    def having_nonempty_versions(self):
        """Return a QS of SLs that have at least 1 version with 1 or more subtitles."""
        return self.get_query_set().extra(where=[
            """
            EXISTS
            (SELECT 1
               FROM subtitles_subtitleversion AS sv
              WHERE sv.subtitle_language_id = subtitles_subtitlelanguage.id
            AND NOT sv.visibility_override = 'deleted'
                AND sv.subtitle_count > 0)
            """,
        ])

    def not_having_nonempty_versions(self):
        """Return a QS of SLs that have zero versions with 1 or more subtitles."""
        return self.get_query_set().extra(where=[
            """
            NOT EXISTS
            (SELECT 1
               FROM subtitles_subtitleversion AS sv
              WHERE sv.subtitle_language_id = subtitles_subtitlelanguage.id
            AND NOT sv.visibility_override = 'deleted'
                AND sv.subtitle_count > 0)
            """,
        ])


    def having_nonempty_tip(self):
        """Return a QS of SLs that have a tip version with 1 or more subtitles."""
        return self.get_query_set().extra(where=[
            """
            EXISTS (
               SELECT 1 FROM subtitles_subtitleversion AS sv
                INNER JOIN (
                     SELECT subtitle_language_id,
                            MAX(version_number) AS tip_version_number
                       FROM subtitles_subtitleversion AS subver
                      WHERE NOT subver.visibility_override = 'deleted'
                      GROUP BY subtitle_language_id
                ) AS tip_versions ON (
                    sv.subtitle_language_id = tip_versions.subtitle_language_id
                    AND sv.version_number = tip_versions.tip_version_number
                )
                WHERE sv.subtitle_count > 0
                  AND sv.subtitle_language_id = subtitles_subtitlelanguage.id
            )
            """,
        ])

    def not_having_nonempty_tip(self):
        """Return a QS of SLs that do not have a tip version with 1 or more subtitles."""
        return self.get_query_set().extra(where=[
            """
            NOT EXISTS (
               SELECT 1 FROM subtitles_subtitleversion AS sv
                INNER JOIN (
                     SELECT subtitle_language_id,
                            MAX(version_number) AS tip_version_number
                       FROM subtitles_subtitleversion AS subver
                      WHERE NOT subver.visibility_override = 'deleted'
                      GROUP BY subtitle_language_id
                ) AS tip_versions ON (
                    sv.subtitle_language_id = tip_versions.subtitle_language_id
                    AND sv.version_number = tip_versions.tip_version_number
                )
                WHERE sv.subtitle_count > 0
                  AND sv.subtitle_language_id = subtitles_subtitlelanguage.id
            )
            """,
        ])


    def having_public_versions(self):
        """Return a QS of SLs that have at least 1 publicly-visible versions.

        TODO: See if we need to denormalize this into a field.  I don't think we
        will (and would strongly prefer not to (see the has_version/had_version
        mess we were in before)).

        """
        return self.get_query_set().extra(where=[
            """
            EXISTS (
                SELECT 1
                  FROM subtitles_subtitleversion AS sv
                 WHERE sv.subtitle_language_id = subtitles_subtitlelanguage.id
               AND NOT sv.visibility_override = 'deleted'
               AND NOT sv.visibility_override = 'private'
               AND NOT (sv.visibility = 'private' AND sv.visibility_override = '')
            )
            """,
        ])

    def not_having_public_versions(self):
        """Return a QS of SLs that have zero publicly-visible versions.

        TODO: See if we need to denormalize this into a field.  I don't think we
        will (and would strongly prefer not to (see the has_version/had_version
        mess we were in before)).

        """
        return self.get_query_set().extra(where=[
            """
            NOT EXISTS (
                SELECT 1
                  FROM subtitles_subtitleversion AS sv
                 WHERE sv.subtitle_language_id = subtitles_subtitlelanguage.id
               AND NOT sv.visibility_override = 'deleted'
               AND NOT sv.visibility_override = 'private'
               AND NOT (sv.visibility = 'private' AND sv.visibility_override = '')
            )
            """,
        ])


class SubtitleLanguage(models.Model):
    """SubtitleLanguages are the equivalent of a 'branch' in a VCS.

    These exist mostly to coordiante access to a language amongst users.  Most
    of the actual data for the subtitles is stored in the version themselves.

    """
    # Basic Data
    video = models.ForeignKey(Video, related_name='newsubtitlelanguage_set')
    language_code = models.CharField(max_length=16, choices=ALL_LANGUAGES)
    created = models.DateTimeField(editable=False)

    # Should be True if the latest version for this set of subtitles covers all
    # of the video, False otherwise.  This is set and handled entirely
    # independently of versions though.
    subtitles_complete = models.BooleanField(default=False)

    # This field is a temporary shim until we move to the new user interface.
    # A "forked" language is one that was originally a translation but has since
    # been changed to be a standalone language.
    is_forked = models.BooleanField(default=False)

    # Writelocking
    writelock_time = models.DateTimeField(null=True, blank=True,
                                          editable=False)
    writelock_owner = models.ForeignKey(User, null=True, blank=True,
                                        editable=False,
                                        related_name='writelocked_newlanguages')
    writelock_session_key = models.CharField(max_length=255, blank=True,
                                             editable=False)

    # Denormalized signoff/collaborator count fields.
    # These are stored here for speed of retrieval and filtering.
    #
    # They are updated in the update_signoff_counts() method, which is called
    # from the Collaborator .save() method.
    #
    # I'd really like to reconsider whether we need these when we actually start
    # using them.  If we can use some SQL magic in a manager to avoid the
    # denormalized fields but still have speedy queries I'd prefer that to
    # having to make sure these are properly synced.
    unofficial_signoff_count = models.PositiveIntegerField(default=0,
                                                           editable=False)
    official_signoff_count = models.PositiveIntegerField(default=0,
                                                         editable=False)
    pending_signoff_count = models.PositiveIntegerField(default=0,
                                                        editable=False)
    pending_signoff_unexpired_count = models.PositiveIntegerField(default=0,
                                                                  editable=False)
    pending_signoff_expired_count = models.PositiveIntegerField(default=0,
                                                                editable=False)

    followers = models.ManyToManyField(User, blank=True,
            related_name='new_followed_languages', editable=False)

    # Statistics
    subtitles_fetched_count = models.IntegerField(default=0, editable=False)
    subtitles_fetched_counter = RedisSimpleField()

    # Manager
    objects = SubtitleLanguageManager()

    class Meta:
        unique_together = [('video', 'language_code')]


    # Writelocking
    @property
    def is_writelocked(self):
        """Return whether this language is writelocked for subtitling."""
        if self.writelock_time == None:
            return False
        delta = datetime.now() - self.writelock_time
        seconds = delta.days * 24 * 60 * 60 + delta.seconds
        return seconds < WRITELOCK_EXPIRATION

    def can_writelock(self, key):
        """Return whether a user with the session key can writelock this language."""
        return self.writelock_session_key == key or not self.is_writelocked

    def writelock(self, user, key, save=True):
        """Writelock this language for subtitling and save it.

        This method does NO permission checking.  If you want that you'll need
        to use can_writelock() yourself before calling this (probably in
        a transaction).

        `user` is the User who should own the lock.

        `key` is their session key which you can get through request.browser_id

        `save` determines whether this method will save the SubtitleLanguage for
        you.  Pass False if you want to handle saving yourself.

        """
        if user.is_authenticated():
            self.writelock_owner = user
        else:
            self.writelock_owner = None

        self.writelock_session_key = key
        self.writelock_time = datetime.now()

        if save:
            self.save()

    def release_writelock(self, save=True):
        """Writelock this language for subtitling and save it.

        `save` determines whether this method will save the SubtitleLanguage
        for you.  Pass False if you want to handle saving yourself.

        """
        self.writelock_owner = None
        self.writelock_session_key = ''
        self.writelock_time = None

        if save:
            self.save()

    def get_writelock_owner_name(self):
        """Return the human-readable name of the owner of this language's writelock.

        This assumes that the language actually IS writelocked.  If that's not
        the case this method will return nonsensical data, so you'll need to
        check that first.

        """
        if self.writelock_owner == None:
            return "anonymous"
        else:
            return self.writelock_owner.__unicode__()


    def is_rtl(self):
        return is_rtl(self.language_code)


    def __unicode__(self):
        return 'SubtitleLanguage %s / %s / %s' % (
            (self.id or '(unsaved)'), self.video.video_id,
            self.get_language_code_display()
        )

    def save(self, *args, **kwargs):
        assert self.language_code in VALID_LANGUAGE_CODES, \
            "Subtitle Language %s should be a valid code." % self.language_code

        creating = not self.pk

        if creating and not self.created:
            self.created = datetime.now()

        return super(SubtitleLanguage, self).save(*args, **kwargs)


    def get_tip(self, public=False, full=False):
        """Return the tipmost version of this language (if any).

        If public is given, returns the tipmost version that is visible to the
        general public (if any).

        If full is given, select from ALL versions (public, private, AND
        deleted).  Giving both public and full will result in an error.

        """
        if public and full:
            assert False, "Cannot specify public and full in get_tip()!"

        if public:
            versions = SubtitleVersion.objects.public()
        elif full:
            versions = SubtitleVersion.objects.full()
        else:
            versions = SubtitleVersion.objects.extant()

        versions = versions.filter(subtitle_language=self)
        versions = versions.order_by('-version_number')
        versions = versions[:1]

        if versions:
            return versions[0]
        else:
            return None

    def get_public_tip(self):
        """Return the latest public tip for a particular version.

        This is currently being used on the search templates for videos, since
        we can't specify parameters when calling get_tip + we don't have
        template tags (afaik).

        TODO: see if we can remove this somehow.

        """
        return self.get_tip(public=True)

    def first_public_version(self):
        """Returns the very fist version to be made public of none"""
        try:
            return self.subtitleversion_set.public().order_by("version_number")[0]
        except IndexError:
            return None

    def has_public_version(self):
        """Check if there are any public versions for this language."""
        return self.subtitleversion_set.public().exists()

    def is_complete_and_synced(self, public=False):
        """Return whether this language's subtitles are complete and fully synced."""

        if not self.subtitles_complete:
            return False

        version = self.get_tip(public)

        if not version:
            return False

        subtitles = version.get_subtitles()

        return subtitles.fully_synced

    def _sanity_check_parents(self, version, parents):
        r"""Check that the given parents are sane for an SV about to be created.

        There are a few rules checked here.

        First, versions cannot have more than one parent from a single language.
        For example, the following is invalid:

            en fr

            1
            |\
            \ \
             \ 2
              \|
               1

        Second, a parent cannot have a parent that precedes something existing
        in its own lineage.  It's easiest to understand this with an example.
        The following is invalid:

            en fr
            3
            |\
            2 \
            |  \
            1   \
             \   |
              \  |
               2 |
               |/
               1

        This is invalid because English was based off of French version 2, and
        then you tried to say a later version was based on French version 1.

        If English version 3 had been based on French version 2 (or later) that
        would be have been okay.

        """

        # There can be at most one parent from any given language.
        if len(parents) != len(set([v.language_code for v in parents])):
            raise ValidationError(
                "Versions cannot have two parents from the same language!")

        for parent in parents:
            if parent.language_code in version.lineage:
                if parent.version_number < version.lineage[parent.language_code]:
                    raise ValidationError(
                        "Versions cannot have parents that precede parents in "
                        "their lineage!")


    def add_version(self, *args, **kwargs):
        """Add a SubtitleVersion to the tip of this language.

        You probably don't need this.  You probably want
        apps.subtitles.pipeline.add_subtitles instead.

        Does not check any writelocking -- that's up to the pipeline.

        """
        kwargs['subtitle_language'] = self
        kwargs['language_code'] = self.language_code
        kwargs['video'] = self.video

        tip = self.get_tip(full=True)

        version_number = ((tip.version_number + 1) if tip else 1)
        kwargs['version_number'] = version_number

        parents = (kwargs.pop('parents', None) or [])

        if tip:
            parents.append(tip)

        kwargs['lineage'] = get_lineage(parents)

        ensure_stringy(kwargs.get('title'))
        ensure_stringy(kwargs.get('description'))

        sv = SubtitleVersion(*args, **kwargs)

        sv.set_subtitles(kwargs.get('subtitles', None))
        self._sanity_check_parents(sv, parents)

        sv.full_clean()
        sv.save()

        for p in parents:
            sv.parents.add(p)

        cache.invalidate_language_cache(self)
        return sv

    def is_synced(self, public=True):
        value = cache.get_is_synced(self, public)
        if value is None:
            value = self.get_tip(public=public).is_synced()
            cache.set_is_synced(self, public, value)
        return value

    def nuke_language(self):
        """Delete all SubtitleVersions for this language, as well as all
        SubtitleVersions for dependent languages.
        """
        # delete dependent languages first
        languages = [self] + self.get_dependent_subtitle_languages()
        for lang in languages:
            for sv in lang.subtitleversion_set.extant().all():
                sv.unpublish(delete=True)
            signals.language_deleted.send(lang)

    def update_signoff_counts(self):
        """Update the denormalized signoff count fields and save."""

        cs = self.collaborator_set.all()

        self.official_signoff_count = len(
            [c for c in cs if c.signoff and c.signoff_is_official])

        self.unofficial_signoff_count = len(
            [c for c in cs if c.signoff and (not c.signoff_is_official)])

        self.pending_signoff_count = len(
            [c for c in cs if (not c.signoff)])

        self.pending_signoff_expired_count = len(
            [c for c in cs if (not c.signoff) and c.expired])

        self.pending_signoff_unexpired_count = len(
            [c for c in cs if (not c.signoff) and (not c.expired)])

        self.save()

    def get_description(self, public=True):
        v = self.get_tip(public=public)

        if v:
            return v.description

        return self.video.description

    def get_title(self, public=True):
        v = self.get_tip(public=public)

        if v:
            return v.title

        return self.video.title


    def get_subtitle_count(self):
        tip = self.get_tip()
        if tip:
            return tip.get_subtitle_count()
        return 0


    def is_primary_audio_language(self):
        return self.video.primary_audio_language_code == self.language_code


    def versions_for_user(self, user):
        from teams.models import TeamVideo
        from teams.permissions import get_member

        try:
            team_video = (TeamVideo.objects.select_related('team')
                                           .get(video=self.video))
        except TeamVideo.DoesNotExist:
            team_video = None

        if team_video:
            member = get_member(user, team_video.team)

            if not member:
                return self.subtitleversion_set.public()

        return self.subtitleversion_set.extant()

    def version(self, public_only=True, version_number=None):
        """Return a SubtitleVersion of this language matching the arguments.

        Returns None if no versions match.

        Cannot return deleted versions.  If you need a deleted version you need
        to look it up another way.

        """
        assert self.pk, "Can't find a version for a language that hasn't been saved"

        qs = self.subtitleversion_set
        qs = qs.public() if public_only else qs.extant()

        if version_number != None:
            qs = qs.filter(version_number=version_number)
        else:
            qs = qs.order_by('-version_number')

        try:
            return qs[:1].get()
        except SubtitleVersion.DoesNotExist:
            return None


    def get_translation_source_language_code(self, ignore_forking=False):
        """
        Returns the language code of the language that served as the
        source language for this translation, or None if no languages
        are found on the lineage.

        In some cases, you might want to ignore the is_forked attribute. For
        example, on the new editor, you want to see the language this was
        translated from, even if it was forked. Unless that's your very specific
        use case, just leave `ignore_forking` as False.

        Right now, we're only allowing for 1 source language, but that
        could be revisited in the future.

        """
        if not ignore_forking and self.is_forked:
            return None

        tip_version = self.get_tip()
        if not tip_version:
            return None

        lineage = tip_version.lineage
        source_codes = [lc for lc in lineage.keys() if lc != self.language_code]

        return source_codes[0] if source_codes else None

    def get_translation_source_language(self, ignore_forking=False):
        """
        Returns the new SubtitleLanguage object that served as the
        source language for this translation, or None if no languages
        are found on the lineage.

        Right now, we're only allowing for 1 source language, but that
        could be revisited in the future.

        """
        source_lc = self.get_translation_source_language_code(
            ignore_forking=ignore_forking)

        if not source_lc:
            return None

        try:
            return SubtitleLanguage.objects.get(
                video=self.video, language_code=source_lc)
        except (SubtitleLanguage.DoesNotExist, IndexError):
            return None

    def get_translation_source_version(self, ignore_forking=False):
        '''
        Returns the new SubtitleVersion object that served as the
        source for this translation, or None if no versions
        are found on the lineage.

        Right now, we're only allowing for 1 version, but that
        could be revisited in the future.
        '''
        if  not ignore_forking and self.is_forked:
            return None

        tip_version = self.get_tip()
        if not tip_version:
            return None

        lineage = tip_version.lineage

        try:
            source_pair = [(lc, version_no) for lc,version_no in lineage.items()\
                           if lc != self.language_code][0]
            return SubtitleVersion.objects.get(
                language_code = source_pair[0],
                version_number = source_pair[1],
                video__id = self.video.id)
        except (SubtitleVersion.DoesNotExist, IndexError):
            return None
        return None

    def get_dependent_subtitle_languages(self):
        """Return a list of SLs that are dependents/translations of this.

        This is a shim for the existing UI.  Once the new one comes this
        monstrosity will be torn out.

        """
        # Start with all the subtitle languages for the video.
        sls = self.video.newsubtitlelanguage_set

        # Exclude this one.
        sls = sls.exclude(id=self.id)

        # Exclude those that are already forked.  They can't be dependents.
        sls = sls.exclude(is_forked=True)

        # Realize the query to get the list of remaining SubtitleLanguages that
        # could possibly be dependents.  Hopefully there shouldn't be too many.
        sls = list(sls)

        # Check the lineage maps for the candidates to determine if they're
        # dependents.
        results = []
        for sl in sls:
            tip = sl.get_tip()
            if tip and self.language_code in tip.lineage:
                results.append(sl)

        return results


    def get_widget_url(self, mode=None, task_id=None):
        """SHIM for getting the widget URL for this language."""
        return shims.get_widget_url(self, mode, task_id)

    @models.permalink
    def get_absolute_url(self):
        return ('videos:translation_history',
                [self.video.video_id, self.language_code or 'unknown', self.pk])

    @property
    def has_version(self):
        """
        http://amara.readthedocs.org/en/latest/model-refactor.html#id4
        """
        return SubtitleLanguage.objects.having_nonempty_versions().filter(
                video=self.video).exists()

    def notification_list(self, exclude=None):
        qs = self.followers.filter(notify_by_email=True, is_active=True)

        if exclude:
            if not isinstance(exclude, (list, tuple)):
                exclude = [exclude]
            qs = qs.exclude(pk__in=[u.pk for u in exclude if u])
        return qs

    def in_progress(self):
        """Return whether this SubtitleLanguage is "in progress".

        Moderated teams:

            It's in progress if it has an unapproved draft

        Unmoderated teams:

            It's in progress if it has subs but not marked as complete

        """
        if self.video.is_moderated:
            if self.get_tip().is_private():
                return True
        else:
            if not self.subtitles_complete and \
                    self.get_tip().get_subtitle_count() > 0:
                return True

        return False

    @property
    def is_imported_from_youtube_and_not_worked_on(self):
        versions = self.subtitleversion_set.full()
        if versions.count() > 1 or versions.count() == 0:
            return False

        version = versions[0]

        if version.note == 'From youtube':
            return True

        return False


# SubtitleVersions ------------------------------------------------------------
class SubtitleVersionManager(models.Manager):
    use_for_related_fields = True

    # ---------------------------- IMPORTANT ----------------------------------
    #
    # Django Managers contain proxy methods to querysets like .filter() and
    # such.  DO NOT USE THEM.  They will bypass the full/extant/public methods
    # that perform the appropriate filtering.
    #
    # So instead of:
    #
    #     sl.subtitleversion_set.filter(...)
    #
    # You should do:
    #
    #     sl.subtitleversion_set.full().filter(...)
    #
    # Normally we'd disable all these proxy methods so we could find all the
    # places where they're used, and it would be safe and break loudly instead
    # of silently doing unsafe things.  Unfortunately Django's Model class uses
    # these proxy methods instead of going through get_query_set(), so we're out
    # of luck.

    # These three methods are your main entry point into SubtitleVersion querysets.
    def full(self):
        """Return a queryset of ALL versions (including deleted ones)."""
        return self.get_query_set()

    def extant(self):
        """Return a queryset of all non-deleted versions."""
        return (self.get_query_set()
                    .exclude(visibility_override='deleted'))

    def public(self):
        """Return a queryset of all publicly-visible versions."""
        return (self.get_query_set()
                    .exclude(visibility='private', visibility_override='')
                    .exclude(visibility_override='private')
                    .exclude(visibility_override='deleted'))

    def all(self):
        assert False, ('all() is disabled on SubtitleVersion sets.  '
                       'Use full(), extant(), or public() instead.')

ORIGIN_API = 'api'
ORIGIN_IMPORTED = 'imported'
ORIGIN_LEGACY_EDITOR = 'web-legacy-editor'
ORIGIN_ROLLBACK = 'rollback'
ORIGIN_SCRIPTED = 'scripted'
ORIGIN_TERN = 'tern'
ORIGIN_UPLOAD = 'upload'
ORIGIN_WEB_EDITOR = 'web-editor'

SUBTITLE_VERSION_ORIGINS = (
    (ORIGIN_API, _("API")),
    (ORIGIN_LEGACY_EDITOR, _("Subtitle Editor")),
    (ORIGIN_IMPORTED, _("Imported")),
    (ORIGIN_ROLLBACK, _("Rollback")),
    (ORIGIN_SCRIPTED, _("Scripted")),
    (ORIGIN_TERN, _("Tern")),
    (ORIGIN_UPLOAD, _("Uploaded")),
    (ORIGIN_WEB_EDITOR, _("Through web editor")),
)

class SubtitleVersion(models.Model):
    """SubtitleVersions are the equivalent of a 'changeset' in a VCS.

    They are designed with a few key principles in mind.

    First, SubtitleVersions should be mostly immutable.  Once written they
    should never be changed, unless a team needs to publish or unpublish them.
    Any other changes should simply create a new version.

    Second, SubtitleVersions are self-contained.  There's a little bit of
    denormalization going on with the video and language_code fields, but this
    makes it much easier for a SubtitleVersion to stand on its own and will
    improve performance overall.

    Because they're (mostly) immutable, the denormalization is less of an issue
    than it would be otherwise.

    You should only create new SubtitleVersions through the `add_version` method
    of SubtitleLanguage instances.  This will ensure consistency and handle
    updating the parentage and version numbers correctly.

    """
    parents = models.ManyToManyField('self', symmetrical=False, blank=True)

    video = models.ForeignKey(Video, related_name='newsubtitleversion_set')
    subtitle_language = models.ForeignKey(SubtitleLanguage)
    language_code = models.CharField(max_length=16, choices=ALL_LANGUAGES)

    # If you just want to *check* the visibility of a version you probably want
    # to use the is_public and is_private methods instead, which handle the
    # logic of visibility + visibility_override.
    visibility = models.CharField(max_length=10,
                                  choices=(('public', 'public'),
                                           ('private', 'private'),),
                                  default='public')

    # Visibility override can be used by team admins to force a specific type of
    # visibility for a version.  If set, it takes precedence over, but does not
    # affect, the main visibility field.
    visibility_override = models.CharField(max_length=10, blank=True,
                                           choices=(('public', 'public'),
                                                    ('private', 'private'),
                                                    ('deleted', 'deleted'),),
                                           default='')

    version_number = models.PositiveIntegerField(default=1)

    author = models.ForeignKey(User, default=User.get_anonymous,
                               related_name='newsubtitleversion_set')

    title = models.CharField(max_length=2048, blank=True)
    description = models.TextField(blank=True)
    note = models.CharField(max_length=512, blank=True, default='')

    # If this version is a rollback we record the version number of its source.
    # Note that there are three possible values here:
    #
    # None: This version is not a rollback.
    # 0: This version is a rollback, but we don't know the source (legacy data).
    # 1+: This version is a rollback and the source is version N.
    #
    # You should probably just use is_rollback and get_rollback_source to work
    # with this value.
    rollback_of_version_number = models.PositiveIntegerField(null=True,
                                                             blank=True,
                                                             default=None)

    # Keeps tab of how this SV was originated (uploads, api, etc)
    origin = models.CharField(max_length=255, choices=SUBTITLE_VERSION_ORIGINS,
                              blank=True, default='')
    # Denormalized count of the number of subtitles this version contains, for
    # easier filtering later.
    subtitle_count = models.PositiveIntegerField(default=0)

    created = models.DateTimeField(editable=False)

    # Subtitles are stored in a text blob, serialized as base64'ed zipped XML
    # (oh the joys of Django).  Use the subtitles property to get and set them.
    # You shouldn't be touching this field.
    serialized_subtitles = models.TextField()

    # Lineage is stored as a blob of JSON to save on DB rows.  You shouldn't
    # need to touch this field yourself, use the lineage property.
    serialized_lineage = models.TextField(blank=True)

    objects = SubtitleVersionManager()

    def get_subtitles(self):
        """Return the SubtitleSet for this version.

        A SubtitleSet will always be returned.  It may be empty if there are no
        subtitles.

        """
        # We cache the parsed subs for speed.
        if self._subtitles == None:
            self._subtitles = load_from(decompress(self.serialized_subtitles),
                    type='dfxp').to_internal()

        return self._subtitles

    def set_subtitles(self, subtitles):
        """Set the SubtitleSet for this version.

        You have a few options here:

        * Passing None will set the subtitles to an empty set.
        * Passing a SubtitleSet will set the subtitles to that set.
        * Passing a string of XML will treat it as DXFP and set it directly.
        * Passing a vanilla list (or any iterable) of subtitle tuples will
          create a SubtitleSet from that.

        """
        # TODO: Fix the language code to use the proper standard.
        if subtitles == None:
            subtitles = SubtitleSet(self.language_code)
        elif isinstance(subtitles, str) or isinstance(subtitles, unicode):
            subtitles = SubtitleSet(self.language_code, initial_data=subtitles)
        elif isinstance(subtitles, SubtitleSet):
            pass
        else:
            try:
                i = iter(subtitles)
                subtitles = SubtitleSet.from_list(self.language_code, i)
            except TypeError:
                raise TypeError("Cannot create SubtitleSet from type %s"
                                % str(type(subtitles)))

        self.subtitle_count = len(subtitles)
        self.serialized_subtitles = compress(subtitles.to_xml())

        # We cache the parsed subs for speed.
        self._subtitles = subtitles


    def get_lineage(self):
        # We cache the parsed lineage for speed.
        if self._lineage == None:
            if self.serialized_lineage:
                self._lineage = json_to_lineage(self.serialized_lineage)
            else:
                self._lineage = {}

        return self._lineage

    def set_lineage(self, lineage):
        self.serialized_lineage = lineage_to_json(lineage)
        self._lineage = lineage

    lineage = property(get_lineage, set_lineage)

    class Meta:
        unique_together = [('video', 'subtitle_language', 'version_number'),
                           ('video', 'language_code', 'version_number')]


    def __init__(self, *args, **kwargs):
        """Create a new SubtitleVersion.

        You probably don't need this.  You probably want
        apps.subtitles.pipeline.add_subtitles instead.  Or at the very least you
        want the add_version method of SubtitleLanguage instances.

        `subtitles` can be given in any of the forms supported by set_subtitles.

        `lineage` should be a Python dictionary describing the lineage of this
        version.

        """
        # This is a bit clumsy, but we need to handle the subtitles kwarg like
        # this for it to work properly.  If it's given, we set the subtitles
        # appropriately after we create the version object.  If it's not given,
        # we *don't* set the subtitles at all -- we just let the
        # serialized_subtitles field stay as it is.
        has_subtitles = 'subtitles' in kwargs
        subtitles = kwargs.pop('subtitles', None)

        lineage = kwargs.pop('lineage', None)

        super(SubtitleVersion, self).__init__(*args, **kwargs)

        self._subtitles = None
        if has_subtitles:
            self.set_subtitles(subtitles)

        self._lineage = None
        if lineage != None:
            self.lineage = lineage

    def __unicode__(self):
        return u'SubtitleVersion %s / %s / %s v%s' % (
            (self.id or '(unsaved)'), self.video.video_id,
            self.get_language_code_display(), self.version_number
        )


    def clean(self):
        if self.rollback_of_version_number != None:
            if self.rollback_of_version_number >= self.version_number:
                raise ValidationError(
                    "The version number of a rollback's source must be less "
                    "than version number of the rollback itself!")

    def save(self, *args, **kwargs):
        creating = not self.pk

        if creating and not self.created:
            self.created = datetime.now()

        # Sanity checking of the denormalized data.
        assert self.language_code == self.subtitle_language.language_code, \
               "Version language code does not match Language language code!"

        assert self.video_id == self.subtitle_language.video_id, \
               "Version video does not match Language video!"

        assert self.visibility in ('public', 'private',), \
            "Version visibility must be either 'public' or 'private'!"

        from django.conf import settings
        if hasattr(settings, 'TERN_IMPORT') and settings.TERN_IMPORT:
            # This check is a shim for the data import.  We can delete it once
            # that's done and just always create an action.
            pass
        else:
            Action.create_caption_handler(self, self.created)

        return super(SubtitleVersion, self).save(*args, **kwargs)


    def get_ancestors(self):
        """Return all ancestors of this version.  WARNING: MAY EAT YOUR DB!

        Returning all ancestors of a version is very database-intensive, because
        we need to walk each relation.  It will make roughly l^b database calls,
        where l is the length of a branch of history and b is the "branchiness".

        You probably don't need this.  You probably want to use the lineage
        instead.  This is mostly here for sanity tests.

        """
        def _ancestors(version):
            return [version] + list(mapcat(_ancestors, version.parents.full()))

        return set(mapcat(_ancestors, self.parents.full()))

    def get_subtitle_count(self):
        # TODO: babelsubs now supports len() on SubtitleSet instances
        return len([s for s in self.get_subtitles().subtitle_items()])

    def get_changes(self):
        """Return (time_change, text_change).

        Beware.

        This was ported over from the old data model as a hack.  There are
        probably lots of cases where it doesn't work right.

        What we *really* need to do is sit down and come up with a scheme for
        diffing subtitle versions meaningfully.  Until then, we have this
        monstrosity.  Godspeed.

        """
        # TODO: Time only changes aren't quite right.

        if hasattr(self, '_time_change') and hasattr(self, '_text_change'):
            return (self._time_change, self._text_change)

        parent = self.previous_version()

        if not parent:
            return (1.0, 1.0)

        diff_data = diff_subtitles(parent.get_subtitles(), self.get_subtitles(),
                                   HTMLGenerator.MAPPINGS)

        self._text_change = diff_data['text_changed']
        self._time_change = diff_data['time_changed']

        return self._time_change, self._text_change

    @property
    def time_change(self):
        if not hasattr(self, '_time_change'):
            self.get_changes()

        if not self._time_change:
            return '0%'
        else:
            return '%.0f%%' % (self._time_change * 100)

    @property
    def text_change(self):
        if not hasattr(self, '_text_change'):
            self.get_changes()

        if not self._text_change:
            return '0%'
        else:
            return '%.0f%%' % (self._text_change * 100)


    def is_private(self):
        if self.visibility_override in ('public', 'deleted'):
            return False
        elif self.visibility_override == 'private':
            return True
        else:
            return self.visibility == 'private'

    def is_public(self):
        if self.visibility_override == 'public':
            return True
        elif self.visibility_override in ('private', 'deleted'):
            return False
        else:
            return self.visibility == 'public'

    def is_deleted(self):
        return self.visibility_override == 'deleted'

    def is_rollback(self):
        """Return whether this version is a rollback of another version."""

        return self.rollback_of_version_number != None

    def get_rollback_source(self, full):
        """Return the SubtitleVersion that is the source for this rollback, or None.

        If full is given, deleted source versions will be returned.  Otherwise
        None will be returned if the source version has been deleted.

        """
        n = self.rollback_of_version_number
        if n == 0 or n == None:
            # Non-rollbacks and legacy rollbacks have no source.
            return None
        else:
            qs = self.sibling_set.full() if full else self.sibling_set.extant()
            try:
                return qs.get(version_number=n)
            except SubtitleVersion.DoesNotExist:
                # This can occur when full=False and the source version is
                # deleted.  In this case we just return None.
                return None


    @property
    def sibling_set(self):
        """Return a manager of a version's sibling versions, including itself.

        Sibling versions are versions for the same video and language.

        Since this returns a SubtitleVersionManager you can filter it further
        with .public() and so on.

        """
        return self.subtitle_language.subtitleversion_set


    # Metadata
    def _get_metadata(self, key):
        """Return the metadata for this version for the given key, or None."""
        try:
            m = self.metadata.get(key=SubtitleVersionMetadata.KEY_IDS[key])
            return m.get_data()
        except SubtitleVersionMetadata.DoesNotExist:
            return None


    def get_reviewed_by(self):
        """Return the User that reviewed this version, or None.  Hits the DB."""
        return self._get_metadata('reviewed_by')

    def get_approved_by(self):
        """Return the User that approved this version, or None.  Hits the DB."""
        return self._get_metadata('approved_by')

    def get_workflow_origin(self):
        """Return the step of the workflow where this version originated, or None.

        Hits the DB.

        May be None if this version didn't come from any workflow step.

        """
        return self._get_metadata('workflow_origin')


    def _set_metadata(self, key, value):
        v, created = SubtitleVersionMetadata.objects.get_or_create(
                        subtitle_version=self,
                        key=SubtitleVersionMetadata.KEY_IDS[key])
        v.data = value
        v.save()


    def set_reviewed_by(self, user):
        """Set the User that reviewed this version."""
        self.subtitle_language.followers.add(user)
        self._set_metadata('reviewed_by', user.pk)

    def set_approved_by(self, user):
        """Set the User that approved this version."""
        self._set_metadata('approved_by', user.pk)

    def set_workflow_origin(self, origin):
        """Set the step of the workflow that this version originated in."""
        self._set_metadata('workflow_origin', origin)

    def next_version(self, full=False):
        """Return the next SubtitleVersion.

        By default this does not return deleted versions.  If full is given
        deleted versions will be returned.

        """
        qs = self.sibling_set.full() if full else self.sibling_set.extant()
        try:
            return (qs.filter(version_number__gt=self.version_number)
                      .order_by('version_number')[0])
        except IndexError:
            return None

    def previous_version(self, full=False):
        """Return the previous SubtitleVersion.


        By default this does not return deleted versions.  If full is given
        deleted versions will be returned.

        """
        qs = self.sibling_set.full() if full else self.sibling_set.extant()
        try:
            return (qs.filter(version_number__lt=self.version_number)
                      .order_by('-version_number')[0])
        except IndexError:
            return None

    def revision_time(self):
        today = date.today()
        yesterday = today - timedelta(days=1)
        d = self.created.date()
        if d == today:
            return 'Today'
        elif d == yesterday:
            return 'Yesterday'
        else:
            d = d.strftime('%m/%d/%Y')
        return d

    @property
    def has_subtitles(self):
        return self.subtitle_count is not 0

    def is_synced(self):
        return self.get_subtitles().fully_synced

    def publish(self):
        """Make this version publicly viewable."""

        team_video = self.video.get_team_video()

        assert team_video, \
               "Cannot unpublish for a video not moderated by a team."
        self.visibility = 'public'
        self.save()

    def unpublish(self, delete=False):
        """Unpublish this version.

        If delete is given, "delete" it entirely (not *really*, of course).

        """
        team_video = self.video.get_team_video()

        self.visibility_override = 'deleted' if delete else 'private'
        self.save()

    @models.permalink
    def get_absolute_url(self):
        return ('videos:subtitleversion_detail',
                [self.video.video_id, self.language_code, self.subtitle_language.pk,
                 self.pk])

class SubtitleVersionMetadata(models.Model):
    """This model is used to add extra metadata to SubtitleVersions.

    This is basically a shim for the broken-ass tasks system that should go away
    once we tear that out.  See the corresponding model of the same name in
    videos.models for more information.

    """
    KEY_CHOICES = (
        (100, 'reviewed_by'),
        (101, 'approved_by'),
        (200, 'workflow_origin'),
    )
    KEY_NAMES = dict(KEY_CHOICES)
    KEY_IDS = dict([choice[::-1] for choice in KEY_CHOICES])

    WORKFLOW_ORIGINS = ('transcribe', 'translate', 'review', 'approve')

    key = models.PositiveIntegerField(choices=KEY_CHOICES)
    data = models.TextField(blank=True)
    subtitle_version = models.ForeignKey(SubtitleVersion, related_name='metadata')

    created = models.DateTimeField(auto_now_add=True, editable=False)
    modified = models.DateTimeField(auto_now=True, editable=False)

    class Meta:
        unique_together = (('key', 'subtitle_version'),)
        verbose_name_plural = 'subtitle version metadata'

    def __unicode__(self):
        return u'%s - %s' % (self.subtitle_version, self.get_key_display())

    def get_data(self):
        if self.get_key_display() in ['reviewed_by', 'approved_by']:
            return User.objects.get(pk=int(self.data))
        else:
            return self.data


# Collaborators ---------------------------------------------------------------
class CollaboratorManager(models.Manager):
    def get_for(self, subtitle_language):
        return self.get_query_set().filter(subtitle_language=subtitle_language)

    def get_all_signoffs_for(self, subtitle_language):
        return self.get_for(subtitle_language).filter(signoff=True)

    def get_peer_signoffs_for(self, subtitle_language):
        return (self.get_all_signoffs_for(subtitle_language)
                    .filter(signoff_is_official=False))

    def get_official_signoffs_for(self, subtitle_language):
        return (self.get_all_signoffs_for(subtitle_language)
                    .filter(signoff_is_official=True))

    def get_unsignedoff_for(self, subtitle_language, include_expired=False):
        qs = self.get_for(subtitle_language).filter(signoff=False)

        if not include_expired:
            qs = qs.exclude(expired=True)

        return qs

class Collaborator(models.Model):
    """Collaborator models represent a user working on a specific language."""

    user = models.ForeignKey(User)
    subtitle_language = models.ForeignKey(SubtitleLanguage)

    signoff = models.BooleanField(default=False)
    signoff_is_official = models.BooleanField(default=False)
    expired = models.BooleanField(default=False)

    expiration_start = models.DateTimeField(editable=False)

    created = models.DateTimeField(editable=False)

    objects = CollaboratorManager()

    class Meta:
        unique_together = (('user', 'subtitle_language'),)


    def save(self, *args, **kwargs):
        creating = not self.pk

        if creating and not self.created:
            self.created = datetime.now()

        if creating and not self.expiration_start:
            self.expiration_start = self.created

        result = super(Collaborator, self).save(*args, **kwargs)

        # Update the denormalized signoff count fields for SubtitleLanguages.
        # This has to be done after we've saved this Collaborator so the changes
        # will take effect.
        self.subtitle_language.update_signoff_counts()

        return result


