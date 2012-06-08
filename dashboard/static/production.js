(function() {
  var description;
  description = {
    "Requests per second": {
      source: "http://graphite.universalsubtitles.org/render?from=-2hours&until=now&width=600&height=400&target=production.all-hosts.requests.completed.rate-per-second&_uniq=0.1587535673752427&title=production.all-hosts.requests.completed.rate-per-second&format=json",
      TimeSeries: {
        parent: "#req-per-sec",
        title: "Requests per second",
        type: "max"
      }
    },
    "Number of videos": {
      source: "http://graphite.universalsubtitles.org/render?from=-2hours&until=now&width=600&height=400&target=production.all-hosts.gauges.videos.Video&_uniq=0.05974812782369554&title=production.all-hosts.gauges.videos.Video&format=json",
      GaugeLabel: {
        parent: "#videos",
        title: "Videos"
      }
    },
    "Number of users": {
      source: "http://graphite.universalsubtitles.org/render?from=-2hours&until=now&width=600&height=400&target=production.all-hosts.gauges.auth.CustomUser&_uniq=0.15688160923309624&title=production.all-hosts.gauges.auth.CustomUser&format=json",
      GaugeLabel: {
        parent: "#users",
        title: "Users"
      }
    },
    "Number of tasks": {
      source: "http://graphite.universalsubtitles.org/render?from=-2hours&until=now&width=600&height=400&target=production.all-hosts.gauges.teams.Task&_uniq=0.15688160923309624&title=production.all-hosts.gauges.teams.Task&format=json",
      GaugeLabel: {
        parent: "#tasks",
        title: "Tasks"
      }
    },
    "95% response time": {
      source: "http://graphite.universalsubtitles.org/render?from=-2hours&until=now&width=600&height=400&target=production.all-hosts.response-time.value.95&_uniq=0.7285419753752649&title=production.all-hosts.response-time.value.95&format=json",
      TimeSeries: {
        parent: "#resp",
        title: "95% response time"
      }
    }
  };

  

  


  var g = new Graphene;
  g.build(description);

}).call(this);
