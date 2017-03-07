
ostrich - An OpenStack-Ansible install runner
#############################################

The goal of ostrich is to make running OpenStack-Ansible (OSA) easier and more
fool-proof. Specifically it configures OSA for use with Ironic (i.e. bare
metal provisioning)

Installation
============

Linux
-----

Installing pre-requisites under an Ubuntu or similar operating system is easy:

.. code-block:: bash

    $ apt-get install python-dev ack-grep build-essential screen
    $ wget https://bootstrap.pypa.io/get-pip.py
    $ python ./get-pip.py
    $ pip install -r requirements.txt

Grab the latest version of ostrich:

.. code-block:: bash

    $ git clone https://github.com/mikalstill/ostrich.git

Running ostrich
===============

Ostrich must be run in a screen or tmux session, because it's going to take
a while, and you might like to go grab a cup of tea while it's doing its
thing.

.. code-block:: bash

    $ screen
    $ cd ostrich
    $ ./ostrich
