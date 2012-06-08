# Amara, universalsubtitles.org
# 
# Copyright (C) 2012 Participatory Culture Foundation
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see 
# http://www.gnu.org/licenses/agpl-3.0.html.

from django.core.management.base import BaseCommand
from django.conf import settings
import optparse
import socket
class Command(BaseCommand):
    help = u'Lists the settings values for a given setting name'
    
    option_list = BaseCommand.option_list + (
        optparse.make_option('--single-host',
            action='store_true', dest='single_host', default=False,
            help="Print only the value for one host"),
    )

    def handle(self, *args, **kwargs):
        if kwargs.get("single_host", False):
            for name in args :
                print getattr(settings, name, "")
            return
        hostname = socket.gethostname()
        print "@ %s"  % hostname
        for name in args :
            print "\t%s : %s" % (name, getattr(settings, name, "empty"))









