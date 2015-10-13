"""States for managing CKAN extensions."""

import os

import yaml


__virtualname__ = 'ckanext'


def __virtual__():
    return __virtualname__


def _ckan():
    # XXX duplicate the whole map.jinja logic
    stream = __salt__['cp.get_file_str']('salt://ckan/defaults.yaml')
    default_settings = yaml.load(stream)
    os_family_map = __salt__['grains.filter_by'](
        {'Debian': {},
         'RedHat': {}},
        grain="os_family",
        merge=__salt__['pillar.get']('ckan:lookup')
    )
    default_settings['ckan'].update(os_family_map)
    ckan = __salt__['pillar.get'](
        'ckan',
        default=default_settings['ckan'],
        merge=True
    )
    ckan['venv_path'] = ckan['ckan_home'] + '/venv'
    return ckan


def installed(name, repourl=None, rev=None, requirements_file=None):
    """Install the `name` CKAN extension.
    """
    ckan = _ckan()
    if rev is None:
        rev = ckan['extensions'].get(name, {}).get('rev', None)
        if rev is None:
            rev = 'master'
    if requirements_file is None:
        requirements_file = 'requirements.txt'
    ret = {
        'changes': {},
        'comment': '',
        'name': name,
        'result': None,
    }
    fullname = 'ckanext-' + name
    if repourl is None:
        repourl = ckan['extensions'].get(name, {}).get('repourl', None)
        if repourl is None:
            repourl = 'https://github.com/ckan/' + fullname
    srcdir = os.path.join(ckan['src_dir'], fullname)
    user, group = ckan['ckan_user'], ckan['ckan_group']
    bin_env = ckan['venv_path']
    if __opts__['test']:
        ret['comment'] = (
            'would install {0} CKAN extention into {1} virtualenv'.format(
            name, bin_env))
        ret['result'] = None
        return ret

    def log(change_ctx, msg):
        ret['changes'][change_ctx] = msg

    def failed(change_ctx, res):
        msg = 'failed'
        if isinstance(res, dict):
            msg = '\n'.join(
                [msg + ':', res.get('stderr', ''), res.get('stdout', '')])
        else:
            msg = ': '.join([msg, str(res)])
        log(change_ctx, msg)
        ret['result'] = False
        return ret

    if os.path.isdir(srcdir):
        res = __salt__['git.fetch'](cwd=srcdir, opts='origin ' + rev)
        if isinstance(res, dict) and res.get('retcode'):
            return failed('sources update', res)
        log('sources update', res)
    else:
        ret['changes']['sources clone'] = __salt__['git.clone'](
            cwd=srcdir, repository=repourl)
    ret['changes']['sources checkout'] = __salt__['git.checkout'](
        cwd=srcdir, rev=rev)
    res = __salt__['file.chown'](srcdir, user=user, group=group)
    if res is not None:
        return failed('sources ownership', res)
    res = __salt__['pip.install'](editable=srcdir, user=user, bin_env=bin_env)
    if res['retcode']:
        return failed('pip install', res)
    log('pip install', 'pip installed {0}'.format(fullname))
    requirements_file = os.path.join(srcdir, requirements_file)
    if os.path.exists(requirements_file):
        res = __salt__['pip.install'](
            requirements=requirements_file, user=user, bin_env=bin_env)
        if res['retcode']:
            return failed('pip install dependencies', res)
        log('pip install dependencies',
            'install {0} dependencies from {1}'.format(
                fullname, requirements_file))
    ret['comment'] = ' successfully installed CKAN extension {0}'.format(name)
    ret['result'] = True
    return ret
