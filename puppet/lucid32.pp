Exec {
  path => "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
}
class lucid32 {
  $projectdir = "/opt/unisubs"
  $extrasdir = "/opt/extras"
  $venv = "/opt/extras/venv"

  group { "vagrant": ensure => "present"; } ->
  user { "vagrant": ensure => "present"; } ->
  class { 'environ': } ->
  file { "${extrasdir}":
    ensure => directory,
    owner => "vagrant",
    group => "vagrant",
  }

  group { "puppet": ensure => "present"; }  ->
  class { 'aptitude': } ->
  class { 'java': } ->
  class { 'python': } ->
  python::venv { "unisubsvenv":
    require => [File["${extrasdir}"]],
    path => $venv,
    owner => "vagrant",
    group => "vagrant"; } ->
  class { 'unisubs::db':
    require => Class["aptitude"];
  } ->
  class { 'solr': 
    require => Package["curl"],
  } ->
  class { "rabbitmq::server": } ->
  class { "unisubs::rabbitmq": } ->
  class { "celeryd":
    project_dir => "$projectdir/",
    settings_module => "dev_settings",
    venv => $venv;
  }

  class { 'unisubs::closure':
    projectdir => $projectdir
  }
  class { 'nginx': }
  class { 'gettext': }

  package { "curl": ensure => "present", }
  package { "git-core": ensure => "installed", }
  package { "swig": ensure => "installed", }
  package { "vim": ensure => "installed", }
  package { "libxslt-dev": ensure => "installed", }
  package { "libxml2-dev": ensure => "installed", }

  class { "redis::server":
    version => "2.4.8",
    bind => "127.0.0.1",
    port => 6379,
  }
}

class { "lucid32": }
