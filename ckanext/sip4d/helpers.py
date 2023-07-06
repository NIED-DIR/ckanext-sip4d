# encoding: utf-8

import re
import json
from dateutil.parser import parse
import pytz
from ckan.common import config
import ckan.lib.helpers as h

import ckan.logic as logic
import logging

log = logging.getLogger(__name__)


def get_sip4d_pkg_dict_extra(pkg_dict, key, default=None):
    """
    :param pkg_dict: dictized dataset
    :param key extra key to lookup
    :param default value returned if not found
    """
    extras = pkg_dict['extras'] if 'extras' in pkg_dict else []
    for extra in extras:
        if extra['key'] == key:
            extvalue = extra['value']
            extras.remove(extra)
            return extvalue

    return default


def get_sip4d_default_spatial(local=None):
    bbox = list()
    if local == 'ja':
        bbox = [122.5, 20.2, 154.0, 51.5]
    else:
        extent = config.get('ckan.spatial.default_map_extent', None)
        if extent:
            extents = extent.split(',')
            if len(extents) >= 4:
                bbox = [float(extents[0]), float(extents[1]), float(extents[2]), float(extents[3])]
    if len(bbox) != 4:
        bbox = [-180, -90, 180, 90]

    coordinates = [[[bbox[0], bbox[1]], [bbox[2], bbox[1]], [bbox[2], bbox[3]], [bbox[0], bbox[3]], [bbox[0], bbox[1]]]]
    spatial = dict()
    spatial['type'] = "Polygon"
    spatial['coordinates'] = coordinates
    return json.dumps(spatial)


def get_sip4d_timerange_value(start, end):
    if not start or not end:
        return ""
    start_date = ""
    end_date = ""
    try:
        DATETIME_FORMAT = '%Y/%m/%d'
        valid_date = parse(start)
        start_date = valid_date.strftime(DATETIME_FORMAT)
        valid_date = parse(end)
        end_date = valid_date.strftime(DATETIME_FORMAT)
    except (TypeError, ValueError) as e:
        return ""

    if start_date and end_date:
        return start_date + " - " + end_date
    return ""


def get_sip4d_localedatetime(datetime):
    if not datetime:
        return ""
    try:
        valid_date = parse(datetime)
        # utc_dt = valid_date.replace(tzinfo=pytz.timezone('UTC'))
        utc_tz = pytz.timezone('UTC')
        utc_dt = utc_tz.localize(valid_date)
        locale_now = utc_dt.astimezone(h.get_display_timezone())
        datetime_format = '%Y-%m-%dT%H:%M:%S'
        return locale_now.strftime(datetime_format)
    except (TypeError, ValueError) as e:
        print(e)
    return ""


def get_utcdatetime(datetime):
    if not datetime:
        return ""
    has_timezone = False
    if datetime.endswith('Z'):
        datetime = datetime.rstrip('Z')
        has_timezone = True
    try:
        valid_date = parse(datetime)
        # locale_date = valid_date.replace(tzinfo=h.get_display_timezone())
        locale_tz = h.get_display_timezone()
        locale_date = locale_tz.localize(valid_date)
        utc_dt = locale_date.astimezone(pytz.timezone('UTC'))
        datetime_format = '%Y-%m-%dT%H:%M:%S'
        if has_timezone:
            datetime_format = '%Y-%m-%dT%H:%M:%SZ'
        return utc_dt.strftime(datetime_format)
    except (TypeError, ValueError) as e:
        print(e)
    return ""


def render_sip4d_datetime(strdatetime, lang):
    if not strdatetime:
        return ""
    try:
        valid_date = parse(strdatetime)
        if lang == 'ja':
            newdate_time = valid_date.strftime(u'%Y{0}%m{1}%d{2} %H{3}%M{4}').format('年', '月', '日', '時', '分')
            # newdate_time = valid_date.strftime(u'%Y年%m月%d日 %H時%M分'.encode('utf-8')).decode('utf-8')
            return newdate_time
        else:
            datetime_format = '%Y-%m-%dT%H:%M'
            return valid_date.strftime(datetime_format)
    except (TypeError, ValueError) as e:
        print(e)
    return strdatetime


def is_sip4d_guests_ban():
    is_ban = config.get('ckanext.sip4d.guests_ban', False)
    if is_ban == 'true' or is_ban is True:
        return True
    return False


def get_sip4d_logo_path():
    logo_path = config.get('ckanext.sip4d.logo_path', '/images/logo_SIP4D-CKAN_01.svg')
    return logo_path


def get_sip4d_logo_width():
    logo_style = config.get('ckanext.sip4d.logo_width_percent', '55')
    logo_style += '%'
    return logo_style


