# -*- coding: utf-8 -*-

import logging
import six
import inspect
import html
from ckan import model
from six.moves.urllib.parse import urlencode
from time import sleep
from ckan.common import g, config, request, _
import ckan.lib.helpers as h
from ckan.lib.base import render
import ckan.plugins.toolkit as tk
import ckan.logic as logic

from ckanext.sip4d import helpers as sip4d_helpers

log = logging.getLogger(__name__)


def url_with_params(url, params):
    params = _encode_params(params)
    return url + u'?' + urlencode(params)


def _encode_params(params):
    return [(k, html.escape(v).encode('utf-8') if isinstance(v, six.string_types) else str(v))
            for k, v in params]  # basestring


def datesetview():
    context = {'model': model, 'session': model.Session, 'user': tk.c.user or tk.c.author, 'return_query': True}
    try:
        strlimit = request.params.get('limit', '20')
        strpage = request.params.get('page', '1')
        if isinstance(strlimit, str) and len(strlimit) == 0:
            strlimit = 20
        if isinstance(strpage, str) and len(strpage) == 0:
            strpage = 20

        limit = int(strlimit)
        page = int(strpage)

        q = g.q = request.params.get('q', '')
        tk.c.order_by = request.params.get('sort', 'information_date desc')
        if not tk.c.order_by.endswith('asc') and not tk.c.order_by.endswith('desc'):
            tk.c.order_by = 'information_date desc'

        # startdatetime-enddatetime
        start_date = request.params.get('ext_startdate', None)
        end_date = request.params.get('ext_enddate', None)
        # search date type
        ext_search_date_type = request.params.get('ext_search_date_type', 'information_date')
        # datetime2utc
        utc_start_date = sip4d_helpers.get_utcdatetime(start_date)
        utc_end_date = sip4d_helpers.get_utcdatetime(end_date)
        # log.debug("utc_start_date %s" % utc_start_date)

        fq = ''
        if utc_start_date and utc_end_date and len(utc_start_date) > 0 and len(utc_end_date) > 0:
            fq = '{ext_search_date_type}:[{start_date} TO {end_date}]'.format(
                ext_search_date_type=ext_search_date_type, start_date=utc_start_date, end_date=utc_end_date)

        search_dict = {
            'q': q,
            'fq': fq,
            'rows': limit,
            'sort': tk.c.order_by,
            'start': (page - 1) * limit,
            'include_private': tk.asbool(config.get(
                'ckan.search.default_include_private', True)),
        }

        params_nopage = [(k, v) for k, v in request.params.items() if k != 'page']

        query = logic.get_action('package_search')(context, search_dict)

        def pager_url(q=None, page=None):
            # url = h.url_for(controller='ckanext.sip4d.controller:Sip4DCustomViewController', action='datesetview')
            url = h.url_for('/sip4d/sip4d_update_list_page')
            params = list(params_nopage)
            params.append(('page', page))
            return url_with_params(url, params)

        tk.c.page = h.Page(
            collection=query['results'],
            page=page,
            url=pager_url,
            item_count=query['count'],
            items_per_page=limit
        )

        tk.c.page.items = query['results']
        if start_date:
            tk.c.page.startdate = start_date
        if end_date:
            tk.c.page.enddate = end_date

        return render('sip4d/base.html')
    except tk.NotAuthorized:
        return tk.abort(403, _('Not authorized to see this page'))
    except tk.ObjectNotFound:
        return tk.abort(404, _('ObjectNotFound'))
    except Exception as e:
        log.error('DisasterInfo search error: %r', e.args)
        return tk.abort(500)


def disasterupdate(response):
    def _errormes(mes, status):
        mesjson = dict()
        mesjson['error'] = mes
        mesjson['status'] = status
        return h.json.dumps(mesjson)

    try:
        # post value
        context = {'model': model, 'user': tk.c.user, 'return_query': True}

        update_type = request.params.get('type', '')

        response.content_type = 'application/json; charset=utf-8'
        if not update_type:
            return _errormes(_('not found {0} param'.format('update_type')), 400)

        update_value = request.json[update_type];
        if not update_value:
            update_value = ''

        #  datasetIds = [v for k, v in request.json if k == 'dataset_ids']
        datasetIds = request.json['dataset_ids']

        log.debug('update disaster info, update_type: %s' % update_type)
        log.debug(datasetIds)

        if len(datasetIds) == 0:
            return _errormes(_('Dataset is not selected'), 400)

        update_count = 0
        for pkgid in datasetIds:
            try:
                # get package
                pkg_dict = logic.get_action('package_show')(context, {'id': pkgid})
                # pkg = model.Package.get(pkgid)
                if not pkg_dict:
                    continue
                # check authentication
                try:
                    logic.check_access('package_update', context, {'id': pkgid})
                except logic.NotAuthorized:
                    log.error('DisasterInfo update error: NoAuthorized')
                    continue

                # extras update
                checkflag = False
                for extra in pkg_dict['extras']:
                    if extra['key'] == update_type:
                        extra['value'] = update_value
                        extra['state'] = 'active'
                        checkflag = True
                        break

                log.debug(pkg_dict)

                if not checkflag:
                    extraitem = dict()
                    extraitem['key'] = update_type
                    extraitem['value'] = update_value
                    extraitem['state'] = 'active'
                    pkg_dict['extras'].append(extraitem)

                update_dict = logic.get_action('package_update')(context, pkg_dict)

                if update_dict:
                    update_count += 1
                sleep(0.01)
            except Exception as e:
                log.error('DisasterInfo update error: %r', e.args)

        success = dict()
        success['success'] = True
        success['mes'] = _('{0} / {1} datasets was updated').format(str(update_count), str(len(datasetIds)))
        return h.json.dumps(success)
    except tk.NotAuthorized:
        return tk.abort(403, _('Not authorized to see this page'))
    except Exception as e:
        log.error('DisasterInfo update error: %r', e.args)
        return tk.abort(500)
    return _errormes('Server Error', 500)


def sip4d_search_dataset():
    """
    top画面からのsearch,organization指定で検索画面切替
    :return:
    """
    params_list = [(k, v) for k, v in request.params.items() if k != 'organization']
    org_name = tk.request.params.get('organization', None)
    search_url = h.url_for('dataset.search')  # /dataset
    if params_list is not None and len(params_list) > 0:
        search_url = url_with_params(search_url, params_list)
    if org_name is not None:
        search_url += '&organization=' + org_name
        # search_url = h.url_for(controller='organization', action='read', id=org_name)
        # search_url += '&sort=score+desc,+metadata_modified+desc'
    return tk.redirect_to(search_url)