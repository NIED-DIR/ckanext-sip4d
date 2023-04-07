# encoding: utf-8

import logging
from dateutil.parser import parse
import pytz

import sys
import re
import os
import ckan.plugins as p
import ckan.lib.helpers as h
import ckan.plugins.toolkit as tk
from ckan.logic.validators import email_validator
from ckan.lib.navl.dictization_functions import Invalid

try:
    from ckan.lib.plugins import DefaultTranslation
except ImportError:
    class DefaultTranslation():
        pass
from ckanext.sip4d.logic import auth_issysadmin, auth_update
import ckanext.sip4d.helpers as sip4d_helpers

if tk.check_ckan_version(min_version="2.9.0"):
    from ckanext.sip4d.plugin.flask_plugin import Sip4DMixinPlugin
else:
    print('sip4d import 2.8')
    from ckanext.sip4d.plugin.pylons_plugin import Sip4DMixinPlugin


log = logging.getLogger(__name__)

config = tk.config

current_dir = os.path.abspath(os.path.dirname(__file__))
i18n_dir = os.path.join(current_dir, u"../i18n")



class Sip4DDataViewPlugin(Sip4DMixinPlugin, p.SingletonPlugin, tk.DefaultDatasetForm, DefaultTranslation):

    log.debug('load sip4dview plugin')

    p.implements(p.IConfigurer)
    # p.implements(p.IRoutes, inherit=True)
    p.implements(p.IFacets, inherit=True)
    p.implements(p.IAuthFunctions)
    p.implements(p.IAuthenticator)
    p.implements(p.ITemplateHelpers)

    if tk.check_ckan_version(min_version='2.5.0'):
        p.implements(p.ITranslation, inherit=True)

    # ------------- ITranslation ---------------#

    # def i18n_domain(self):
    #     return u'ckanext-{name}'.format(name='sip4d')
    # ITranslation
    # def i18n_directory(self):
    #     log.debug('ckanext-sip4d i18n_dir %s' % i18n_dir)
    #     return i18n_dir
    def i18n_directory(self):
        extension_module_name = '.'.join(self.__module__.split('.')[0:2])
        module = sys.modules[extension_module_name]
        path = os.path.join(os.path.dirname(module.__file__), 'i18n')
        print("sip4d i18n_directory : %s" % path)
        return os.path.join(os.path.dirname(module.__file__), 'i18n')

    def i18n_locales(self):
        directory = self.i18n_directory()
        return [d for
                d in os.listdir(directory)
                if os.path.isdir(os.path.join(directory, d))]

    def i18n_domain(self):
        return 'ckanext-sip4d'

    # ------------- IConfigurer ---------------#

    def update_config(self, config):
        tk.add_public_directory(config, '../public')
        tk.add_template_directory(config, '../templates')
        tk.add_resource('../public', 'ckanext-sip4d')

    # ------------- IRoutes ---------------#
    # def after_map(self, map):
    #     controller = 'ckanext.sip4d.controller:Sip4DCustomViewController'
    #     map.connect('/sip4d/sip4d_update_list_page', controller=controller, action='datesetview')
    #     map.connect('/sip4d/disaster_update', controller=controller, action='disasterupdate')
    #     return map

    # ------------- IAuthFunctions ---------------#

    def get_auth_functions(self):
        return {
            'sip4d_issysadmin': auth_issysadmin,
            'sip4d_update': auth_update,
        }
    # ------------- IFacets ---------------#

    def dataset_facets(self, facets_dict, package_type):
        show_group = config.get('ckanext.sip4d.show_facets_groups', False)
        if show_group is False and package_type == 'dataset' and 'groups' in facets_dict:
            del facets_dict['groups']
        return facets_dict

    def group_facets(self, facets_dict, group_type, package_type):
        show_group = config.get('ckanext.sip4d.show_facets_groups', False)
        if show_group is False and group_type == 'organization' and 'groups' in facets_dict:
            del facets_dict['groups']
        return facets_dict

    # def organization_facets(self, facets_dict, organization_type, package_type):
    #     return facets_dict

    # ------------- IAuthenticator ---------------#

    def identify(self):
        # print('IAuthenticator identify')
        # obj = tk.request
        # for m in inspect.getmembers(obj):
        #     print(m)
        request_path = tk.request.path
        if request_path.startswith('/dashboard'):
            # if tk.request.referrer is None:  # login redirect　None
            return tk.redirect_to(h.url_for(u'home.index'))
        return
    #     return tk.redirect_to('https://server.domain.com/')  # tk.url_for(u'home.index'))

    def login(self):
        # print('IAuthenticator login')
        return

    def logout(self):
        # print('IAuthenticator logout')
        return

    # ------------- ITemplateHelpers ---------------#
    def get_helpers(self):
        return {
            "build_sip4d_nav_main": sip4d_helpers.build_sip4d_nav_main,
            'get_sip4d_localedatetime': sip4d_helpers.get_sip4d_localedatetime,
            'get_sip4d_logo_path': sip4d_helpers.get_sip4d_logo_path,
            'get_sip4d_logo_width': sip4d_helpers.get_sip4d_logo_width,
            "get_sip4d_resource_thumbnail_url": sip4d_helpers.get_sip4d_resource_thumbnail_url,
            'get_sip4d_pkg_dict_extra': sip4d_helpers.get_sip4d_pkg_dict_extra,
            'get_sip4d_default_spatial': sip4d_helpers.get_sip4d_default_spatial,
            "get_sip4d_organization_title": sip4d_helpers.get_sip4d_organization_title,
            "get_sip4d_organization_id": sip4d_helpers.get_sip4d_organization_id,
            'get_sip4d_search_item_list': sip4d_helpers.get_sip4d_search_item_list,
            "get_sip4d_show_search_flag": sip4d_helpers.get_sip4d_show_search_flag,
            'get_sip4d_timerange_value': sip4d_helpers.get_sip4d_timerange_value,
            'get_sip4d_site_title' : sip4d_helpers.get_sip4d_site_title,
            'render_sip4d_datetime': sip4d_helpers.render_sip4d_datetime,
            "is_sip4d_guests_ban": sip4d_helpers.is_sip4d_guests_ban,
            # "is_sip4d_view_login_user": sip4d_helpers.is_sip4d_view_login_user,
            "sip4d_featured_organizations": sip4d_helpers.sip4d_featured_organizations,
        }


