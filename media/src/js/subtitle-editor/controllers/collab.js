// Amara, universalsubtitles.org
//
// Copyright (C) 2013 Participatory Culture Foundation
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU Affero General Public License as
// published by the Free Software Foundation, either version 3 of the
// License, or (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU Affero General Public License for more details.
//
// You should have received a copy of the GNU Affero General Public License
// along with this program.  If not, see
// http://www.gnu.org/licenses/agpl-3.0.html.

(function() {

    var root = this;

    var CollabController = function($scope, $timeout, SubtitleStorage) {

        // Some modules can be opened and closed. These are the default states.
        $scope.modulesOpen = {
            notes: false,
            pane: false
        };

        // These states define whether the modules are enabled at all.
        $scope.modulesEnabled = {
            approval: false,
            notes: false,
            pane: false
        };

        // If this is a task, set up the proper panels.
        if (SubtitleStorage.getCachedData().task_needs_pane) {
            $scope.modulesOpen = {
                notes: true,
                pane: true
            };

            $scope.modulesEnabled = {
                approval: true,
                notes: true,
                pane: true
            };
        }

        $scope.approve = function() {
            $scope.$root.$emit('approve-task');
        };
        $scope.toggleDocking = function(module) {
            $scope.modulesOpen[module] = !$scope.modulesOpen[module];
        };
        $scope.sendBack = function() {
            $scope.$root.$emit('send-back-task');
        };

        $scope.$root.$on('subtitle-key-up', function($event, options) {
            if (options.parser.needsAnyTranscribed(options.subtitles)) {
                $scope.error = 'You have empty subtitles.';
            } else {
                $scope.error = null;
            }
            $scope.$digest();
        });
        
    };

    root.CollabController = CollabController;

}).call(this);
