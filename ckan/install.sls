{% from "ckan/map.jinja" import ckan with context %}

ckan-user:
  user.present:
    - name: {{ ckan.ckan_user }}
    - home: {{ ckan.ckan_home }}
    - createhome: True
    - system: True
    - shell: /bin/bash

ckan-venv:
  pkg.installed:
    - pkgs:
      - python-virtualenv
      - python-pip

  virtualenv.managed:
    - name: {{ ckan.venv_path }}
    - user: {{ ckan.ckan_user }}
    - require:
      - user: ckan-user

{% set ckan_src = ckan.src_dir + '/ckan' %}

ckan-src:
  git.latest:
    - rev: {{ ckan.ckan_rev }}
    - name: {{ ckan.ckan_repo }}
    - target: {{ ckan_src }}

ckan:
  pip.installed:
    - editable: {{ ckan_src }}
    - require:
      - virtualenv: ckan-venv
    - watch:
      - git: ckan-src

ckan-deps:
  pkg.installed:
    - pkgs:
      - python-dev
      - libpq-dev  # required by psycopg2.
  pip.installed:
    - requirements: {{ ckan_src }}/requirements.txt
    - user: {{ ckan.ckan_user }}
    - bin_env: {{ ckan.venv_path }}
    - require:
      - pip: ckan

{{ ckan.confdir }}:
  file.directory:
    - user: {{ ckan.ckan_user }}
    - makedirs: true
    - recurse:
      - user

{% set ckan_conffile = [ckan.confdir, ckan.conffile]|join('/') %}

make_config:
  cmd.run:
    - name: {{ ckan.venv_path }}/bin/paster make-config ckan {{ ckan.conffile }}
    - unless: test -f {{ ckan.conffile }}
    - user: {{ ckan.ckan_user }}
    - require:
      - pip: ckan
      - virtualenv: ckan-venv
      - file: {{ ckan.confdir }}

{{ ckan.confdir}}/who.ini:
  file.symlink:
    - target: {{ ckan_src }}/who.ini

ckan_environmnent:
  file.managed:
    - name: {{ ckan.confdir }}/environment.sh
    - source: salt://ckan/files/environment.sh
    - template: jinja
    - user: {{ ckan.ckan_user }}
    - mode: 0700
    - require:
      - file: {{ ckan.confdir }}

ckan_user_bashrc:
  file.append:
    - name: {{ ckan.ckan_home }}/.bashrc
    - text: source {{ ckan.confdir }}/environment.sh
