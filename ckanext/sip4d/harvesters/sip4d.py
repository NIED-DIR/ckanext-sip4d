# encoding: utf-8

import os
import io
from PIL import Image

import six
from six.moves.urllib.parse import urlparse, urlencode
from six.moves.urllib.request import Request, urlopen
from six.moves.urllib.error import URLError, HTTPError
from six.moves.http_client import HTTPException

import requests
import datetime
import socket

from ckan import model
from ckan.lib.uploader import get_storage_path
from ckan.lib.helpers import json, get_pkg_dict_extra
from ckan.logic import ValidationError, NotFound, get_action, NotAuthorized

import ckan.plugins as p
from ckan.plugins.core import SingletonPlugin, implements

from ckanext.harvest.interfaces import IHarvester
from ckanext.harvest.model import HarvestObjectExtra
from ckanext.harvest.model import HarvestJob, HarvestObject, HarvestGatherError
from ckanext.sip4d.harvesters.base import Sip4DHarvesterBase
import logging

log = logging.getLogger(__name__)


class Sip4DHarvester(Sip4DHarvesterBase, SingletonPlugin):
    implements(IHarvester)

    config = None

    force_import = False

    api_version = 2
    action_api_version = 3

    def info(self):
        return {
            'name': 'sip4d',
            'title': 'CKAN (SIP4D)',
            'description': p.toolkit._('Harvests remote CKAN(SIP4D) Dataset'),
            'form_config_interface': 'Text'
        }

    def _get_action_api_offset(self):
        return '/api/%d/action' % self.action_api_version

    def _get_search_api_offset(self):
        return '%s/package_search' % self._get_action_api_offset()

    def _get_content(self, url):
        http_request = Request(url=url)

        api_key = self.config.get('api_key')
        if api_key:
            http_request.add_header('Authorization', api_key)

        try:
            http_response = urlopen(http_request)
        except HTTPError as e:
            if e.getcode() == 404:
                raise ContentNotFoundError('HTTP error: %s' % e.code)
            else:
                raise ContentFetchError('HTTP error: %s' % e.code)
        except URLError as e:
            raise ContentFetchError('URL error: %s' % e.reason)
        except HTTPException as e:
            raise ContentFetchError('HTTP Exception: %s' % e)
        except socket.error as e:
            raise ContentFetchError('HTTP socket error: %s' % e)
        except Exception as e:
            raise ContentFetchError('HTTP general exception: %s' % e)
        return http_response.read()

    def _get_group(self, base_url, group):
        url = base_url + self._get_action_api_offset() + '/group_show?id=' + \
              group['id']
        try:
            content = self._get_content(url)
            data = json.loads(content)
            if self.action_api_version == 3:
                return data.pop('result')
            return data
        except (ContentFetchError, ValueError):
            log.debug('Could not fetch/decode remote group')
            raise RemoteResourceError('Could not fetch/decode remote group')

    def _get_organization(self, base_url, org_name):
        url = base_url + self._get_action_api_offset() + \
              '/organization_show?id=' + org_name
        try:
            content = self._get_content(url)
            content_dict = json.loads(content)
            return content_dict['result']
        except (ContentFetchError, ValueError, KeyError):
            log.debug('Could not fetch/decode remote group')
            raise RemoteResourceError(
                'Could not fetch/decode remote organization')

    def _get_organization_thumb(self, url):
        try:
            if url.startswith('http'):
                result = urlparse(url)
                imagename = result.path.rsplit('/', 1)[1]
                storage_dir = get_storage_path()
                upload_dir = os.path.join(storage_dir, 'storage', 'uploads', 'group')
                if os.path.exists(upload_dir):
                    image_path = os.path.join(upload_dir, imagename)
                    req = requests.get(url)
                    img = Image.open(io.BytesIO(req.content))
                    img.save(image_path)
        except Exception as e:
            log.error('_get_organization_thumb error: %s' % e)

    def _set_config(self, config_str):
        if config_str:
            self.config = json.loads(config_str)
            if 'api_version' in self.config:
                self.api_version = int(self.config['api_version'])

            log.debug('Using config: %r', self.config)
        else:
            self.config = {}

    def validate_config(self, source_config):
        try:
            if not source_config:
                raise ValueError('No configuration settings')

            config_obj = json.loads(source_config)

            if 'api_version' in config_obj:
                try:
                    int(config_obj['api_version'])
                except ValueError:
                    raise ValueError('api_version must be an integer')

            if 'default_tags' in config_obj:
                if not isinstance(config_obj['default_tags'], list):
                    raise ValueError('default_tags must be a list')
                if config_obj['default_tags'] and \
                        not isinstance(config_obj['default_tags'][0], dict):
                    raise ValueError('default_tags must be a list of '
                                     'dictionaries')

            if 'default_groups' in config_obj:
                if not isinstance(config_obj['default_groups'], list):
                    raise ValueError('default_groups must be a *list* of group'
                                     ' names/ids')
                if config_obj['default_groups'] and \
                        not isinstance(config_obj['default_groups'][0],
                                       six.string_types):  # basestring
                    raise ValueError('default_groups must be a list of group '
                                     'names/ids (i.e. strings)')

                # Check if default groups exist
                context = {'model': model, 'user': p.toolkit.c.user}
                config_obj['default_group_dicts'] = []
                for group_name_or_id in config_obj['default_groups']:
                    try:
                        group = get_action('group_show')(
                            context, {'id': group_name_or_id})
                        # save the dict to the config object, as we'll need it
                        # in the import_stage of every dataset
                        config_obj['default_group_dicts'].append(group)
                    except NotFound as e:
                        raise ValueError('Default group not found')
                source_config = json.dumps(config_obj)

            if 'default_extras' in config_obj:
                if not isinstance(config_obj['default_extras'], dict):
                    raise ValueError('default_extras must be a dictionary')

            if 'organizations_filter_include' in config_obj \
                    and 'organizations_filter_exclude' in config_obj:
                raise ValueError('Harvest configuration cannot contain both '
                                 'organizations_filter_include and organizations_filter_exclude')

            if 'groups_filter_include' in config_obj \
                    and 'groups_filter_exclude' in config_obj:
                raise ValueError('Harvest configuration cannot contain both '
                                 'groups_filter_include and groups_filter_exclude')

            if 'user' in config_obj:
                # Check if user exists
                context = {'model': model, 'user': p.toolkit.c.user}
                try:
                    user = get_action('user_show')(
                        context, {'id': config_obj.get('user')})
                except NotFound:
                    raise ValueError('User not found')

            for key in ('read_only', 'force_all'):
                if key in config_obj:
                    if not isinstance(config_obj[key], bool):
                        raise ValueError('%s must be boolean' % key)

            if 'harvest_flags' in config_obj:
                if not isinstance(config_obj['harvest_flags'], list):
                    raise ValueError('harvest_flags must be a list')
                if config_obj['harvest_flags'] and \
                        not isinstance(config_obj['harvest_flags'][0], dict):
                    raise ValueError('harvest_flags must be a list of dictionaries')
                config_obj = json.loads(source_config)
                update_now = datetime.datetime.now()
                update_date = update_now.strftime('%Y-%m-%dT%H:%M:%S')
                config_obj['harvest_update'] = update_date
                source_config = json.dumps(config_obj, ensure_ascii=False, encoding='utf8', indent=2, sort_keys=True)
            # else:
            #     raise ValueError('harvest_flags must in config')

            if 'testflags' in config_obj:
                if not isinstance(config_obj['testflags'], list):
                    raise ValueError('testflags must be a list')
            #else:
            #    raise ValueError('testflags must in config')

            if 'harvestflgs' in config_obj:
                if not isinstance(config_obj['harvestflgs'], list):
                    raise ValueError('harvestflgs must be a list')
            else:
                raise ValueError('harvestflgs must in config')

            if 'harvestmode' in config_obj:
                if config_obj['harvestmode'] not in ('overwrite', 'append'):
                    raise ValueError('Only "overwrite" or "append" can be specified for harvestmode')
            else:
                raise ValueError('harvestmode must in config')

            if 'include_private' in config_obj:
                if not isinstance(config_obj['include_private'], bool):
                    raise ValueError('include_private must be a bool')

        except ValueError as e:
            raise e

        return source_config

    def gather_stage(self, harvest_job):
        log.debug('In SIP4D CKANHarvester gather_stage (%s)',
                  harvest_job.source.url)
        p.toolkit.requires_ckan_version(min_version='2.0')
        get_all_packages = True

        self._set_config(harvest_job.source.config)

        # Get source URL
        remote_ckan_base_url = harvest_job.source.url.rstrip('/')

        # Filter in/out datasets from particular organizations
        fq_terms = []
        org_filter_include = self.config.get('organizations_filter_include', [])
        org_filter_exclude = self.config.get('organizations_filter_exclude', [])
        # if org_filter_include:
        #    fq_terms.append(' OR '.join(
        #        'organization:%s' % org_name for org_name in org_filter_include))
        # elif org_filter_exclude:
        #    fq_terms.extend(
        #        '-organization:%s' % org_name for org_name in org_filter_exclude)
        if org_filter_include:
            ors = str()
            if len(fq_terms) > 0:
                ors = ' OR '
            fq_terms.append(ors + 'organization:(' + ' OR '.join(org_filter_include) + ')')
        elif org_filter_exclude:
            ors = str()
            if len(fq_terms) > 0:
                ors = ' OR '
            fq_terms.append(ors + 'organization:(' + ' OR '.join(org_filter_exclude) + ')')

        groups_filter_include = self.config.get('groups_filter_include', [])
        groups_filter_exclude = self.config.get('groups_filter_exclude', [])
        if groups_filter_include:
            ors = str()
            if len(fq_terms) > 0:
                ors = ' OR '
            fq_terms.append(ors + 'groups:(' + ' OR '.join(groups_filter_include) + ')')
        elif groups_filter_exclude:
            ors = str()
            if len(fq_terms) > 0:
                ors = ' OR '
            fq_terms.append(ors + 'groups:(' + ' OR '.join(groups_filter_exclude) + ')')

        # Mod Harvester Flag Filter
        # <field name="harvest_flag" type="text_ja" indexed="true" stored="true" multiValued="true" />
        # <field name="id" type="string" indexed="true" docValues="true" required="true" />
        #        harvest_flags = self.config.get('harvest_flags', [])
        #        if harvest_flags:
        #            harvest_flag_list = list()
        #            for harvest_flag in harvest_flags:
        #                if harvest_flag['key']:
        #                    flag_value = harvest_flag['key']
        #                    if isinstance(flag_value, unicode):
        #                        harvest_flag_list.append(flag_value.encode('utf-8'))
        #                    elif isinstance(flag_value, str):
        #                        harvest_flag_list.append(flag_value)
        #            if len(harvest_flag_list) > 0:
        #                ors = str()
        #                if len(fq_terms) > 0:
        #                    ors = ' OR '
        #                fq_terms.append(ors+'harvest_flag:('+' OR '.join(harvest_flag_list)+')')

        testflags = self.config.get('testflags', [])
        if testflags:
            testflag_list = list()
            for testflag in testflags:
                if isinstance(testflag,  six.binary_type):  # six.text_type):  # unicode
                    testflag_list.append(testflag.decode('utf-8'))
                    # testflag_list.append(testflag.encode('utf-8'))  # encode('utf-8')でbyte変換
                elif isinstance(testflag, str):
                    testflag_list.append(testflag)
            if len(testflag_list) > 0:
                if testflag_list[0] != 'all':  # 「all」は「testflg」の値を確認せずデータセットを全て取得
                    ors = str()
                    if len(fq_terms) > 0:
                        ors = ' AND '
                    if testflag_list[0] == 'none':
                        # 「none」は「testflag」の値が設定されていないデータセットを取得する
                        fq_terms.append(ors + '-testflg:*')
                    else:
                        # 「通常」「訓練」「試験」の設定時は一致する「testflg」のデータセットを取り込む
                        fq_terms.append(ors + 'testflg:(' + ' OR '.join(testflag_list) + ')')

        harvestflgs = self.config.get('harvestflgs', [])
        if harvestflgs:
            harvestflg_list = list()
            for harvestflg in harvestflgs:
                if isinstance(harvestflg,  six.binary_type):  # six.text_type):  # unicode
                    harvestflg_list.append(harvestflg.decode('utf-8'))
                elif isinstance(harvestflg, str):
                    harvestflg_list.append(harvestflg)
            if len(harvestflg_list) > 0:
                if 'SPF' in harvestflg_list:
                    ors = str()
                    if len(fq_terms) > 0:
                        ors = ' AND '

                    fq_terms.append(ors + 'harvestflg:(' + ' OR '.join(harvestflg_list) + ')')
                else:
                    return []


        # include_private
        include_private = self.config.get('include_private', False)
        # Fall-back option - request all the datasets from the remote CKAN
        pkg_dicts = list()
        if get_all_packages:
            # Request all remote packages
            try:
                pkg_dicts = self._search_for_datasets(remote_ckan_base_url,
                                                      fq_terms, include_private)
            except SearchError as e:
                log.error('Searching for all datasets gave an error: %s', e)
                self._save_gather_error(
                    'Unable to search remote SIP4D CKAN for datasets:%s url:%s'
                    'terms:%s' % (e, remote_ckan_base_url, fq_terms),
                    harvest_job)
                return None
            except Exception as e:
                log.error('Searching for all datasets gave an error: %s', e)
                self._save_gather_error(
                    'Unable to search remote SIP4D CKAN for datasets:%s url:%s'
                    'terms:%s' % (e, remote_ckan_base_url, fq_terms),
                    harvest_job)
                return None

        if not pkg_dicts or len(pkg_dicts) == 0:
            self._save_gather_error(
                'No datasets found at SIP4D CKAN: %s' % remote_ckan_base_url,
                harvest_job)
            return []

        # Create harvest objects for each dataset
        try:
            query = model.Session.query(HarvestObject.guid, HarvestObject.package_id). \
                filter(HarvestObject.current is True). \
                filter(HarvestObject.harvest_source_id == harvest_job.source.id)
            guid_to_package_id = {}

            for guid, package_id in query:
                guid_to_package_id[guid] = package_id

            guids_in_db = set(guid_to_package_id.keys())

            dataset_id_list = set()
            for pkg_dict in pkg_dicts:
                if 'id' in pkg_dict and pkg_dict['id']:
                    if pkg_dict['id'] in dataset_id_list:
                        continue
                    dataset_id_list.add(pkg_dict['id'])

            new_dataset = dataset_id_list - guids_in_db
            update_dataset = guids_in_db & dataset_id_list
            package_ids = set()
            object_ids = list()
            # 新規作成
            for dataset_id in new_dataset:
                dataset = None
                for pkg_dict in pkg_dicts:
                    if pkg_dict['id'] == dataset_id:
                        dataset = pkg_dict
                        break
                if dataset:
                    # is_harvest_flag = True
                    is_testflag = True
                    # if harvest_flags:
                    if testflags:
                        # is_harvest_flag = self.check_harvest_flag(harvest_flags=harvest_flags, pkg_dict=dataset)
                        is_testflag = self.check_testflag(testflags=testflags, pkg_dict=dataset)
                    # if is_harvest_flag:
                    if is_testflag:
                        package_ids.add(dataset_id)
                        log.debug('CKAN(SIP4D) Creating HarvestObject for %s', dataset['name'])
                        obj = HarvestObject(guid=dataset_id, job=harvest_job,
                                            content=json.dumps(dataset),
                                            extras=[HarvestObjectExtra(key='status', value='create')])
                        obj.save()
                        object_ids.append(obj.id)

                    is_harvestflg = True
                    if harvestflgs:
                        is_harvestflg = self.check_harvestflg(harvestflgs=harvestflgs, pkg_dict=dataset)
                    if is_harvestflg:
                        package_ids.add(dataset_id)
                        log.debug('CKAN(SIP4D) Creating HarvestObject for %s', dataset['name'])
                        obj = HarvestObject(guid=dataset_id, job=harvest_job,
                                            content=json.dumps(dataset),
                                            extras=[HarvestObjectExtra(key='status', value='create')])
                        obj.save()
                        object_ids.append(obj.id)

            # 更新
            for dataset_id in update_dataset:
                dataset = None
                for pkg_dict in pkg_dicts:
                    if pkg_dict['id'] == dataset_id:
                        dataset = pkg_dict
                        break
                if dataset:
                    # is_harvest_flag = True
                    is_testflag = True
                    # if harvest_flags:
                    if testflags:
                        # is_harvest_flag = self.check_harvest_flag(harvest_flags=harvest_flags, pkg_dict=dataset)
                        is_testflag = self.check_testflag(testflags=testflags, pkg_dict=dataset)
                    # if is_harvest_flag:
                    if is_testflag:
                        package_ids.add(dataset_id)
                        existing_package_dict = self._find_existing_package(dataset)
                        is_dataset_update = False
                        if existing_package_dict:
                            if not 'metadata_modified' in dataset or \
                                    dataset['metadata_modified'] > existing_package_dict.get('metadata_modified'):
                                is_dataset_update = True
                            elif 'state' in existing_package_dict and existing_package_dict['state'] == 'deleted':
                                is_dataset_update = True
                        # print ('dataset update: %s' % str(is_dataset_update))
                        if is_dataset_update:
                            log.debug('CKAN(SIP4D) Update HarvestObject for %s, pid %s', dataset['name'],
                                      guid_to_package_id[dataset_id])
                            obj = HarvestObject(guid=dataset_id, job=harvest_job,
                                                package_id=guid_to_package_id[dataset_id],  # mod add
                                                content=json.dumps(dataset),
                                                extras=[HarvestObjectExtra(key='status', value='update')])
                            obj.save()
                            object_ids.append(obj.id)

                    is_harvestflg = True
                    if harvestflgs:
                        is_harvestflg = self.check_harvestflg(harvestflgs=harvestflgs, pkg_dict=dataset)
                    if is_harvestflg:
                        package_ids.add(dataset_id)
                        existing_package_dict = self._find_existing_package(dataset)
                        is_dataset_update = False
                        if existing_package_dict:
                            if not 'metadata_modified' in dataset or \
                                    dataset['metadata_modified'] > existing_package_dict.get('metadata_modified'):
                                is_dataset_update = True
                            elif 'state' in existing_package_dict and existing_package_dict['state'] == 'deleted':
                                is_dataset_update = True
                        if is_dataset_update:
                            log.debug('CKAN(SIP4D) Update HarvestObject for %s, pid %s', dataset['name'],
                                      guid_to_package_id[dataset_id])
                            obj = HarvestObject(guid=dataset_id, job=harvest_job,
                                                package_id=guid_to_package_id[dataset_id],  # mod add
                                                content=json.dumps(dataset),
                                                extras=[HarvestObjectExtra(key='status', value='update')])
                            obj.save()
                            object_ids.append(obj.id)

            # 削除
            delete_dataset = guids_in_db - package_ids
            for dataset_id in delete_dataset:
                log.debug('CKAN(SIP4D) Delete HarvestObject for %s, pid %s', dataset_id,
                          guid_to_package_id[dataset_id])
                obj = HarvestObject(guid=dataset_id, job=harvest_job,
                                    package_id=guid_to_package_id[dataset_id],  # mod
                                    extras=[HarvestObjectExtra(key='status', value='delete')])
                model.Session.query(HarvestObject). \
                    filter_by(guid=dataset_id). \
                    update({'current': False}, False)
                obj.save()
                object_ids.append(obj.id)

            return object_ids
        except Exception as e:
            self._save_gather_error('%r' % str(e), harvest_job)

    def check_harvest_flag(self, harvest_flags, pkg_dict):
        pkg_register_status = False
        if len(harvest_flags) > 0:
            ex_flag = get_pkg_dict_extra(pkg_dict, 'harvest_flag', None)
            if ex_flag:
                ex_flag_list = ex_flag.split(',')
                for harvest_flag in harvest_flags:
                    if harvest_flag['key']:
                        harvest_flag_val = harvest_flag['key']
                        for ex_flag_val in ex_flag_list:
                            if harvest_flag_val == ex_flag_val:
                                pkg_register_status = True
                                break
                        if pkg_register_status:
                            break

        return pkg_register_status

    def check_testflag(self, testflags, pkg_dict):
        pkg_register_status = False
        if len(testflags) > 0:
            if testflags[0] == 'all':
                # 「all」は「testflag」の値を確認せずデータセットを全て取得
                pkg_register_status = True
            else:
                ex_flag = get_pkg_dict_extra(pkg_dict, 'testflg', None)
                if ex_flag:
                    # 「通常」「訓練」「試験」の設定時は一致する「testflag」のデータセットを取り込む
                    for testflag in testflags:
                        if testflag == ex_flag:
                            pkg_register_status = True
                            break
                else:
                    if testflags[0] == 'none':
                        # 「none」は「testflg」の値が設定されていないデータセットを取得する
                        pkg_register_status = True

        return pkg_register_status

    def check_harvestflg(self, harvestflgs, pkg_dict):
        pkg_register_status = False
        ex_flag = get_pkg_dict_extra(pkg_dict, 'harvestflg', None)
        if ex_flag:
            for harvestflg in harvestflgs:
                if harvestflg == ex_flag:
                    pkg_register_status = True
                    break

        return pkg_register_status

    def _search_for_datasets(self, remote_ckan_base_url, fq_terms=None, include_private=False):
        base_search_url = remote_ckan_base_url + self._get_search_api_offset()
        params = {'rows': '100', 'start': '0', 'sort': 'id asc'}
        if fq_terms:
            params['fq'] = ' '.join(fq_terms)

        if include_private:
            params['include_private'] = 'true'

        pkg_dicts = []
        pkg_ids = set()
        previous_content = None
        while True:
            url = base_search_url + '?' + urlencode(params)
            log.debug('Searching for CKAN datasets: %s', url)
            try:
                content = self._get_content(url)
            except ContentFetchError as e:
                raise SearchError(
                    'Error sending request to search remote '
                    'CKAN instance %s using URL %r. Error: %s' %
                    (remote_ckan_base_url, url, e))

            if previous_content and content == previous_content:
                raise SearchError('The paging doesn\'t seem to work. URL: %s' %
                                  url)
            try:
                response_dict = json.loads(content)
            except ValueError:
                raise SearchError('Response from remote CKAN was not JSON: %r'
                                  % content)
            try:
                pkg_dicts_page = response_dict.get('result', {}).get('results',
                                                                     [])
            except ValueError:
                raise SearchError('Response JSON did not contain '
                                  'result/results: %r' % response_dict)

            # Weed out any datasets found on previous pages (should datasets be
            # changing while we page)
            ids_in_page = set(p_item['id'] for p_item in pkg_dicts_page)
            duplicate_ids = ids_in_page & pkg_ids
            if duplicate_ids:
                pkg_dicts_page = [page for page in pkg_dicts_page
                                  if page['id'] not in duplicate_ids]
            pkg_ids |= ids_in_page

            pkg_dicts.extend(pkg_dicts_page)

            if len(pkg_dicts_page) == 0:
                break

            params['start'] = str(int(params['start']) + int(params['rows']))

        return pkg_dicts

    def fetch_stage(self, harvest_object):
        return True

    def import_stage(self, harvest_object):
        log.debug('In Sip4dHarvester import_stage')

        base_context = {'model': model, 'session': model.Session,
                        'user': self._get_user_name()}
        if not harvest_object:
            log.error('No harvest object received')
            return False

        status = self._get_object_extra(harvest_object, 'status')
        if status == 'delete':
            try:
                # Delete package
                context = {'model': model, 'session': model.Session,
                           'user': self._get_user_name(), 'ignore_auth': True}
                result = p.toolkit.get_action('package_delete')(context, {'id': harvest_object.package_id})
                log.info('Deleted package {0} with guid {1}'.format(harvest_object.package_id,
                                                                    harvest_object.guid))
                return True
            except NotAuthorized:
                log.error('403 Unauthorized to delete package ')
                return False
            except NotFound:
                log.error('404 Dataset not found')
                return False

        if harvest_object.content is None:
            self._save_object_error('Empty content for object %s' %
                                    harvest_object.id,
                                    harvest_object, 'Import')
            return False

        self._set_config(harvest_object.job.source.config)

        try:
            package_dict = json.loads(harvest_object.content)

            if package_dict.get('type') == 'harvest':
                log.warn('Remote dataset is a harvest source, ignoring...')
                return True

            # Set default tags if needed
            default_tags = self.config.get('default_tags', [])
            if default_tags:
                if 'tags' not in package_dict:
                    package_dict['tags'] = []
                package_dict['tags'].extend(
                    [t for t in default_tags if t not in package_dict['tags']])

            remote_groups = self.config.get('remote_groups', None)
            if remote_groups not in ('only_local', 'create'):
                # Ignore remote groups
                package_dict.pop('groups', None)
            else:
                if 'groups' not in package_dict:
                    package_dict['groups'] = []

                # check if remote groups exist locally, otherwise remove
                validated_groups = []

                for group_ in package_dict['groups']:
                    try:
                        try:
                            if 'id' in group_:
                                data_dict = {'id': group_['id']}
                                group = get_action('group_show')(base_context.copy(), data_dict)
                            else:
                                raise NotFound

                        except NotFound as e:
                            if 'name' in group_:
                                data_dict = {'id': group_['name']}
                                group = get_action('group_show')(base_context.copy(), data_dict)
                            else:
                                raise NotFound
                        # Found local group
                        validated_groups.append({'id': group['id'], 'name': group['name']})

                    except NotFound as e:
                        log.info('Group %s is not available', group_)
                        if remote_groups == 'create':
                            try:
                                group = self._get_group(harvest_object.source.url, group_)
                            except RemoteResourceError:
                                log.error('Could not get remote group %s', group_)
                                continue

                            for key in ['packages', 'created', 'users', 'groups', 'tags', 'extras', 'display_name']:
                                group.pop(key, None)

                            get_action('group_create')(base_context.copy(), group)
                            log.info('Group %s has been newly created', group_)
                            validated_groups.append({'id': group['id'], 'name': group['name']})

                package_dict['groups'] = validated_groups

            # Local harvest source organization
            source_dataset = get_action('package_show')(base_context.copy(), {'id': harvest_object.source.id})

            local_org = source_dataset.get('owner_org')

            remote_orgs = self.config.get('remote_orgs', None)

            if remote_orgs not in ('only_local', 'create'):
                # Assign dataset to the source organization
                package_dict['owner_org'] = local_org
            else:
                if 'owner_org' not in package_dict:
                    package_dict['owner_org'] = None

                # check if remote org exist locally, otherwise remove
                validated_org = None
                remote_org = package_dict['owner_org']

                if remote_org:
                    try:
                        data_dict = {'id': remote_org}
                        org = get_action('organization_show')(base_context.copy(), data_dict)
                        validated_org = org['id']

                    except NotFound as e:
                        log.info('Organization %s is not available', remote_org)
                        if remote_orgs == 'create':
                            try:
                                try:
                                    org = self._get_organization(harvest_object.source.url, remote_org)
                                except RemoteResourceError:
                                    # fallback if remote CKAN exposes organizations as groups
                                    # this especially targets older versions of CKAN
                                    org = self._get_group(harvest_object.source.url, remote_org)

                                for key in ['packages', 'created', 'users', 'groups', 'tags', 'extras', 'display_name',
                                            'type']:
                                    org.pop(key, None)
                                get_action('organization_create')(base_context.copy(), org)

                                log.info('Organization %s has been newly created', remote_org)
                                # mod
                                if org['image_display_url']:
                                    log.info('Copy image file %s', org['image_display_url'])
                                    image_url = org['image_display_url']
                                    if isinstance(image_url, six.binary_type):  # unicode
                                        image_url = image_url.decode('utf-8')
                                    self._get_organization_thumb(image_url)

                                validated_org = org['id']
                            except (RemoteResourceError, ValidationError):
                                log.error('Could not get remote org %s', remote_org)

                package_dict['owner_org'] = validated_org or local_org

            # Set default groups if needed
            default_groups = self.config.get('default_groups', [])
            if default_groups:
                if 'groups' not in package_dict:
                    package_dict['groups'] = []
                existing_group_ids = [g['id'] for g in package_dict['groups']]
                package_dict['groups'].extend(
                    [g for g in self.config['default_group_dicts']
                     if g['id'] not in existing_group_ids])
            # Set default extras if needed
            default_extras = self.config.get('default_extras', {})

            def get_extra(extra_key, extra_package_dict):
                for extra in extra_package_dict.get('extras', []):
                    if extra['key'] == extra_key:
                        return extra

            if default_extras:
                override_extras = self.config.get('override_extras', False)
                if 'extras' not in package_dict:
                    package_dict['extras'] = []
                for key, value in default_extras.items():  # iteritems()
                    existing_extra = get_extra(key, package_dict)
                    if existing_extra and not override_extras:
                        continue  # no need for the default
                    if existing_extra:
                        package_dict['extras'].remove(existing_extra)
                    # Look for replacement strings
                    if isinstance(value, six.string_types):  # basestring
                        value = value.format(
                            harvest_source_id=harvest_object.job.source.id,
                            harvest_source_url=harvest_object.job.source.url.strip('/'),
                            harvest_source_title=harvest_object.job.source.title,
                            harvest_job_id=harvest_object.job.id,
                            harvest_object_id=harvest_object.id,
                            dataset_id=package_dict['id'])

                    package_dict['extras'].append({'key': key, 'value': value})

            harvestmode = self.config.get('harvestmode', None)
            if harvestmode == 'append':
                try:
                    local_dataset = get_action('package_show')(base_context.copy(), {'id': package_dict.get('id')})
                    if len(local_dataset) > 0:
                        for local_extra in local_dataset['extras']:
                            local_extra_key = local_extra['key']
                            local_extra_value = local_extra['value']
                            if get_extra(local_extra_key, package_dict) is None:
                                package_dict['extras'].append({'key': local_extra_key, 'value': local_extra_value})
                                log.debug('save :' + local_extra_key)
                except Exception as e:
                    log.debug(e.message)
            else:
                log.debug('extras over write')

            for resource in package_dict.get('resources', []):
                # Clear remote url_type for resources (eg datastore, upload) as
                # we are only creating normal resources with links to the
                # remote ones
                resource.pop('url_type', None)

                # Clear revision_id as the revision won't exist on this CKAN
                # and saving it will cause an IntegrityError with the foreign
                # key.
                resource.pop('revision_id', None)

            result = self._sip4d_create_or_update_package(
                package_dict, harvest_object, package_dict_form='package_show')

            if result == 'unchanged':
                log.info('harvest_object is unchanged, %s' % harvest_object.guid)

            return result
        except ValidationError as e:
            self._save_object_error('Invalid package with GUID %s: %r' %
                                    (harvest_object.guid, e.error_dict),
                                    harvest_object, 'Import')
        except Exception as e:
            self._save_object_error('%s' % e, harvest_object, 'Import')


class ContentFetchError(Exception):
    pass


class ContentNotFoundError(ContentFetchError):
    pass


class RemoteResourceError(Exception):
    pass


class SearchError(Exception):
    pass
