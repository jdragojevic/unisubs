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
var SubtitleListItemController = SubtitleListItemController || null;
var LOCK_EXPIRATION = 25;
var USER_IDLE_MINUTES = 5;

(function($) {

    var directives = angular.module('amara.SubtitleEditor.directives', []);

    function setCaretPosition(elem, caretPos) {
        /** Move the caret to the specified position.
         * This will work, except for text areas with user inserted line breaks
         */
        if (elem != null) {
            if (elem.createTextRange) {
                var range = elem.createTextRange();
                range.move('character', caretPos);
                range.select();
            }
            else {
                if (elem.selectionStart) {
                    elem.focus();
                    elem.setSelectionRange(caretPos, caretPos);
                }
            }
        }
    }
    directives.directive('saveSessionButton', function(SubtitleStorage) {
        return {
            link: function link(scope, elm, attrs) {
                scope.canSave = '';
            }
        };
    });
    directives.directive('subtitleEditor', function(SubtitleStorage, LockService, $timeout) {

        var minutesIdle = 0;
        var secondsUntilClosing = 120;
        var videoId, languageCode, selectedScope, regainLockTimer;

        function startUserIdleTimer() {
            var userIdleTimeout = function() {

                minutesIdle++;

                if (minutesIdle >= USER_IDLE_MINUTES) {
                    showIdleModal();
                    $timeout.cancel(regainLockTimer);
                } else {
                    $timeout(userIdleTimeout, 60 * 1000);
                }
            };

            $timeout(userIdleTimeout, 60 * 1000);
        }
        function startRegainLockTimer() {
            var regainLockTimeout = function() {
                LockService.regainLock(videoId, languageCode);
                regainLockTimer = $timeout(regainLockTimeout, 15 * 1000);
            };

            regainLockTimer = $timeout(regainLockTimeout, 15 * 1000);

        }
        function showIdleModal() {

            var heading = "Warning: you've been idle for more than " + USER_IDLE_MINUTES + " minutes. " +
                "To ensure no work is lost we will close your session in ";

            var closeSessionTimeout;

            var closeSession = function() {

                secondsUntilClosing--;

                if (secondsUntilClosing <= 0) {

                    LockService.releaseLock(videoId, languageCode);

                    selectedScope.$root.$emit("show-modal", {
                        heading: 'Your session has ended. You can try to resume, close the editor, or download your subtitles',
                        buttons: [
                            {'text': 'Try to resume work', 'class': 'yes', 'fn': function() {
                                // TODO: Remove this duplication from below.
                                if (closeSessionTimeout) {
                                    $timeout.cancel(closeSessionTimeout);
                                }

                                var promise = LockService.regainLock(videoId, languageCode);

                                promise.then(function onSuccess(response) {
                                    if (response.data.ok) {
                                        minutesIdle = 0;
                                        selectedScope.$root.$broadcast('hide-modal');
                                        startRegainLockTimer();
                                        startUserIdleTimer();
                                    } else {
                                        window.alert("Sorry, could not restart your session.");
                                        window.location = '/videos/' + videoId + "/";
                                    }
                                }, function onError() {
                                    window.alert("Sorry, could not restart your session.");
                                    window.location = '/videos/' + videoId + "/";
                                });
                            }},
                            {'text': 'Download subtitles', 'class': 'no', 'fn': function() {
                                selectedScope.$root.$emit('show-modal-download');
                            }},
                            {'text': 'Close editor', 'class': 'no', 'fn': function() {
                                window.location = '/videos/' + videoId + "/";
                            }}
                        ]
                    });

                } else {

                    selectedScope.$root.$emit('change-modal-heading', heading + secondsUntilClosing + " seconds.");
                    closeSessionTimeout = $timeout(closeSession, 1000);

                }
            };

            selectedScope.$root.$emit("show-modal", {
                heading: heading + secondsUntilClosing + " seconds.",
                buttons: [
                    {'text': 'Try to resume work', 'class': 'yes', 'fn': function() {
                        if (closeSessionTimeout) {
                            $timeout.cancel(closeSessionTimeout);
                        }

                        var promise = LockService.regainLock(videoId, languageCode);

                        promise.then(function onSuccess(response) {
                            if (response.data.ok) {
                                minutesIdle = 0;
                                selectedScope.$root.$broadcast('hide-modal');
                                startRegainLockTimer();
                                startUserIdleTimer();
                            } else {
                                window.alert("Sorry, could not restart your session.");
                                window.location = '/videos/' + videoId + "/";
                            }
                        }, function onError() {
                            window.alert("Sorry, could not restart your session.");
                            window.location = '/videos/' + videoId + "/";
                        });
                    }}
                ]
            });

            closeSessionTimeout = $timeout(closeSession, 1000);

        }

        return {
            compile: function compile(elm, attrs, transclude) {
                return {
                    post: function post(scope, elm, attrs) {

                        scope.scrollingSynced = true;
                        scope.timelineShown = false;
                        scope.subtitlesHeight = 366;

                        scope.$watch('timelineShown', function() {
                            if (scope.timelineShown) {
                                scope.subtitlesHeight = 431;
                            } else {
                                scope.subtitlesHeight = 366;
                            }
                        });

                        $(elm).on('keydown', function(e) {

                            // Reset the lock timer.
                            minutesIdle = 0;

                            var video = angular.element($('#video').get(0)).scope();

                            // Space with shift, toggle play / pause.
                            if (e.keyCode === 32 && e.shiftKey) {
                                e.preventDefault();
                                video.togglePlay();
                            }

                        });
                        $(elm).on('mousemove', function() {

                            // Reset the lock timer.
                            minutesIdle = 0;

                        });

                        videoId = attrs.videoId;
                        languageCode = attrs.languageCode;
                        selectedScope = scope;

                        startUserIdleTimer();
                        startRegainLockTimer();
                    }
                };
            }
        };
    });
    directives.directive('subtitleList', function(SubtitleStorage, SubtitleListFinder, $timeout) {

        var activeTextArea,
            rootEl,
            selectedController,
            selectedScope,
            value;

        function onSubtitleItemSelected(elm, event) {
            /**
             * Receives the li.subtitle-list-item to be edited.
             * Will put any previously edited ones in display mode,
             * mark this one as being edited, creating the textarea for
             * editing.
             *
             * If this is created by user interaction (clicking on the sub)
             * we want to keep the caret focus on the place he's clicked. Else
             * if this initiated by any other action (e.g. advancing the video
             * playhead / tabbing through subs, we can ignore this).
             */

            elm = $(elm).hasClass('subtitle-list-item') ?
                      elm : $(elm).parents('.subtitle-list-item');

            var controller = angular.element(elm).controller();
            var scope = angular.element(elm).scope();
            // make sure we're actually changing the editing sub
            if (scope == selectedScope){
                return;
            }

            if (controller instanceof SubtitleListItemController) {
                if (selectedScope) {
                    selectedScope.finishEditingMode(activeTextArea.val());
                    selectedScope.$digest();
                }
                activeTextArea = $('textarea', elm);
                selectedScope = scope;

                var textValue = selectedScope.startEditingMode()
                activeTextArea.val(textValue);
                var caretPos = (event && document.getSelection().extentOffset) ||
                                textValue.length;
                selectedScope.$digest();

                activeTextArea.focus();
                activeTextArea.autosize();

                selectedScope.$root.$broadcast('subtitle-selected', selectedScope);
                setCaretPosition($(activeTextArea).get(0), caretPos);
            }
        }
        function onSubtitleTextKeyDown(e) {
            /*
             * When a key is down, check to see if we need to do something:
             *
             * Enter / return: finish editing current sub and focus on the next one.
             * Shift + Enter / return: enter a newline in the current subtitle.
             * Tab: send the event to the video controller for playback control.
             * Shift + Tab: send the event to the video controller for playback control.
             * Any other key: do nothing.
             */

            var nextSubtitle;

            var $currentSubtitle = $(e.currentTarget).parent();

            // Tab without shift.
            if (e.keyCode === 9 && !e.shiftKey) {

                // Prevent an additional newline from being added to the next subtitle.
                e.preventDefault();

                // If canAddAndRemove is true and this is the last subtitle in the set,
                // save the current subtitle and create a new subtitle at the end.
                if (selectedScope.canAddAndRemove) {
                    if ($currentSubtitle.next().length === 0) {

                        // Save the current subtitle.
                        selectedScope.finishEditingMode(activeTextArea.val());

                        // Passing true as the last argument indicates that we want
                        // to select this subtitle after it is created.
                        selectedScope.addSubtitle(null, {}, '', true);

                        // Apply the current scope.
                        selectedScope.$apply();

                    }
                }

                // Set the next subtitle to be the one after this.
                nextSubtitle = $currentSubtitle.next().get(0);

            }

            // Tab with shift.
            if (e.keyCode === 9 && e.shiftKey) {

                // Keep the cursor in the current subtitle.
                e.preventDefault();

                // Set the next subtitle to be the one before this.
                nextSubtitle = $currentSubtitle.prev().get(0);

            }

            // Space with shift.
            if (e.keyCode === 32 && e.shiftKey) {

                // We're letting this event bubble up to the subtitleEditor directive
                // where it will trigger the appropriate video method.

                // Keep the cursor in the current subtitle.
                e.preventDefault();

            }

            // enter without shift
            if (e.keyCode === 13 && !e.shiftKey) {
                e.preventDefault();
                if (selectedScope && selectedScope.isEditing) {
                    selectedScope.finishEditingMode(activeTextArea.val());
                    selectedScope.$digest();
                }

            }

            if (nextSubtitle) {

                // Select the next element.
                onSubtitleItemSelected(nextSubtitle);

            }
        }
        function onSubtitleTextKeyUp(e) {

            var newText = activeTextArea.val();

            // Save the content to the DFXP wrapper.
            selectedScope.parser.content(selectedScope.subtitle, newText);

            // Cache the value for a negligible performance boost.
            value = activeTextArea.val();

            selectedScope.empty = value === '';
            selectedScope.characterCount = value.length;

            selectedScope.$root.$emit('subtitle-key-up', {
                parser: selectedScope.parser,
                subtitles: $(selectedScope.subtitles),
                subtitle: selectedScope,
                value: value
            });

            selectedScope.$digest();

        }

        return {
            compile: function compile(elm, attrs, transclude) {
                rootEl = elm;
                return {
                    post: function post(scope, elm, attrs) {

                        // set these *before* calling get subtitle since if
                        // the subs are bootstrapped it will return right away
                        scope.isEditable = attrs.editable === 'true';
                        scope.canAddAndRemove = attrs.canAddAndRemove === 'true';
                        scope.getSubtitles(attrs.languageCode, attrs.versionNumber);


                        // Cache the jQuery selection of the element.
                        var $elm = $(elm);

                        // Handle scroll.
                        $elm.parent().scroll(function() {

                            // If scroll sync is locked.
                            if (scope.$root.scrollingSynced) {
                                var newScrollTop = $elm.parent().scrollTop();

                                $('div.subtitles').each(function() {

                                    var $set = $(this);

                                    if ($set.scrollTop() !== newScrollTop) {
                                        $set.scrollTop(newScrollTop);
                                    }

                                });
                            }
                        });

                        if (scope.isEditable) {
                            $elm.click(function(e) {
                                onSubtitleItemSelected(e.srcElement || e.target, e);
                            });
                            $elm.on('keydown', 'textarea', onSubtitleTextKeyDown);
                            $elm.on('keyup', 'textarea', onSubtitleTextKeyUp);

                            // In order to catch an <esc> key sequence, we need to catch
                            // the keycode on the document, not the list. Also, keyup must
                            // be used instead of keydown.
                            $(document).on('keyup', function(e) {
                                if (e.keyCode === 27) {
                                    if (selectedScope) {
                                        selectedScope.finishEditingMode(activeTextArea.val());
                                        selectedScope.$digest();
                                    }
                                }
                            });

                            // Create a custom event handler to select a subtitle.
                            //
                            // See the subtitleListItem directive below. This gets called
                            // if a subtitleListItem is created and its index matches the
                            // focus index that is set when adding the new subtitle from the
                            // controller.
                            $elm.on('selectFocusedSubtitle', function() {

                                var $subtitle = $('li', elm).eq(scope.focusIndex);

                                // Select the subtitle.
                                //
                                // We have to timeout here, otherwise we'll try to select
                                // the new subtitle before it's been added to DOM.
                                $timeout(function() {
                                    onSubtitleItemSelected($subtitle.get(0));
                                });

                            });
                        }
                        scope.setVideoID(attrs.videoId);
                        scope.setLanguageCode(attrs.languageCode);
                        SubtitleListFinder.register(attrs.subtitleList, elm,
                            angular.element(elm).controller(), scope);
                    }
                };
            }
        };
    });
    directives.directive('subtitleListItem', function() {
        return {
            compile: function compile(elm, attrs, transclude) {
                return {
                    post: function post(scope, elm, attrs) {

                        // If we need to focus this subtitle.
                        if (scope.getSubtitleIndex() === scope.$parent.focusIndex) {

                            // Trigger the custom event selectFocusedSubtitle on the UL,
                            // which was bound in the subtitleList directive above.
                            $(elm).parent().trigger('selectFocusedSubtitle');

                        }

                    }
                };
            }
        };
    });
    directives.directive('timeline', function() {
        return {
            compile: function compile(elem, attrs, transclude) {
                return {
                    post: function post(scope, elem, attrs) {

                        var $elem = $(elem);
                        var $timingContainer = $('div.timing-container', elem);
                        var $body = $('body');

                        var renderTimelineSubtitles = function(pop) {

                        };
                        var renderTimelineSeconds = function(pop) {

                            var currentTime = pop.currentTime();
                            var duration = pop.duration();
                            var durationRoundedUp = Math.ceil(duration * 1) / 1;

                            var endTime = currentTime + 15;
                            endTime = endTime > durationRoundedUp ? durationRoundedUp : endTime;

                            var startTime = currentTime - 15;
                            startTime = startTime < 0 ? 0 : startTime;

                            for (var i = startTime; i < endTime; i++) {

                                // Create a new div for this second and append to the timing container.
                                $timingContainer.append($('<div class="second"><span>' + i + '</span></div>'));

                            }

                            //$timingContainer.width(scope.secondsRoundedUp * 100);

                        };

                        scope.$root.$on('video-ready', function($event, pop) {
                            renderTimelineSeconds(pop);
                            renderTimelineSubtitles(pop);
                        });
                        scope.$root.$on('video-timechanged', function($event, pop) {
                            renderTimelineSeconds(pop);
                            renderTimelineSubtitles(pop);
                        });

                    }
                };
            }
        };
    });
    directives.directive('languageSelector', function(SubtitleStorage) {



        return {
            compile: function compile(elm, attrs, transclude) {
                return {
                    post: function post(scope, elm, attrs) {
                        SubtitleStorage.getLanguages(function(languages){
                            scope.setInitialDisplayLanguage(
                                languages,
                                attrs.initialLanguageCode,
                                attrs.initialVersionNumber);
                        });
                    }
                };
            }
        };
    });
})(window.AmarajQuery);
