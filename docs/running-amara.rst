===========================
Running Amara
===========================

To run the development version:

1. Git clone the repository::

       git clone git://github.com/pculture/unisubs.git unisubs

   Now the entire project will be in the ``unisubs/`` directory.

2. Install `virtualenv <http://pypi.python.org/pypi/virtualenv>`_.

3. (optional) download and download the `virtualenv wrapper
   <http://www.doughellmann.com/projects/virtualenvwrapper/>`_ bash functions

4. Create a virtual environment and activate it. Here is how to do it 
   *without* the virtualenv wrapper. Run these commands from the parent 
   of the unisubs directory created in #1::

   $ virtualenv unisubs-env
   $ source unisubs-env/bin/activate

   If you're using the virtualenv wrapper (run from any directory)::

   $ mkvirtualenv unisubs
   $ workon unisubs

5. Run::

    $ easy_install -U setuptools
    $ easy_install pip
    $ cd deploy
    # this is the unisubs directory you cloned from git, not the parent you created the virtualenv in.
    $ pip install -r requirements.txt

   .. note:: You'll need mercurial installed to make this last command work.

   .. note:: If you do not have the MySQL bindings installed (MySQLdb) and
        wish to keep it that way, unisubs runs just fine on sqlite, just comment
        out the line ``MySQL_python>=1.2.2`` on ``deploy/requirements.txt`` before
        running this command.


6. Check out google closure into directory of your choice: ::

    $ svn checkout http://closure-library.googlecode.com/svn/trunk/ <directory>.

   Then symlink ``media/js/closure-library`` to the checkout location. From the
   unisubs directory in step 1::

   $ cd media/js
   $ ln -s <google closure checkout directory> closure-library

7. Add ``unisubs.example.com`` to your hosts file, pointing at ``127.0.0.1``.
   This is necessary for Twitter oauth to work correctly.

8. From the unisubs directory created in step 1, first create the 
   database with::

       python manage.py syncdb

   Then update the database with::

       python manage.py migrate

   SQLLite warnings are okay. Then run the site with::

       ./dev-runserver.sh

   You can access the site at http://unisubs.example.com:8000.

9. (optional) If you want to run video searches  / watch page locally, you need to set up solr:

   A. Download solr and unzip to ``../buildout/parts/solr`` (relative to this directory).
   B. Run ``./manage.py run_solr`` in one terminal that is dedicated to running the solr process.
   C. Run ``./manage.py rebuild_index`` to update the index.
   D. That should be it but, in case you're interested, here's a
      list of `haystack commands <http://docs.haystacksearch.org/dev/management_commands.html>`_.

   .. seealso:: If you want to install SOLR as a daemon on your Mac, please see `this
        guide <https://github.com/8planes/unisubs/wiki/Running-SOLR-as-a-daemon-on-Mac>`_.

10. Celeryd:

  Many things in unisubs run asynchronously, so you will need to run celeryd.
  If you would rather run celery with another backend of your choice, it's fine
  just adapt these instructions:

  A. Download and install  `redis <http://redis.io/>`_  
  B. Start redis
  C. Make sure you have on your local_settings ::

      BROKER_BACKEND = 'redis'
      BROKER_HOST = "localhost"
      BROKER_VHOST = "/"
 
  D. Cd in to the unisubs directory and run ::

      python manage.py celeryd --loglevel=INFO --settings=dev_settings

  Or you can just add to your local settings ::
    
    CELERY_ALWAYS_EAGER = True

Using vagrant
-------------

Amara uses `Vagrant <http://vagrantup.com/>`_ to make it easy to
get started.  If you've never used Vagrant before we highly recommend going
through its `quick start guide
<http://vagrantup.com/docs/getting-started/index.html>`_ to learn how it works.

To run the development version:

1. Clone the git repository ::

        git clone git://github.com/pculture/unisubs.git unisubs

   Now the entire project will be in the ``unisubs/`` directory.

2. Install VirtualBox and vagrant if you don't have them yet. Then type::

        vagrant up

   This is going to create a vm and provision it. It should take 10-15 minutes.
   Remember what mom said: a watched pot never boils.

3. Switch over to your vagrant vm with::

        vagrant ssh

   By default our ``~/.bashrc`` file will automatically move you to the shared
   folder and activate the virtualenv.

   Now run following command::

        ./bootstrap-vagrant.sh

   It's safe to run ``bootstrap-vagrant.sh`` multiple times if something goes
   wrong (like PyPi goes down).

4. Add ``unisubs.example.com`` to your hosts file, pointing at ``127.0.0.1``.  This
   is necessary for Twitter and Facebook oauth to work correctly.

5. In your vagrant vm (the one you switched to in step 3), run the site with::

        ./dev-runserver.sh

   You can access the site at http://unisubs.example.com:8000.

6. (Optional) :doc:`Set up Sentry </sentry>`.