def get_sip4d_organization_title():
    value = config.get('ckanext.sip4d_organization_title', 'SIP4D')
    return value


def get_sip4d_organization_id():
    value = config.get('ckanext.sip4d_organization_id', 'sip4d')
    return value


def get_sip4d_site_title():
    site_title = config.get('ckanext.sip4d.site_title', 'SIP4D-CKAN')
    return site_title


def get_sip4d_show_search_flag():
    show_flag = config.get('ckanext.sip4d.show_search_div_flag', False)
    if show_flag == 'true' or show_flag is True:
        return True
    return False


def sip4d_featured_organizations(count=1):
    """Returns a list of favourite organization in the form
    of organization_list action function
    """
    #    config_orgs = config.get('ckan.featured_orgs', '').split()
    config_orgs = [get_sip4d_organization_id()]
    #    orgs = h.featured_group_org(get_action='organization_show',
    orgs = sip4d_featured_group_org(get_action='organization_show',
                                    list_action='organization_list',
                                    count=count,
                                    items=config_orgs)
    return orgs


def sip4d_featured_group_org(items, get_action, list_action, count):
    def get_group(dict_id):
        context = {'ignore_auth': True,
                   'limits': {'packages': 5},
                   'for_view': True}
        data_dict = {'id': dict_id,
                     'include_datasets': True}

        try:
            out = logic.get_action(get_action)(context, data_dict)
        #            log.debug('sip4d_featured_group_org 1')
        #            log.debug(out)
        except logic.NotFound:
            #            log.debug('sip4d_featured_group_org: logic not found')
            return None
        return out

    groups_data = []

    #    extras = logic.get_action(list_action)({}, {})

    # list of found ids to prevent duplicates
    found = []

    #    for group_name in items + extras:
    for group_name in items:
        log.debug('group_name=' + group_name)

        group = get_group(group_name)
        if not group:
            continue
        # check if duplicate
        if group['id'] in found:
            continue
        found.append(group['id'])
        groups_data.append(group)
        if len(groups_data) == count:
            break

    return groups_data


def get_sip4d_resource_thumbnail_url(resources):
    """
    get package thumbnail url
    resources package.resources
    """
    try:
        # config
        thumbnail_width = config.get('ckanext.sip4d.thumbnail_width', '140px')
        thumbnail_height = config.get('ckanext.sip4d.thumbnail_height', '140px')

        image_dict = dict()
        thumbnail_url = None
        pattern = "^thumbnail.(jpg|png|jpeg|gif)"

        if resources is not None and len(resources) > 0:
            for resource in resources:
                if thumbnail_url is not None:
                    break
                resource_name = resource['name'] if 'name' in resource else None
                if resource_name is not None and re.match(pattern, resource_name, re.IGNORECASE):
                    thumbnail_url = resource['url'] if 'url' in resource else None
        if thumbnail_url is not None:
            image_dict['width'] = thumbnail_width
            image_dict['height'] = thumbnail_height
            image_dict['url'] = thumbnail_url
            return image_dict
    except ValueError as e:
        print(e)
    return None


def get_sip4d_search_item_list():
    """
    configから検索に追加するアイテムリストを取得
    ckanext.sip4d.search_item_list = id1:name2 id2:name2 id3:name3
    title:タイトル notes:説明  author:著作者 tags:タグ disaster_name:災害名　res_format:データ形式
    [{id:"title", name:"タイトル"},{id:"notes", name:"説明"},{id:"author", name:"著作者"},{id:"notes", name:"タグ"}]
    :return list():
    """
    search_item_str = config.get('ckanext.sip4d.search_item_list', None)
    search_dir_list = []
    if search_item_str is not None:
        # search_item_list = search_item_str.split()
        # if len(search_item_list) > 0:
        for search_item_str in search_item_str.split():
            seach_item_list = search_item_str.split(':')
            if len(seach_item_list) == 2:
                search_dir_list.append({'id':seach_item_list[0],
                                        'name':seach_item_list[1]})
    return search_dir_list


def build_sip4d_nav_main(*args):
    """
    Custom ckan.kub.helper build_nav_main function
    """

    output = ''
    sip4d_id = get_sip4d_organization_id()
    sip4d_name = get_sip4d_organization_title()
    if sip4d_id and sip4d_name:
        output += h.literal('<li>') + h.literal(
            '<a href="/organization/' + sip4d_id + u'?sort=metadata_modified+desc">') \
                  + sip4d_name + h.literal('</a>') + h.literal('</li>')

    for item in args:
        menu_item, title, highlight_controllers = (list(item) + [None] * 3)[:3]
        output += h.build_nav_icon(menu_item, title, highlight_controllers=highlight_controllers)
    print(output)
    return output
