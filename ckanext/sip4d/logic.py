# encoding: utf-8

import ckan.plugins as pt


def auth_issysadmin(context, data_dict):
    model = context['model']
    user = context['user']
    user_obj = model.User.get(user)

    if not user_obj:
        raise pt.Objectpt.ObjectNotFound('User {0} not found').format(user)

    if user_obj.sysadmin:
        return {'success': True}
    else:
        return {'success': False}


def auth_update(context, data_dict):
    model = context['model']
    source_id = data_dict['source_id']

    pkg = model.Package.get(source_id)
    if not pkg:
        raise pt.ObjectNotFound(pt._('Package source not found'))

    context['package'] = pkg
    try:
        pt.check_access('package_update', context, data_dict)
        return {'success': True}
    except pt.NotAuthorized:
        return {'success': False}

