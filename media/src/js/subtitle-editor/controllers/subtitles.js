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

var angular = angular || null;

(function() {

    var root = this;
    var _ = root._.noConflict();
    var $ = root.AmarajQuery;

    var LanguageSelectorController = function($scope, SubtitleStorage, SubtitleListFinder) {
        /**
         * This controller is responsible for the language and version selector
         * widget.  The widget allows the user to select a reference language and
         * version when translating subtitles into another language.
         *
         * The $scope contains 'languages' and 'versions'.  Each list is
         * represented in the UI as a <select> element.  The selected language or
         * version is stored on the $scope as a 'language' and 'version' model.
         *
         * Whenever the language selection is changed, we update the list of
         * versions.  When a new version is selected, we retrieve the subtitles
         * (either from memory or from the API via ajax) and display them in the
         * side panel.
         */

        /**
         * The second param will be either an int or the version data object,
         * depending if this is being set from the bootstrapped value or later
         * fetches.
         */
        $scope.languageChanged = function(lang, versionOrVersionNumber, another) {
            // this gets called both on setInitialDisplayLanguage manually at
            // the first start up, or through the changes to the scope.language.
            // in the later cases, angular sends (newLang, oldLang) so we can
            // detect if anything is actually changed. In this case, we just bail
            // out, because nothing has actually changed.
            if (lang == versionOrVersionNumber){
                return;
            }
            var vers, language, versionNumber;

            if (lang) {
                language = lang;
            } else {
                language = $scope.language;
            }

            if (!language) {
                return;
            }

            vers =_.sortBy(language.versions, function(item) {
                return item.version_no;
            });

            $scope.versions = vers.reverse();

            if (versionOrVersionNumber !== undefined ){
                if (!isNaN(parseInt(versionOrVersionNumber.version_no))){
                    versionNumber = parseInt(versionOrVersionNumber.version_no);
                }else if(!isNaN(parseInt(versionOrVersionNumber))){
                    versionNumber = parseInt(versionOrVersionNumber);
                }
            }
            if (vers.length && vers.length > 0) {
                if (isNaN(parseInt(versionNumber))){
                    $scope.version = $scope.versions[0];
                }else{
                    $scope.version = _.find($scope.versions, function(version){
                        return version.version_no == versionNumber;
                    });
                }
            }
        };
        $scope.setReferenceSubs = function(subtitleData) {
            if (!$scope.refSubList) {
                $scope.refSubList = SubtitleListFinder.get('reference-subtitle-set');
            }
            $scope.refSubList.scope.onSubtitlesFetched(subtitleData);
        };
        $scope.versionChanged = function(newVersion) {

            if (!newVersion) {
                return;
            }
            // new version can be the version number of the version object
            if (!newVersion.version_no){
                newVersion = $scope.versions[newVersion];
            }

            var subtitlesXML = newVersion.subtitlesXML;

            if (!subtitlesXML) {
                SubtitleStorage.getSubtitles(
                    $scope.language.code,
                    newVersion.version_no,
                    function(subtitleData) {
                        $scope.version.subtitlesXML = subtitleData.subtitlesXML;
                        $scope.setReferenceSubs(subtitleData);
                    });
            } else {
                $scope.setReferenceSubs(newVersion);
            }
        };

        $scope.setInitialDisplayLanguage = function(allLanguages, languageCode, versionNumber){

            $scope.languages = allLanguages;
            $scope.language = _.find(allLanguages, function(item) {
                return item.code == languageCode;
            });
            $scope.languageChanged($scope.language, versionNumber);
        }

        $scope.$watch('language', $scope.languageChanged);
        $scope.$watch('version', $scope.versionChanged);
    };
    var SaveSessionController = function($scope, SubtitleListFinder, SubtitleStorage) {

        $scope.discard = function() {

            $scope.showCloseModal();

        };
        $scope.getNotes = function() {
            var collabScope = angular.element($('section.collab').get(0)).scope();
            return collabScope.notes || '';
        };
        $scope.saveAndApprove = function() {

            $scope.saveSession().then(function(response) {
                if ($scope.status === 'saved') {

                    $scope.status = 'approving';

                    SubtitleStorage.approveTask(response, $scope.getNotes()).then(function onSuccess(response) {

                        $scope.$root.$emit('show-loading-modal', 'Subtitles saved, task approved. Redirecting…');
                        window.location = $scope.primaryVideoURL;

                    }, function onError() {
                        $scope.status = 'error';
                        $scope.showErrorModal();
                    });
                }
            });

        };
        $scope.save = function() {

            $scope.saveSession().then(function(response) {
                if ($scope.status === 'saved') {
                    $scope.showCloseModal();
                }
            });
        };
        $scope.saveAndSendBack = function() {
            $scope.saveSession().then(function(response) {
                if ($scope.status === 'saved') {

                    $scope.status = 'sending-back';

                    SubtitleStorage.sendBackTask(response, $scope.getNotes()).then(function onSuccess(response) {

                        $scope.$root.$emit('show-loading-modal', 'Subtitles saved, task sent back. Redirecting…');
                        window.location = $scope.primaryVideoURL;
                        
                    }, function onError() {
                        $scope.status = 'error';
                        $scope.showErrorModal();
                    });

                }
            });
        };
        $scope.saveSession = function() {
            if ($scope.status !== 'saving') {
                $scope.status = 'saving';

                var promise = SubtitleListFinder.get('working-subtitle-set').scope.saveSubtitles();

                promise.then(function onSuccess(response) {
                    $scope.status = 'saved';
                }, function onError() {
                    $scope.status = 'error';
                    $scope.showErrorModal();
                });

                return promise;
            }
        };
        $scope.setCloseStates = function() {

            var subtitleListScope = SubtitleListFinder.get('working-subtitle-set').scope;

            $scope.fromOldEditor = window.location.search.indexOf('from-old-editor') !== -1 ? true : false;
            $scope.primaryVideoURL = '/videos/' + subtitleListScope.videoID + '/';

            if ($scope.fromOldEditor) {
                $scope.dialogURL = '/onsite_widget/?config=' + window.location.search.split('config=')[1];
            }
        };
        $scope.showCloseModal = function() {

            var buttons = [];

            if ($scope.fromOldEditor) {
                buttons.push({
                    'text': 'Back to full editor', 'class': 'yes', 'fn': function() {
                        window.location = $scope.dialogURL;
                    }
                });
            }

            buttons.push({
                'text': 'Exit', 'class': 'no', 'fn': function() {
                    window.location = $scope.primaryVideoURL;
                }
            });

            if ($scope.status !== 'saved') {

                buttons.push({
                    'text': "Wait, don't discard my changes!", 'class': 'last-chance', 'fn': function() {
                        $scope.$root.$broadcast('hide-modal');
                    }
                });

            }

            $scope.$root.$emit('show-modal', {
                heading: ($scope.status === 'saved' ? 'Your changes have been saved.' : 'Your changes will be discarded.'),
                buttons: buttons
            });
        };
        $scope.showErrorModal = function(message) {

            var subtitleListScope = SubtitleListFinder.get('working-subtitle-set').scope;

            $scope.$root.$emit("show-modal", {
                heading: message || "There was an error saving your subtitles. You'll need to copy and save your subtitles below, and upload them to the system later.",
                buttons: [
                    {'text': 'Close editor', 'class': 'no', 'fn': function() {
                        window.location = '/videos/' + subtitleListScope.videoID + "/";
                    }}
                ]
            });
            $scope.$root.$emit('show-modal-download');
        };

        $scope.$root.$on('approve-task', function() {
            $scope.saveAndApprove();
        });
        $scope.$root.$on('send-back-task', function() {
            $scope.saveAndSendBack();
        });
        $scope.$root.$on('subtitles-fetched', function() {
            $scope.setCloseStates();
        });
        $scope.$root.$on('work-done', function() {
            $scope.canSave = '';
            $scope.$digest();
        });

    };
    var SubtitleListController = function($window, $scope, $timeout, SubtitleStorage) {
        /**
         * Responsible for everything that touches subtitles as a group,
         * souch as populating the list with actual data, removing subs,
         * adding subs.
         * @param $scope
         * @param SubtitleStorage
         * @constructor
         */

        $scope.allowsSyncing = $window.editorData.allowsSyncing;
        $scope.addSubtitle = function(index, attrs, content, focus) {

            // Add the subtitle directly to the DFXP instance.
            var newSubtitle = $scope.parser.addSubtitle(index, attrs, content);

            // If we want to focus the subtitle after it's been added, set
            // the index here.
            if (focus) {
                $scope.focusIndex = $scope.parser.getSubtitleIndex(newSubtitle, $scope.parser.getSubtitles().get());

            // Otherwise, reset the focusIndex.
            } else {
                $scope.focusIndex = null;
            }

            // Update the subtitles on the list scope.
            $scope.updateParserSubtitles();
        };
        $scope.getSubtitleListHeight = function() {
            return $(window).height() - $scope.$root.subtitlesHeight;
        };
        $scope.getSubtitles = function(languageCode, versionNumber) {

            // If this version has no default source translation language
            // it will be empty, in which case we want to wait for user
            // interaction to request a reference subtitle set.
            if (!languageCode || !versionNumber) {
                $scope.status = 'idle';
                return;
            }

            $scope.status = 'loading';

            var that = this;
            SubtitleStorage.getSubtitles(languageCode, versionNumber, function(subtitleData) {
                $scope.onSubtitlesFetched.call(that, subtitleData);
            });

        };
        $scope.onSubtitlesFetched = function (subtitleData) {

            // Save the title and description to this scope.
            $scope.videoTitle = subtitleData.title;
            $scope.videoDescription = subtitleData.description;

            if ( subtitleData.visibility == 'Public' || $scope.isEditable){
                // Set up a new parser instance with this DFXP XML set.
               this.dfxpWrapper = new root.AmaraDFXPParser();
               this.dfxpWrapper.init(subtitleData.subtitlesXML);

                // Reference the parser and instance on the scope so we can access it via
                // the templates.
                $scope.parser = this.dfxpWrapper;
                $scope.subtitles = $scope.parser.getSubtitles().get();

                $scope.status = 'ready';
            }


            // When we have subtitles for an editable set, broadcast it.
            $timeout(function() {
                if ($scope.isEditable) {
                    $scope.$root.$broadcast('subtitles-fetched');
                }
            });
        };
        $scope.removeSubtitle = function(subtitle) {
            $scope.parser.removeSubtitle(subtitle);
            $scope.updateParserSubtitles();
        };
        $scope.saveSubtitles = function() {
            $scope.status = 'saving';
            return SubtitleStorage.saveSubtitles($scope.videoID,
                                          $scope.languageCode,
                                          $scope.parser.xmlToString(true, true),
                                          $scope.videoTitle,
                                          $scope.videoDescription);
        };
        $scope.setLanguageCode = function(languageCode) {
            $scope.languageCode = languageCode;

            SubtitleStorage.getLanguageMap(function(languageMap) {
                $scope.languageName = languageMap[$scope.languageCode];
            });
        };
        $scope.setVideoID = function(videoID) {
            $scope.videoID = videoID;
        };
        $scope.updateParserSubtitles = function() {
            $scope.subtitles = $scope.parser.getSubtitles().get();
        };

        $scope.$watch($scope.getSubtitleListHeight, function(newHeight) {
            $($('div.subtitles').height(newHeight));
        });

        window.onresize = function() {
            $scope.$digest();
        };
    };
    var SubtitleListHelperController = function($scope) {

        $scope.isEditingAny = false;

        $scope.$root.$on('editing', function() {
            $scope.isEditingAny = true;
            $scope.$digest();
        });
        $scope.$root.$on('editing-done', function() {
            $scope.isEditingAny = false;
            $scope.$digest();
        });
    };
    var SubtitleListItemController = function($scope) {
        /**
         * Responsible for actions on one subtitle: editing, selecting.
         * @param $scope
         * @constructor
         */

        var initialText;

        $scope.empty = false;
        $scope.isEditing = false;
        $scope.showStartTime = $scope.parser.startTime($scope.subtitle) !== -1;
        $scope.contentAsHTML = $scope.parser.contentRendered($scope.subtitle);
        // convert to markdown at init time, then never again to avoid
        // double scaping
        initialText = $scope.parser.dfxpToMarkdown($scope.subtitle, true);

        $scope.finishEditingMode = function(newValue) {

            $scope.isEditing = false;

            // Tell the root scope that we're no longer editing, now.
            $scope.$root.$emit('editing-done');


            if (newValue !== initialText) {
                // we can store markdown content directly on the node
                // then on serialization it will get converted correctly
                // to dfxp
                $scope.parser.content($scope.subtitle, newValue);
                $scope.contentAsHTML = $scope.parser.contentRendered($scope.subtitle);
                initialText = $scope.parser.content($scope.subtitle);
                $scope.$root.$emit('work-done');
            }
        };
        $scope.getSubtitleIndex = function() {
            return $scope.parser.getSubtitleIndex($scope.subtitle, $scope.subtitles);
        };
        $scope.startEditingMode = function() {


            $scope.isEditing = true;

            // Tell the root scope that we're editing, now.
            $scope.$root.$emit('editing');

            return initialText;
        };

        $scope.$root.$on('subtitles-fetched', function() {
            // When subtitles are first retrieved, we need to set up the amarasubtitle
            // on the video and bind to this scope.
            //
            // This will happen on the video controller. Just throw an event stating that
            // we're ready.

            // Only emit the event on editable subtitles. We don't want to initialize
            // Popcorn subtitles for the non-editable set.
            if ($scope.$parent.isEditable) {
                $scope.$root.$emit('subtitle-ready', $scope);
            }
        });
    };

    root.LanguageSelectorController = LanguageSelectorController;
    root.SaveSessionController = SaveSessionController;
    root.SubtitleListController = SubtitleListController;
    root.SubtitleListHelperController = SubtitleListHelperController;
    root.SubtitleListItemController = SubtitleListItemController;

}).call(this);
