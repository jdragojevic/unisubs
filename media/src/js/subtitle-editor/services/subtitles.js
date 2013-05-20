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

    var API_BASE_PATH_TEAMS = '/api2/partners/teams/';
    var API_BASE_PATH_VIDEOS = '/api2/partners/videos/';

    var root = this;
    var module = angular.module('amara.SubtitleEditor.services', []);

    var getSubtitleFetchAPIUrl = function(videoId, languageCode, versionNumber) {
        var url = API_BASE_PATH_VIDEOS + videoId +
            '/languages/' + languageCode + '/subtitles/?format=dfxp';

        if (versionNumber) {
            url = url + '&version=' + versionNumber;
        }
        return url;
    };
    var getSubtitleSaveAPIUrl = function(videoId, languageCode) {
        var url = API_BASE_PATH_VIDEOS + videoId +
            '/languages/' + languageCode + '/subtitles/';
        return url;
    };
    var getTaskSaveAPIUrl = function(teamSlug, taskID) {
        return API_BASE_PATH_TEAMS + teamSlug + '/tasks/' + taskID + '/';
    };
    var getVideoLangAPIUrl = function(videoId) {
        return API_BASE_PATH_VIDEOS + videoId + '/languages/';
    };

    module.factory('SubtitleStorage', function($http) {

        var cachedData = window.editorData;
        var authHeaders = cachedData.authHeaders;

        return {
            approveTask: function(response, notes) {

                var url = getTaskSaveAPIUrl(cachedData.team_slug, cachedData.task_id);

                var promise = $http({
                    method: 'PUT',
                    url: url,
                    headers: authHeaders,
                    data:  {
                        complete: true,
                        body: notes,
                        version_number: response.data.version_number
                    }
                });

                return promise;

            },
            getCachedData: function() {
                return cachedData;
            },
            getLanguages: function(callback) {

                // If there are no languages in our cached data, ask the API.
                if (cachedData.languages && cachedData.languages.length === 0) {

                    var url = getVideoLangAPIUrl(cachedData.video.id);

                    $http.get(url).success(function(response) {
                        cachedData.languages = response.objects;
                        callback(response.objects);
                    });

                // If we have cached languages, just call the callback.
                } else {
                    callback(cachedData.languages);
                }
            },
            getLanguageMap: function(callback) {

                // If the language map doesn't exist in our cached data, ask the API.
                if (!cachedData.languageMap) {
                    $http.get('/api2/partners/languages/').success(function(response) {
                        cachedData.languageMap = response.languages;
                        callback(cachedData.languageMap);
                    });

                // If we have a cached language map, just call the callback.
                } else {
                    callback(cachedData.languageMap);
                }

            },
            getSubtitles: function(languageCode, versionNumber, callback){

                // You must supply a language code in order to get subtitles.
                if (!languageCode) {
                    throw Error('You must supply a language code to getSubtitles().');
                }

                var subtitleData;

                // Loop through all of our cached languages to find the correct subtitle version.
                for (var i=0; i < cachedData.languages.length; i++){

                    var language = cachedData.languages[i];

                    // Once we find the language we're looking for, find the version.
                    if (language.code === languageCode){

                        for (var j = 0; j < language.versions.length; j++){

                            // We've found the version.
                            if (language.versions[j].version_no === parseInt(versionNumber, 10)){

                                subtitleData = language.versions[j];
                                if (subtitleData.subtitlesXML) {
                                    break;
                                }

                            }
                        }

                        break;
                    }
                }

                // If we found subtitles, call the callback with them.
                if (subtitleData.subtitlesXML !== undefined){
                   callback(subtitleData);

                // Otherwise, ask the API for this version.
                } else {

                    var url = getSubtitleFetchAPIUrl(cachedData.video.id, languageCode, versionNumber);

                    $http.get(url).success(function(response) {

                        // Cache these subtitles on the cached data object.
                        subtitleData.subtitlesXML = response;
                        callback(subtitleData);

                    });
                }
            },
            getPrimaryVideoURL: function() {
                return cachedData.video.primaryVideoURL;
            },
            getVideoURLs: function() {
                return cachedData.video.videoURLs;
            },
            sendBackTask: function(response, notes) {

                var url = getTaskSaveAPIUrl(cachedData.team_slug, cachedData.task_id);

                var promise = $http({
                    method: 'PUT',
                    url: url,
                    headers: authHeaders,
                    data:  {
                        complete: true,
                        notes: notes,
                        send_back: true,
                        version_number: response.data.version_number
                    }
                });

                return promise;

            },
            saveSubtitles: function(videoID, languageCode, dfxpString, title, description){

                var url = getSubtitleSaveAPIUrl(videoID, languageCode);

                var promise = $http({
                    method: 'POST',
                    url: url,
                    headers: authHeaders,
                    data:  {
                        video: videoID,
                        language: languageCode,
                        subtitles: dfxpString,
                        sub_format: 'dfxp',
                        title: title,
                        description: description
                    }
                });

                return promise;
            }
        };
    });
    module.factory('SubtitleListFinder', function($http) {
        /**
         * A sevice to cache and retrieve instances of the subtitle-list directive.
         *
         * TODO: We don't really need this service. We can simply use angular.element to retrieve
         * subtitle-list instances and access the scope / controller from there.
         */
        var registry = {};

        return {
            register: function(name, elm, controller, scope) {
                /**
                 * @param name  String to identify this subtitle list by, this is taken from the
                 * value of the 'subtitle-list' attribute on the SubtitleList directive.
                 * @param elm The wrapped element for the subtitle list.
                 * @param controller Controller for the the subtitle list
                 * @param scope The scope for the list
                 */

                // Registering the same name more than once will throw an error.
                if (registry[name]){
                   throw new Error('Already registred a subtitle list component with name"' + name + '".') ;
                }

                registry[name] = {
                    name: name,
                    elm: elm,
                    controller: controller,
                    scope: scope
                };

                return this;
            },
            get: function(name) {
                return registry[name];
            }
        };
    });

    module.factory('OldEditorConfig', function($window) {
        /**
         * A sevice to cache and retrieve instances of the subtitle-list directive.
         *
         * TODO: We don't really need this service. We can simply use angular.element to retrieve
         * subtitle-list instances and access the scope / controller from there.
         */
        var oldEditorURL = window.editorData.oldEditorURL;

        return {
            get: function() {
                return oldEditorURL;
            }
        };
    });}).call(this);
