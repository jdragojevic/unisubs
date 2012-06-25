(function(window, document, undefined) {

    // When the embedder is compiled, dependencies will be loaded directly before this
    // function. Set dependencies to use no-conflict mode to avoid destroying any
    // original objects.
    var __ = _.noConflict();
    var _$ = Zepto;
    var _Backbone = Backbone.noConflict();
    var _Popcorn = Popcorn.noConflict();

    // _amara may exist with a queue of actions that need to be processed after the
    // embedder has finally loaded. Store the queue in toPush for processing in init().
    var toPush = window._amara || [];

    var Amara = function(Amara) {

        // For reference in inner functions.
        var that = this;

        // Private methods that are called via the push() method.
        var actions = {

            // The core function for constructing an entire video with Amara subtitles from
            // just a video URL. This includes DOM creation for the video, etc.
            embedVideo: function(options) {

                // Make sure we have a URL to work with.
                if (__.has(options, 'url') && __.has(options, 'div')) {
                    // Init the Popcorn video.
                    var pop = Popcorn.smart(options.div, options.url);
                }
            }

        };

        // push() handles all action calls before and after the embedder is loaded.
        // Aside from init(), this is the only function that may be called from the
        // parent document.
        //
        // Must send push() an object with only two items:
        //     * Action  (string)
        //     * Options (object)
        //
        // Note: we don't use traditional function arguments because before the
        // embedder is loaded, _amara is just an array with a normal push() method.
        this.push = function(args) {
            
            // No arguments? Don't do anything.
            if (!arguments.length) { return; }

            // Must send push() an object with only two items.
            if (__.size(arguments[0]) === 2) {

                var action = args[0];
                var options = args[1];

                // If a method exists for this action, call it with the options.
                if (actions[action]) {
                    actions[action](options);
                }
            }

        };

        // init() gets called as soon as the embedder has finished loading.
        // Simply processes the existing _amara queue if we have one.
        this.init = function() {

            // If we have a queue from before the embedder loaded, process the actions.
            if (toPush) {
                for (var i = 0; i < toPush.length; i++) {
                    that.push(toPush[i]);
                }
                toPush = [];
            }

            // Check to see if we have any amara-embed's to initilize.
            var amaraEmbeds = _$('div.amara-embed');

            if (amaraEmbeds.length) {
                amaraEmbeds.each(function() {

                    // This is a patch until Popcorn.js supports passing a DOM elem to
                    // its smart() method. See: http://bit.ly/L0Lb7t
                    var id = 'amara-embed-' + Math.floor(Math.random() * 100000000);
                    var $div = $(this);
                    $div.attr('id', id);

                    // Call embedVideo with this div and URL.
                    that.push(['embedVideo', {'div': id, 'url': $div.data('url') }]);
                });
            }

        };

    };

    window._amara = new Amara();
    window._amara.init();

}(window, document));