class Sip4DDataPlugin(p.SingletonPlugin, tk.DefaultDatasetForm, DefaultTranslation):

    log.debug('load sip4ddata plugin')

    p.implements(p.IDatasetForm, inherit=False)
    p.implements(p.IPackageController, inherit=True)

    def is_fallback(self):
        return True

    def package_types(self):
        return []

    # def setup_template_variables(self, context, data_dict):
    #    return

    def create(self, package):
        self.check_informationdate(package)

    def edit(self, package):
        self.check_informationdate(package)

    def check_informationdate(self, package):
        if not package.id:
            return
        for extra in package.extras_list:
            if extra.key == 'information_date':
                if extra.state == 'active' and extra.value:
                    try:
                        valid_date = parse(extra.value)
                        hasmicroseconds = False
                        try:
                            time_tuple = re.split('[^\d]+', extra.value, maxsplit=5)
                            m = re.match('(?P<seconds>\d{2})(\.(?P<microseconds>\d{6}))?$', time_tuple[5])
                            # seconds = int(m.groupdict().get('seconds'))
                            microseconds = int(m.groupdict(0).get('microseconds'))
                            if microseconds > 0:
                                hasmicroseconds = True
                        except ValueError as e:
                            print(e)
                        datetime_format = '%Y-%m-%dT%H:%M:%S'
                        if hasmicroseconds:
                            datetime_format = '%Y-%m-%dT%H:%M:%S.%f'
                        extra.value = valid_date.strftime(datetime_format)
                        break
                    except ValueError as e:
                        error_dict = {'information_date': [u'Error decoding datetime: %s' % str(e)]}
                        raise tk.ValidationError(error_dict, error_summary=error_dict)
                    except TypeError as e:
                        error_dict = {'information_date': [u'Error decoding datetime: %s' % str(e)]}
                        raise tk.ValidationError(error_dict, error_summary=error_dict)

    def validate(self, context, data_dict, schema, action):

        if action == 'package_update' or action == 'package_create':
            extralist = ['information_date','information_datetime',
                         'disaster_id', 'disaster_name',
                         'language', 'credit', 'testflg', 'harvest_flag', 'spatial',
                         'author_mailform', 'maintainer_mailform','harvestflg','harvestmode']
            for checkname in extralist:
                checkvalue = None
                checkflag = False
                if checkname == 'information_datetime':
                    if data_dict.get(checkname):
                        checkvalue = data_dict.get(checkname)
                        if checkvalue:
                            try:
                                valid_date = parse(checkvalue)
                                local_dt = valid_date.replace(tzinfo=h.get_display_timezone())
                                utc_date = local_dt.astimezone(pytz.utc)
                                datetime_format = '%Y-%m-%dT%H:%M:%S'
                                new_information_date = utc_date.strftime(datetime_format)
                                checkvalue = new_information_date
                            except (TypeError, ValueError) as e:
                                print(e)
                    if 'extras' in data_dict:
                        for extra in data_dict['extras']:
                            if extra['key'] == 'information_date':
                                checkflag = True
                                break
                    else:
                        data_dict['extras'] = []
                    if not checkflag and checkvalue:
                        extraitem = dict()
                        extraitem['key'] = 'information_date'
                        extraitem['value'] = checkvalue
                        data_dict['extras'].append(extraitem)
                else:
                    if data_dict.get(checkname):
                        checkvalue = data_dict.get(checkname)
                    if 'extras' in data_dict:
                        for extra in data_dict['extras']:
                            if extra['key'] == checkname:
                                checkflag = True
                                break
                    else:
                        data_dict['extras'] = []
                    if not checkflag and checkvalue:
                        extraitem = dict()
                        extraitem['key'] = checkname
                        extraitem['value'] = checkvalue
                        data_dict['extras'].append(extraitem)

            # 'author_email', 'maintainer_email'
            maillist = ['author_email', 'maintainer_email']
            for mailcolumn in maillist:
                if data_dict.get(mailcolumn):
                    email_value = data_dict.get(mailcolumn)
                    try:
                        email_validator(email_value, None)
                    except Invalid:
                        extracolumn = str()
                        if mailcolumn == 'author_email':
                            extracolumn = 'author_mailform'
                        elif mailcolumn == 'maintainer_email':
                            extracolumn = 'maintainer_mailform'
                        data_dict[mailcolumn] = u''
                        addflag = True
                        if 'extras' in data_dict:
                            for extra in data_dict['extras']:
                                if extra['key'] == extracolumn:
                                    if not extra['value']:
                                        extra['value'] = email_value
                                    addflag = False
                                    break
                        else:
                            data_dict['extras'] = []
                        if addflag:
                            extraitem = dict()
                            extraitem['key'] = extracolumn
                            extraitem['value'] = email_value
                            data_dict['extras'].append(extraitem)
        return tk.navl_validate(data_dict, schema, context)

    def before_search(self, search_params):
        # log.debug('call before_search')
        # if 'q' in search_params:
        #     search_params['q'] = html.escape(search_params['q'])

        extras = search_params.get('extras')
        if not extras:
            return search_params
        start_date = extras.get('ext_startdate')
        end_date = extras.get('ext_enddate')
        # locale to utc
        utc_start_date = sip4d_helpers.get_utcdatetime(start_date)
        utc_end_date = sip4d_helpers.get_utcdatetime(end_date)
        # search params
        if start_date and end_date and len(start_date) > 0 and len(end_date) > 0:
            fq = search_params['fq']
            fq = '{fq} +information_date:[{start_date} TO {end_date}]'.format(
                fq=fq, start_date=utc_start_date, end_date=utc_end_date)
            search_params['fq'] = fq

        return search_params
