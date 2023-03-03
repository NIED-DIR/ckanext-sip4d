# encoding: utf-8

import logging
import six
from ckan import model
from six.moves.urllib.parse import urlencode
from time import sleep
from paste.deploy.converters import asbool
from ckan.lib.base import BaseController
from ckan.common import g, config, request, response
import ckantoolkit as tk
import ckan.lib.helpers as h
import ckan.logic as logic

from ckanext.sip4d import helpers as sip4d_helpers

log = logging.getLogger(__name__)


def url_with_params(url, params):
    params = _encode_params(params)
    return url + u'?' + urlencode(params)


def _encode_params(params):
    return [(k, v.encode('utf-8') if isinstance(v, six.string_types) else str(v))
            for k, v in params]  # basestring


class Sip4DCustomViewController(BaseController):

    def datesetview(self):
        context = {'model': model, 'session': model.Session, 'user': tk.c.user or tk.c.author, 'return_query': True}
        try:
            limit = int(request.params.get('limit', 20))
            page = int(request.params.get('page', 1))

            q = tk.c.q = request.params.get('q', '')
            tk.c.order_by = request.params.get('sort', 'information_date desc')
            if not tk.c.order_by.endswith('asc') and not tk.c.order_by.endswith('desc'):
                tk.c.order_by = 'information_date desc'

            # startdatetime-enddatetime
            start_date = request.params.get('ext_startdate', None)
            end_date = request.params.get('ext_enddate', None)
            # datetime2utc
            utc_start_date = sip4d_helpers.get_utcdatetime(start_date)
            utc_end_date = sip4d_helpers.get_utcdatetime(end_date)

            fq = ''
            if utc_start_date and utc_end_date and utc_start_date.__len__ > 0 and utc_end_date.__len__ > 0:
                fq = 'information_date:[{start_date} TO {end_date}]'.format(
                    start_date=utc_start_date, end_date=utc_end_date)

            search_dict = {
                'q': q,
                'fq': fq,
                'rows': limit,
                'sort':  tk.c.order_by,
                'start': (page - 1) * limit,
                'include_private': asbool(config.get(
                    'ckan.search.default_include_private', True)),
            }

            params_nopage = [(k, v) for k, v in request.params.items() if k != 'page']

            query = logic.get_action('package_search')(context, search_dict)

            def pager_url(q=None, page=None):
                url = h.url_for(controller='ckanext.sip4d.controller:Sip4DCustomViewController', action='datesetview')
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
        except logic.NotAuthorized:
            tk.abort(403, tk._('Not authorized to see this page'))
        except Exception as e:
            log.error('DisasterInfo search error: %r', e.args)
            tk.abort(500)
        return tk.render('sip4d/base.html')

    def disasterupdate(self):

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
                return _errormes(tk._('not found {0} param'.format('update_type')), 400)

            update_value = request.params.get(update_type, '')

            datasetIds = [v for k, v in request.params.items() if k == 'dataset_ids']

            if len(datasetIds) == 0:
                return _errormes(tk._('Dataset is not selected'), 400)

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
                    if not checkflag:
                        extraitem = dict()
                        extraitem['key'] = update_type
                        extraitem['value'] = update_value
                        extraitem['state'] = 'active'
                        pkg_dict['extras'].append(extraitem)

                    update_dict = logic.get_action('package_update')(context, pkg_dict)
                    # log.info('Mas Update '+update_type+' :'+pkgid)
                    if update_dict:
                        update_count += 1
                    sleep(0.01)
                except Exception as e:
                    log.error('DisasterInfo update error: %r', e.args)

            success = dict()
            success['success'] = True
            success['mes'] = tk._('{0} / {1} datasets was updated').format(str(update_count), str(len(datasetIds)))
            return h.json.dumps(success)
        except logic.NotAuthorized:
            tk.abort(403, tk._('Not authorized to see this page'))
        except Exception as e:
            log.error('DisasterInfo update error: %r', e.args)
            tk.abort(500)
        return _errormes('Server Error', 500)


    def sip4d_search_dataset(self):
        # search振り分け対象の
        # 検索文字列取得
        # obj = tk.request
        # for m in inspect.getmembers(obj):
        #     print(m)
        search_url = h.url_for('dataset.search')  # /dataset
        # url=h.url_for(controller='organization', action='read', id=organization.name)
        tk.redirect_to(search_url)