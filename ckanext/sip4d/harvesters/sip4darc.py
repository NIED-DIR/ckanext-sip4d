# encoding: utf-8

import datetime
import logging
import re
import socket
import sys
import time
import uuid
import json

import pycrs
import pyproj
import requests
import six
from six.moves.http_client import HTTPException
from six.moves.urllib.error import URLError, HTTPError
from six.moves.urllib.parse import urlencode
from six.moves.urllib.request import Request, urlopen

from ckanext.harvest.interfaces import IHarvester
from ckanext.harvest.model import HarvestObject
from ckanext.harvest.model import HarvestObjectExtra
from ckanext.sip4d.harvesters.base import AESCipher
from ckanext.sip4d.harvesters.base import Sip4DHarvesterBase

import ckan.lib.helpers as h
import ckan.plugins as p
from ckan import model
from ckan.common import config
from ckan.lib.navl.dictization_functions import Invalid
from ckan.logic import NotAuthorized
from ckan.logic import ValidationError, NotFound, get_action
from ckan.logic.validators import email_validator
from ckan.plugins.core import SingletonPlugin, implements

log = logging.getLogger(__name__)


class Sip4DArcGISHarvester(Sip4DHarvesterBase, SingletonPlugin):

    implements(IHarvester)

    config = None

    force_import = False

    api_version = 2
    action_api_version = 3

    def info(self):
        return {
            'name': 'sip4d_arcgis',
            'title': 'ArcGIS Online Harvester',
            'description': p.toolkit._('Harvests dataset from remote ArcGISOnline'),
            'form_config_interface': 'Text'
        }

    dataset_headers = [
        'title',
        'name',  # idを利用
        'notes',
        'tags',
        'license_id',
        'owner_org',
        'thumbnail',  # thumbnailのurl生成を確認
        'private',
        'url',
        # 'version',
        'author',
        'author_email',
        # 'author_mailform',
        'maintainer',
        'maintainer_email',
        # 'maintainer_mailform',
        'spatial',
        # 'information_date'
        'disaster_name',
        # 'disaster_id',
        'language',
        #
        'metadata_created',
        'metadata_modified',
        'copyright'
    ]

    def getArcGisParams(self, token, ext_params):
        params = {'f': 'json'}
        if token:
            params['token'] = token
        if ext_params:
            for key in ext_params:
                params[key] = ext_params[key]
        return params

    # ArcGIS Rest Login
    def loginArcGIS(self, url, username, password):
        token_url = url + '/sharing/rest/generateToken'
        password = self.getDecrypt(password)
        ext_params = {'referer': url}
        if username:
            ext_params['username'] = username
        if password:
            ext_params['password'] = password
        params = self.getArcGisParams(token=None, ext_params=ext_params)
        return self.getJsonResponse(token_url, params)

    def getArcGisResponseToken(self, token_json):
        if token_json and 'token' in token_json:
            return token_json['token']
        return None

    # ArcGIS Rest Get UserInfo
    def getArcGisUser(self, url, token, username):
        if username:
            rest_url = url + '/sharing/rest/community/users/' + username
            ext_params = {'username': username, 'expiration': 30}
            params = self.getArcGisParams(token=token, ext_params=ext_params)
            return self.getJsonResponse(rest_url, params)
        return None

    # ArcGIS Rest Search User
    def findArcGisUserByName(self, url, token, username):
        rest_url = url + '/sharing/rest/community/users'
        ext_params = {'q': username}
        params = self.getArcGisParams(token=token, ext_params=ext_params)
        return self.getJsonResponse(rest_url, params)

    # get User's GroupList
    def getArcGisGroupList(self, userJson):
        if 'groups' in userJson:
            return userJson['groups']
        return None

    # Get GroupId
    def getArcGisGroupId(self, user_json, group_name):
        if 'groups' in user_json:
            group_list = user_json['groups']
            for group in group_list:
                if 'title' not in group:
                    continue
                group_title = group['title']
                if group_title == group_name:
                    return group['id']
        else:
            return None

    # ArcGIS Rest Group Info
    def getArcGisGroupInfo(self, url, token, group_id):
        rest_url = url + '/sharing/rest/community/groups/' + group_id
        params = self.getArcGisParams(token=token, ext_params=None)
        return self.getJsonResponse(rest_url, params)

    # ArcGIS Rest Group's Items
    def searchArcGisGroupItems(self, url, token, group_id):
        rest_url = url + '/sharing/rest/search'
        ext_params = {'q': 'group:' + group_id,
                      'bbox': '',
                      'start': 1,
                      'num': 100,
                      'sortField': 'title',
                      'sortOrder': 'asc'
                      }
        params = self.getArcGisParams(token=token, ext_params=ext_params)
        items = list()
        start = 1
        count = 0
        while True:
            if count > 1000:  # 10万件で停止
                break
            result_json = self.getJsonResponse(rest_url, params)
            if 'results' in result_json and isinstance(result_json['results'], list):
                items = items + result_json['results']

            if 'nextStart' in result_json:
                if result_json['nextStart'] == -1:
                    break
                else:
                    start = result_json['nextStart']
            params['start'] = start
            time.sleep(0.1)  # arcgisonline 504 error?
            count += 1
        return items

    # ArcGIS Rest User's Folder List
    def getArcGisFolderList(self, url, token):
        username = self.config.get('username')
        rest_url = url + '/sharing/rest/content/users/' + username
        params = self.getArcGisParams(token=token, ext_params=None)
        return self.getJsonResponse(rest_url, params)

    # Get FolderID
    def getArcGisFolderId(self, contents_json, folder_name):
        if contents_json and 'folders' in contents_json:
            folder_list = contents_json['folders']
            if folder_list:
                for folder in folder_list:
                    if 'title' not in folder:
                        continue
                    folder_title = folder['title']
                    if folder_title == folder_name:
                        return folder['id']
        else:
            return None

    # ArcGIS Rest Folder's Items
    def getArcGisFolderItems(self, url, token, folder_id):
        username = self.config.get('username')
        rest_url = url + '/sharing/rest/content/users/' + username + '/' + folder_id
        params = self.getArcGisParams(token=token, ext_params=None)
        folder_json = self.getJsonResponse(rest_url, params)
        if 'items' in folder_json:
            return folder_json['items']
        return None

    # convert ArcGIS REST Item to CKAN Dataset
    def convertItemToDataset(self, url, token, items, _type, _name, _id):
        '''
        ArcGIS Onlineから取得したJSON形式のアイテムをCKANのデータセットの対応するフィールドに入力する
        :param url:
        :param token:
        :param items:
        :param _type:
        :param _name:
        :param _id:
        :return:
        '''
        # access 公開設定 publicのみprivate false
        if items is None:
            return None

        # license_list
        context = {'model': model, 'session': model.Session, 'user': self._get_user_name()}
        license_list = p.toolkit.get_action('license_list')(context, {})
        # organization_list dict()
        organization_list = p.toolkit.get_action('organization_list_for_user')(context, {})

        log.info('arcgis rest items.size: %s' % str(len(items)))
        # 返却用のdataset list
        dataset_list = list()
        owner_list = list()
        # itemの変換
        for item in items:
            dataset = dict()
            extras = list()
            resources = list()
            # itemClassName = type(item).__name__
            # print('ItemClass: ' + itemClassName + ' ' + item['title'])
            # elements の構築
            for _header in self.dataset_headers:
                try:
                    if _header == "title":
                        # ISUTサイト（ArcGIS Online）のコンテンツ（レイヤ等）のタイトルを挿入する
                        if 'title' in item:
                            dataset[_header] = item['title']

                    elif _header == "name":
                        # 2-100文字の英数小文字で設定するデータセットの一意の名前、記号は「-_」が利用できる。

                        # ISUTサイト（ArcGIS Online）のコンテンツ（レイヤ等）のIDを挿入する
                        # （IDはユニークなUUIDであり、32文字の英数小文字である）
                        if 'id' in item:
                            dataset[_header] = item['id']
                            dataset['id'] = item['id']

                    elif _header == "notes":
                        # 情報の概要説明　Markdown形式の記述が可能。
                        # 次の項目について可能な限り簡素な説明を記述すること。
                        # １）目的、想定する利用方法を記述する
                        # ２）データの作成方法について記述する
                        # ３）データを利用する上での注意事項を記述する
                        # ４）必要であれば用語の説明を記述する
                        # ５）特殊なライセンスの場合、ライセンスについて記述する

                        # ISUTサイト（ArcGIS Online）のコンテンツの説明部分に記載されている内容を挿入する
                        if 'description' in item:
                            dataset[_header] = item['description']

                    elif _header == "tags":
                        # 検索タグJSONオブジェクトの配列で複数記述可能。
                        # 例:[{"state": "active","name": "タグ1"}, {"state": "active","name": "タグ2"}]

                        # ISUTサイト（ArcGIS Online）側で設定されているタグを挿入する
                        if 'tags' in item:
                            tags = item['tags']
                            tag_list = list()
                            if tags and isinstance(tags, list):
                                re_compile = re.compile(
                                    u'[!"#$%&\'\\\\()*+/:;<=>?@[\\]^_`|~「」〔〕“”〈〉『』【】＆＊・（）＄＃＠。、？！｀＋￥％　]')
                                for tag_name in tags:
                                    # -_.',{} 利用可能な記号
                                    tag_name = re.sub(re_compile, u'_', tag_name).replace(' ', '-')
                                    if len(tag_name) < 2:  # 2文字未満は登録できない
                                        tag_name = tag_name + u"_"
                                    tag_item = {'state': 'active', 'name': tag_name, 'display_name': tag_name}
                                    tag_list.append(tag_item)
                            if tag_list:
                                dataset[_header] = tag_list

                    elif _header == "license_id":
                        # http:// FQDN /api/action/license_list
                        # CKANのAPIを利用して取得するライセンス一覧から、登録する以下のライセンスのidを取得して記述する。
                        # ・GNU Free Documentation License
                        # ・Open Data Commons Attribution License
                        # ・Open Data Commons Open Database License
                        # ・Open Data Commons Public Domain Dedication and License
                        # ・UK Open Govemment License
                        # ・その他（オープンライセンス）
                        # ・その他（パブリックドメイン）
                        # ・その他（表示）
                        # ・その他（非オープンライセンス）
                        # ・その他（非商用）
                        # ・クリエイティブ・コモンズCCO
                        # ・クリエイティブ・コモンズ表示
                        # ・クリエイティブ・コモンズ表示　継承
                        # ・クリエイティブ・コモンズ非商用
                        # ・ライセンス未指定
                        # ・独自利用規約
                        # （参照：http://opendefinition.org/licenses/）
                        if 'licenseInfo' in item and item['licenseInfo']:
                            package_license = None
                            package_license_title = None
                            if license_list:
                                for license_info in license_list:
                                    if item['licenseInfo'].lower() == license_info.get('id') \
                                            or item['licenseInfo'].lower() == license_info.get('url'):
                                        package_license = license_info.get('id')
                                        package_license_title = license_info.get('title')
                                        break
                            # ISUTサイト（ArcGIS Online）側から利用規約に記述されている文言を挿入する
                            if package_license:
                                dataset[_header] = package_license
                                if package_license_title:
                                    dataset['license_title'] = package_license_title
                            else:
                                dataset[_header] = 'notspecified'
                                # extrasに追加
                                license_info = {'key': 'license_note', 'value': item['licenseInfo']}
                                extras.append(license_info)
                        else:
                            dataset[_header] = 'notspecified'
                        # print('license id : %s' % dataset[_header])

                    elif _header == "owner_org":
                        # http:// FQDN /api/action/organization_list_for_user
                        # CKANのAPIで取得される組織一覧から、登録する組織のnameを取得して記述する。
                        # configのorganization_nameを利用する
                        organization_name = self.config.get('organization_name', None)
                        if organization_name:
                            is_organization = False
                            for organization in organization_list:
                                if organization['title'] == organization_name \
                                        or organization['name'] == organization_name \
                                        or organization['id'] == organization_name:
                                    dataset[_header] = organization['id']
                                    dataset['organization'] = organization
                                    is_organization = True
                                    break
                            if not is_organization:
                                dataset[_header] = organization_name

                    elif _header == "private":
                        # 公開・非公開フラグ。以下より選択
                        # True: プライベート
                        # False: パブリック

                        # コンテンツのアクセスレベルがpublicの場合にパブリック、
                        # private/shared/orgの場合にプライベートとする。
                        public = item['access'] == "public"
                        private = public is False  # public == False
                        dataset[_header] = private

                    elif _header == "url":
                        # ソースのＵＲＬ　例：http://example.com/dataset.json
                        # ・リソースを配信している組織のＨＰのＵＲＬ等
                        # ・リソースが２次加工であれば、オリジナルデータを配信しているＨＰのＵＲＬ等

                        # ISUTサイト（ArcGIS Online）側から出力されるコンテンツのURLを挿入する
                        # url or sourceURLの利用
                        source_url = None
                        url_list = list()
                        if 'sourceUrl' in item:
                            source_url = item['sourceUrl']
                            if source_url:
                                dataset[_header] = source_url
                                url_list.append(source_url)
                        if 'url' in item:
                            if source_url is None:
                                dataset[_header] = item['url']
                            if item['url']:
                                url_list.append(item['url'])

                        # FIXME type,typeKeywords
                        # title,type,urlからresourceの作成,typeKeywordは確認
                        for item_url in url_list:
                            resource_title = item['title'] if 'title' in item else None
                            resource_type = item['type'] if 'type' in item else None
                            resource = {'url': item_url}
                            if resource_title:
                                resource['name'] = resource_title
                            if resource_type:
                                resource['format'] = resource_type
                            resources.append(resource)

                    elif _header == "version":
                        # 該当項目なし
                        dataset[_header] = None

                    elif _header == "author":
                        # 作成者（人名もしくは組織名）
                        # 例：防災科研

                        # ISUTサイト（ArcGIS Online）で登録されている所有者情報を挿入する
                        author_user = self.config.get('author_user', None)
                        if author_user:
                            dataset[_header] = author_user
                        else:
                            if 'owner' in item and item['owner']:
                                dataset[_header] = item['owner']
                        # if 'owner' in item and item['owner']:
                        #     dataset[_header] = item['owner']
                        # else:
                        #     author_user = self.config.get('author_user', None)
                        #     if author_user:
                        #         dataset[_header] = author_user

                    elif _header == "author_email":
                        # 作成者のｅメールアドレス（URLの記述は禁止）
                        # 例：sip4d-catalog@bosai.go.jp

                        # ISUTサイト（ArcGIS Online）で登録されている所有者のメールアドレスを挿入する
                        owner_email = None
                        author_email = self.config.get('author_email', None)
                        if author_email:
                            owner_email = author_email
                        else:
                            if 'owner' in item and item['owner']:
                                owner = None
                                for targetOwner in owner_list:
                                    # print ('targetUser: %s' %targetOwner['username'])
                                    if 'username' in targetOwner and targetOwner['username'] == item['owner']:
                                        owner = targetOwner
                                        break
                                if owner is None:
                                    owner = self.getArcGisUser(url, token, item['owner'])
                                    owner_list.append(owner)
                                owner_email = owner['email'] if owner is not None and 'email' in owner else None

                        if owner_email:
                            try:
                                email_validator(owner_email, None)
                                dataset[_header] = owner_email
                            except Invalid:
                                # author_mailform
                                author_mailform = {'key': 'author_mailform', 'value': owner_email}
                                extras.append(author_mailform)

                    elif _header == "author_mailform":
                        # 作成者のメールフォームのＵＲＬ（オプション）
                        # 該当項目なし 出力不要
                        # dataset.append(self.ignoreUnicodeEncodeError(None))
                        pass
                    elif _header == "maintainer":
                        # メンテナー（人名もしくは組織名）
                        # 例：防災科研

                        # 該当項目なし configで設定する
                        maintainer_user = self.config.get('maintainer_user', None)
                        if maintainer_user:
                            dataset[_header] = maintainer_user

                    elif _header == "maintainer_email":
                        # メンテナーのｅメールアドレス（URLの記述は禁止）
                        # 例：sip4d-catalog@bosai.go.jp
                        # 該当項目なし　configで設定する
                        maintainer_email = self.config.get('maintainer_email', None)
                        if maintainer_email:
                            try:
                                email_validator(maintainer_email, None)
                                dataset[_header] = maintainer_email
                            except Invalid:
                                # maintainer_mailform
                                maintainer_mailform = {'key': 'maintainer_mailform', 'value': maintainer_email}
                                extras.append(maintainer_mailform)

                    elif _header == "maintainer_mailform":
                        # メンテナーのメールフォームのＵＲＬ（オプション）
                        # 該当項目なし 出力不要
                        # dataset.append(self.ignoreUnicodeEncodeError(None))
                        pass
                    elif _header == "spatial":
                        # 地理空間の検索範囲を指定する。
                        # 例：{
                        #       "type": "Polygon",
                        #       "coordinates": [[
                        #                        [136.7365, 34.721214],
                        #                        [136.7365, 35.305708],
                        #                        [137.432091, 35.305708],
                        #                        [137.432091, 34.721214],
                        #                        [136.7365, 34.721214]
                        #                      ]]
                        #     }

                        # 範囲情報 (extent) [[minX, minY],[maxX, maxY]]
                        # からPolygonを構築して挿入する。
                        try:
                            if 'extent' in item:
                                extent = item['extent']
                                if extent is not None and 2 <= len(extent):
                                    minX = extent[0][0]
                                    minY = extent[0][1]
                                    maxX = extent[1][0]
                                    maxY = extent[1][1]

                                    # 座標値が-180,-90,180,90の範囲を超えていた場合の動作
                                    is_transform = False
                                    if minX < -180 or minX > 180:
                                        is_transform = True
                                    elif minY < -90 or minY > 90:
                                        is_transform = True
                                    elif maxX < -180 or maxX > 180:
                                        is_transform = True
                                    elif maxY < -90 or maxY > 90:
                                        is_transform = True

                                    if is_transform is False:
                                        coordinates = [[
                                            [minX, minY],
                                            [minX, maxY],
                                            [maxX, maxY],
                                            [maxX, minY],
                                            [minX, minY]
                                        ]]
                                    else:
                                        log.debug("transform extent:"+item['id'])
                                        coordinates = self.transformExtent(item=item, token=token,
                                                                           minx=minX, miny=minY, maxx=maxX, maxy=maxY)
                                    if coordinates:
                                        spatial = {"type": "Polygon", "coordinates": coordinates}
                                        spatial_item = {'key': 'spatial',
                                                        'value': h.json.dumps(spatial)}  # ,ensure_ascii=False
                                        extras.append(spatial_item)
                        except RuntimeError as e:
                            logging.exception(e)

                    elif _header == "information_date":
                        # データが対象としている日時をUTCで登録する。
                        # 書式例：2018-10-11T10:41:49.186303
                        # 該当項目なし
                        # 将来的には、タイトルの日付文字列、またはタグに
                        # 「情報日時2019/02/21」のようなタグから情報日時を取得する。
                        pass
                    elif _header == "disaster_name":
                        # 災害名
                        # メタデータ一覧を取得する際に設定したフォルダもしくはグループ名を挿入する
                        # configにdisaster_nameが設定されている場合、こちらを利用する。

                        disaster_name = self.config.get('disaster_name', None)
                        if disaster_name:
                            disaster_extra = {'key': 'disaster_name', 'value': disaster_name}
                            extras.append(disaster_extra)
                        # else:
                        #     if _name:
                        #         disaster_extra = {'key': 'disaster_name', 'value': _name}
                        #         extras.append(disaster_extra)

                    elif _header == "disaster_id":
                        # 災害ID
                        # CKAN側で災害IDを一括入力するため出力は不要。
                        # 将来的には、CKANがシステムを横断したユニークな災害IDを管理する。
                        # dataset[_header] = None
                        # if _disaster_id:
                        #    disaster_name = {'key':'disaster_id', 'value':_disaster_id}
                        #    extras.append(disaster_name)
                        pass
                    elif _header == "language":
                        # 記述言語 RFC3066で記述　日本語は「ja」
                        # 固定値で「ja」とする。（languagesは空のため）
                        site_lang = config.get('ckan.locale_default', 'ja')
                        language = {'key': 'language', 'value': site_lang}
                        extras.append(language)

                    elif _header == "type":
                        # dataset.append(self.ignoreUnicodeEncodeError(_type))
                        pass
                    elif _header == "folderid":
                        # dataset.append(self.ignoreUnicodeEncodeError(_id))
                        pass
                    elif _header == "folder":
                        # dataset.append(self.ignoreUnicodeEncodeError(_name))
                        pass
                    elif _header == "created":
                        # timestamp = datetime.datetime.fromtimestamp(item.created / 1000)
                        # dataset.append(self.ignoreUnicodeEncodeError(timestamp))
                        pass
                    elif _header == "modified":
                        # timestamp = datetime.datetime.fromtimestamp(item.modified / 1000)
                        # dataset.append(self.ignoreUnicodeEncodeError(timestamp))
                        pass
                    elif _header == "modified_number":
                        # dataset.append(self.ignoreUnicodeEncodeError(item.modified))
                        pass
                    elif _header == "metadata_created":
                        if 'created' in item:
                            timestamp = datetime.datetime.fromtimestamp(item['created'] / 1000)
                            if timestamp:
                                # dataset[_header] = timestamp
                                datetime_str_format = '%Y-%m-%d %H:%M:%S'
                                dataset[_header] = timestamp.strftime(datetime_str_format)
                    elif _header == "metadata_modified":
                        if 'modified' in item:
                            timestamp = datetime.datetime.fromtimestamp(item['modified'] / 1000)
                            if timestamp:
                                # dataset[_header] = timestamp
                                datetime_str_format = '%Y-%m-%d %H:%M:%S'
                                dataset[_header] = timestamp.strftime(datetime_str_format)
                    elif _header == "thumbnail":
                        if 'thumbnail' in item:
                            thumbnail = item['thumbnail']
                            if thumbnail:
                                thumbnail_url = url + '/sharing/rest/content/items/' + item['id'] + "/info/" + item[
                                    'thumbnail'] + "?w=400"  # &token=token
                                resource = {'name': 'thumbnail.png', 'format': 'PNG', "url": thumbnail_url}
                                resources.append(resource)
                        else:
                            # dataset.append(self.ignoreUnicodeEncodeError(item[_header]))
                            pass
                    elif _header == "copyright":
                        # accessInformation
                        if 'accessInformation' in item:
                            copyright = item['accessInformation']
                            if copyright:
                                # copyright_extra = {'key': 'copyright', 'value': copyright}
                                copyright_extra = {'key': 'credit', 'value': copyright}
                                extras.append(copyright_extra)
                    # elif _header == "shared_with":
                    #     try:
                    #         dataset.append(self.ignoreUnicodeEncodeError(item.shared_with))
                    #     except RuntimeError as e:
                    #         logging.exception(e)
                    #         dataset.append('item.shared_with RuntimeError')
                    # elif _header == "shared_with_everyone":
                    #     dataset.append(self.ignoreUnicodeEncodeError(item.shared_with['everyone']))
                    # elif _header == "shared_with_org":
                    #     dataset.append(self.ignoreUnicodeEncodeError(item.shared_with['org']))
                    # elif _header == "shared_with_groups":
                    #     shared_with_group = '|' if 0 < len(item.shared_with['groups']) else None
                    #     try:
                    #         for index, group in enumerate(item.shared_with['groups']):
                    #             shared_with_group += ('|' if index == 0 else '')
                    #             shared_with_group += group.id + ':' + group.title + '(owner:' + group.owner + ')'
                    #         dataset.append(self.ignoreUnicodeEncodeError(shared_with_group))
                    #     except RuntimeError as e:
                    #         logging.exception(e)
                    #         dataset.append('item.shared_with_groups RuntimeError')
                except (TypeError, ValueError) as e:
                    exc_type, exc_obj, tb = sys.exc_info()
                    lineno = tb.tb_lineno
                    print(str(lineno) + ":" + str(type(e)))
                    log.error('ArcGIS Rest Item convert Error: {0}'.format(e))
                except Exception as e:
                    exc_type, exc_obj, tb = sys.exc_info()
                    lineno = tb.tb_lineno
                    print(str(lineno) + ":" + str(type(e)))
                    log.error('ArcGIS Rest Item convert Exception: {0}'.format(e))
            if extras:
                dataset['extras'] = extras
            if resources:
                dataset['resources'] = resources
            dataset_list.append(dataset)
        return dataset_list

    # 全件検索
    def getAllDatasetList(self, remote_rest_base_url, arcgis_user, token):
        dataset_list = list()
        # group+folder+folder.none
        arcgis_grouplist = self.getArcGisGroupList(arcgis_user)
        for arcgis_group in arcgis_grouplist:
            arcgis_group_name = arcgis_group['title']
            arcgis_group_id = arcgis_group['id']
            # グループ毎にアイテム取得
            if arcgis_group_id:
                group_list = self.searchArcGisGroupItems(remote_rest_base_url, token, arcgis_group_id)
                if group_list:
                    group_dataset_list = self.convertItemToDataset(remote_rest_base_url, token, group_list,
                                                                   'Group', arcgis_group_name, arcgis_group_id)
                    if group_dataset_list:
                        dataset_list = dataset_list + group_dataset_list
        # folder
        arcgis_folderlist = self.getArcGisFolderList(remote_rest_base_url, token)
        if arcgis_folderlist:
            # フォルダー未登録アイテム
            if 'items' in arcgis_folderlist:
                arcgis_folder_none_list = arcgis_folderlist['items']
                if arcgis_folder_none_list:
                    folder_dataset_list = self.convertItemToDataset(remote_rest_base_url, token,
                                                                    arcgis_folder_none_list,
                                                                    'Folder', '', '')
                    dataset_list = dataset_list + folder_dataset_list
            # フォルダー毎のアイテム取得
            if 'folders' in arcgis_folderlist:
                arcgis_folders = arcgis_folderlist['folders']
                if arcgis_folders:
                    for arcgis_folder in arcgis_folders:
                        if 'id' in arcgis_folder:
                            folder_items = self.getArcGisFolderItems(remote_rest_base_url, token, arcgis_folder['id'])
                            folder_dataset_list = self.convertItemToDataset(remote_rest_base_url, token, folder_items,
                                                                            'Folder', arcgis_folder['title'],
                                                                            arcgis_folder['id'])
                            if folder_dataset_list:
                                dataset_list = dataset_list + folder_dataset_list
        return dataset_list

    # グループ取得
    def getGroupDatasetList(self, remote_rest_base_url, arcgis_user, token, groups):
        dataset_list = list()
        for group_name in groups:
            arcgis_groupid = self.getArcGisGroupId(arcgis_user, group_name)
            # group items
            if arcgis_groupid:
                group_list = self.searchArcGisGroupItems(remote_rest_base_url, token, arcgis_groupid)
                if group_list:
                    group_dataset_list = self.convertItemToDataset(remote_rest_base_url, token, group_list,
                                                                   'Group', group_name, arcgis_groupid)
                    if group_dataset_list:
                        dataset_list = dataset_list + group_dataset_list
        return dataset_list

    # フォルダー取得
    def getFolderDatasetList(self, remote_rest_base_url, arcgis_user, token, folders, arcgis_folderlist):
        dataset_list = list()
        for folder_name in folders:
            arcgis_folderid = ''
            folder_items = list()
            if folder_name == 'None':
                if 'items' in arcgis_folderlist:
                    folder_items = arcgis_folderlist['items']
            else:
                if 'folders' in arcgis_folderlist:
                    arcgis_folderid = self.getArcGisFolderId(arcgis_folderlist, folder_name)
                    if arcgis_folderid:
                        folder_items = self.getArcGisFolderItems(remote_rest_base_url, token, arcgis_folderid)
            if folder_items:
                folder_dataset_list = self.convertItemToDataset(remote_rest_base_url, token, folder_items,
                                                                'Folder', folder_name, arcgis_folderid)
                if folder_dataset_list:
                    dataset_list = dataset_list + folder_dataset_list
        return dataset_list

    def getDatasetFromName(self, dataset_list, name):
        for dataset in dataset_list:
            if 'name' in dataset and dataset['name'] == name:
                return dataset
        return None

    # extentが-180~180,-90~90の範囲外の場合座標変換
    def transformExtent(self, item, token, minx, miny, maxx, maxy):
        # urlからprojection取得
        req_url = None
        if 'sourceUrl' in item:
            req_url = item['sourceUrl']
        if req_url is None and 'url' in item:
            req_url = item['url']
        if req_url:
            params = self.getArcGisParams(token=token, ext_params=None)
            try:
                # urlから情報を取得後、座標系情報を確認
                response = requests.post(req_url, params)
                response_item = None
                if response.status_code == 200:
                    response_item = response.json()
                if response_item:  # wktをパース後, projを利用して座標変換
                    for item_key in ('spatialReference', 'initialExtent', 'fullExtent'):
                        wkt_item = None
                        if item_key is 'spatialReference' and item_key in response_item:
                            wkt_item = response_item[item_key]
                        elif item_key in response_item:
                            if response_item[item_key] and 'spatialReference' in response_item[item_key]:
                                wkt_item = response_item[item_key]['spatialReference']
                        if isinstance(wkt_item, dict):
                            wkt = wkt_item['wkt'] if 'wkt' in wkt_item else None
                            # print wkt
                            epsg_base = None
                            if wkt is not None:
                                if isinstance(wkt, six.binary_type):  # unicode
                                    wkt = wkt.decode('UTF-8')
                                try:
                                    esri_wkt = pycrs.parse.from_ogc_wkt(wkt)  # esri wkt
                                    epsg_base = pyproj.Proj(esri_wkt.to_proj4())
                                except Exception:
                                    log.error("WKT Projection Parse Error %s" % wkt)
                                    epsg_base = pyproj.Proj(wkt)
                            else:
                                wkid = wkt_item['wkid'] if 'wkid' in wkt_item else None
                                if wkid:
                                    try:
                                        epsg_base = pyproj.Proj("+init=EPSG:"+str(wkid))
                                    except Exception:
                                        latestWkid = wkt_item['latestWkid'] if 'latestWkid' in wkt_item else None
                                        if latestWkid:
                                            epsg_base = pyproj.Proj("+init=EPSG:" + str(latestWkid))
                            if epsg_base:
                                epsg_4612 = pyproj.Proj("+init=EPSG:4612")
                                t_minx, t_miny = pyproj.transform(epsg_base, epsg_4612, minx, miny)
                                t_maxx, t_maxy = pyproj.transform(epsg_base, epsg_4612, maxx, maxy)
                                return [[
                                    [t_minx, t_miny],
                                    [t_minx, t_maxy],
                                    [t_maxx, t_maxy],
                                    [t_maxx, t_miny],
                                    [t_minx, t_miny]
                                ]]
            except Exception as e:
                log.error("Extent transform Error {0}".format(e))
        return None

    # def ignoreUnicodeEncodeError(self, _obj):
    #    # Windows標準出力するときにCP932に変換できない場合があるので、ignoreオプションでencodeしてからdecodeで戻す
    #    if _obj is None:
    #        return ''
    #    return str(_obj).encode('cp932','ignore').decode('CP932')

    def getJsonResponse(self, url, values):
        try:
            data = urlencode(values)
            if not isinstance(data, six.binary_type):
                data = data.encode('utf-8')
            http_request = Request(url, data)
            http_response = urlopen(http_request)
            contentsJson = h.json.loads(http_response.read())
            return contentsJson
        except HTTPError as e:
            if e.getcode() == 404:
                raise ContentNotFoundError('HTTP error: %s' % str(e.code))
            else:
                raise ContentFetchError('HTTP error: %s' % str(e.code))
        except URLError as e:
            raise ContentFetchError('URL error: %s' % e.reason)
        except HTTPException as e:
            raise ContentFetchError('HTTP Exception: %s' % e.reason)
        except socket.error as e:
            raise ContentFetchError('HTTP socket error: %s' % e.reason)
        except Exception as e:
            exc_type, exc_obj, tb = sys.exc_info()
            lineno = tb.tb_lineno
            print(str(lineno) + ":" + str(type(e)))
            raise ContentFetchError('HTTP general exception: %s' % e.reason)

    # config str to json
    def _set_config(self, config_str):
        if config_str:
            self.config = h.json.loads(config_str)
        else:
            self.config = {}

    def validate_config(self, source_config):
        try:
            if not source_config:
                raise ValueError('No configuration settings')

            config_obj = h.json.loads(source_config)

            # orgnaization,mainter
            if 'organization_name' in config_obj:
                if not isinstance(config_obj['organization_name'], six.text_type) \
                        and not isinstance(config_obj['organization_name'], str):  # unicode
                    raise ValueError('organization_name must be a str')

            if 'author_user' in config_obj:
                if not isinstance(config_obj['author_user'], six.text_type) \
                        and not isinstance(config_obj['author_user'], str):  # unicode
                    raise ValueError('author_user must be a unicode')

            if 'author_email' in config_obj and config_obj['author_email']:
                try:
                    email_valid = email_validator(config_obj['author_email'], None)
                    if email_valid is None:
                        raise ValueError('The format of the author_email address is not correct')
                except Invalid:
                    raise ValueError('The format of the author_email address is not correct')

            if 'maintainer_user' in config_obj:
                if not isinstance(config_obj['maintainer_user'], six.text_type) \
                        and not isinstance(config_obj['maintainer_user'], str):  # unicode
                    raise ValueError('maintainer_user must be a unicode')

            if 'maintainer_email' in config_obj and config_obj['maintainer_email']:
                try:
                    email_valid = email_validator(config_obj['maintainer_email'], None)
                    if email_valid is None:
                        raise ValueError('The format of the maintainer_email address is not correct')
                except Invalid:
                    raise ValueError('The format of the maintainer_email address is not correct')

            if 'disaster_name' in config_obj:
                if not isinstance(config_obj['disaster_name'], six.text_type) \
                        and not isinstance(config_obj['disaster_name'], str):  # unicode
                    raise ValueError('disaster_name must be a unicode')

            # groups, folders, user, password
            if 'groups' in config_obj:
                if not isinstance(config_obj['groups'], list):
                    raise ValueError('groups must be a list')

            if 'folders' in config_obj:
                if not isinstance(config_obj['folders'], list):
                    raise ValueError('folders must be a list')

            if 'all' in config_obj:
                if not isinstance(config_obj['all'], bool):
                    raise ValueError('all must be True or False')

            if 'username' in config_obj:
                if not isinstance(config_obj['username'], six.text_type):  # unicode
                    raise ValueError('username must be a str')

            if 'password' in config_obj:
                if not isinstance(config_obj['password'], six.text_type):  # unicode
                    raise ValueError('password must be a str')
            # password encrypt
            if 'username' in config_obj and 'password' in config_obj:
                try:
                    config_obj = h.json.loads(source_config)
                    password = self.getEncrypt(config_obj['password'])
                    config_obj['password'] = password
                    source_config = h.json.dumps(config_obj, ensure_ascii=False,
                                                 encoding='utf8', indent=2, sort_keys=True)
                except Exception as e:
                    # print e
                    raise ValueError('password encrypt error')

        except ValueError as e:
            raise e

        return source_config

    def getEncrypt(self, password):
        if password and not password.startswith('PHRASE_'):
            pass_phrase = self.getPassPhrase()
            if pass_phrase:
                cipher = AESCipher(pass_phrase)
                return 'PHRASE_' + cipher.encrypt(password)
        return password

    def getDecrypt(self, encrypt_text):
        if encrypt_text and encrypt_text.startswith('PHRASE_'):
            pass_phrase = self.getPassPhrase()
            if pass_phrase:
                encrypt_text = encrypt_text[7:]
                cipher = AESCipher(pass_phrase)
                return cipher.decrypt(encrypt_text)
        return encrypt_text

    def getPassPhrase(self):
        pass_phrase = config.get("ckanext.sip4d.pass_phrase", None)
        if not pass_phrase or len(pass_phrase) == 0:
            return None  # pass_phrase = '9emQludST3S7Sia9VyE9oQ9xdGeyHAeJ'  # 32文字
        if len(pass_phrase) < 32:
            while True:
                pass_phrase = pass_phrase + pass_phrase
                if len(pass_phrase) > 32:
                    break
        return pass_phrase[0:32]

    def gather_stage(self, harvest_job):

        context = {'model': model, 'session': model.Session,
                   'user': self._get_user_name()}

        log.debug('In SIP4D ArcGIS Rest Harvester gather_stage (%s)',
                  harvest_job.source.url)
        p.toolkit.requires_ckan_version(min_version='2.0')

        self._set_config(harvest_job.source.config)
        # Get source URL
        remote_rest_base_url = harvest_job.source.url.rstrip('/')

        # データセット一覧
        dataset_list = list()
        # 登録時確認用nameリスト
        dataset_name_list = set()
        try:
            # login ArcGIS REST username, password
            username = self.config.get('username')
            password = self.config.get('password')
            token_json = self.loginArcGIS(remote_rest_base_url, username=username, password=password)
            if token_json is None:
                log.error('This user cannot log in ArcGIS Server')
                # return
            token = self.getArcGisResponseToken(token_json)
            # print token

            if token is None:
                log.error('Unable to get ArcGis token')
                return
            # user
            username = self.config.get('username', None)
            if username is None:
                # log.error('ArcGIS Username not found')
                # return
                pass

            arcgis_user = self.getArcGisUser(remote_rest_base_url, token, username)
            if arcgis_user is None:
                log.error('ArcGIS User not found')
                return
            # all
            if 'all' in self.config and self.config['all']:
                log.debug('sip4darc harvest, gather_stage, target all')
                # group+folder+folder.none
                dataset_list = self.getAllDatasetList(remote_rest_base_url, arcgis_user=arcgis_user, token=token)
            else:
                # group
                if 'groups' in self.config:
                    groups = self.config['groups']
                    if len(groups) > 0:
                        log.debug('sip4darc harvest, gather_stage, target groups %s' % ','.join(groups))
                    group_dataset_list = self.getGroupDatasetList(remote_rest_base_url, arcgis_user=arcgis_user,
                                                                  token=token,
                                                                  groups=groups)
                    if group_dataset_list:
                        dataset_list = dataset_list + group_dataset_list
                # folder
                if 'folders' in self.config:
                    folders = self.config['folders']
                    if len(folders) > 0:
                        log.debug('sip4darc harvest, gather_stage, target folders %s' % ','.join(folders))
                    arcgis_folderlist = self.getArcGisFolderList(remote_rest_base_url, token)
                    folder_dataset_list = self.getFolderDatasetList(remote_rest_base_url, arcgis_user=arcgis_user,
                                                                    token=token,
                                                                    folders=folders,
                                                                    arcgis_folderlist=arcgis_folderlist)
                    if folder_dataset_list:
                        dataset_list = dataset_list + folder_dataset_list
            for dataset in dataset_list:
                # print(json.dumps(dataset))
                if 'name' in dataset:
                    dataset_name = dataset['name']
                    if dataset_name in dataset_name_list:
                        continue
                    else:
                        dataset_name_list.add(dataset_name)
            # Filter in/out datasets from particular organizations
        except ContentFetchError as e:
            print(e)
            log.error('There was a problem accessing ArcGIS Rest server ContentFetchError')
            return
        except Exception as e:
            print(e)
            log.error('There was a problem accessing ArcGIS Rest server Exception')
            return

        if not dataset_list or len(dataset_list) == 0:
            self._save_gather_error(
                'No datasets found at ArcGIS Online: %s' % remote_rest_base_url,
                harvest_job)
            return []

        # 登録更新削除チェック
        try:
            query = model.Session.query(HarvestObject.guid, HarvestObject.package_id). \
                filter(HarvestObject.current is True). \
                filter(HarvestObject.harvest_source_id == harvest_job.source.id)
            guid_to_package_id = {}

            for guid, package_id in query:
                guid_to_package_id[guid] = package_id

            guids_in_db = set(guid_to_package_id.keys())

            new_dataset = dataset_name_list - guids_in_db
            delete_dataset = guids_in_db - dataset_name_list
            update_dataset = guids_in_db & dataset_name_list
            object_ids = list()

            # 新規作成
            for dataset_name in new_dataset:
                dataset = self.getDatasetFromName(dataset_list, dataset_name)
                if dataset:
                    log.debug('ArcGis Rest Item Creating HarvestObject for %s', dataset['name'])
                    obj = HarvestObject(guid=dataset_name,
                                        job=harvest_job,
                                        content=h.json.dumps(dataset),
                                        extras=[HarvestObjectExtra(key='status', value='create')])
                    # FIXME flush warning
                    obj.save()
                    object_ids.append(obj.id)

            for dataset_name in update_dataset:
                dataset = self.getDatasetFromName(dataset_list, dataset_name)
                if dataset:
                    existing_package_dict = self._find_existing_package(dataset)
                    dataset_update_flg = False
                    if existing_package_dict:
                        if 'metadata_modified' not in dataset or \
                                dataset['metadata_modified'] > existing_package_dict.get('metadata_modified'):
                            dataset_update_flg = True
                        elif 'state' in existing_package_dict and existing_package_dict['state'] == 'deleted':
                            dataset_update_flg = True
                            # stateにactiveを設定
                            dataset['state'] = 'active'
                    # print ('dataset_update_flg: %s' % str(dataset_update_flg))
                    if dataset_update_flg:
                        log.debug('ArcGis Rest Item Update HarvestObject for %s, pid %s', dataset['name'],
                                  guid_to_package_id[dataset_name])
                        obj = HarvestObject(guid=dataset_name, job=harvest_job,
                                            package_id=guid_to_package_id[dataset_name],  # mod add
                                            content=h.json.dumps(dataset),
                                            extras=[HarvestObjectExtra(key='status', value='update')])
                        obj.save()
                        object_ids.append(obj.id)

            for dataset_name in delete_dataset:
                log.debug('ArcGis Rest Item Delete HarvestObject for %s, pid %s', dataset_name,
                          guid_to_package_id[dataset_name])
                obj = HarvestObject(guid=dataset_name, job=harvest_job,
                                    package_id=guid_to_package_id[dataset_name],  # mod
                                    extras=[HarvestObjectExtra(key='status', value='delete')])
                model.Session.query(HarvestObject). \
                    filter_by(guid=dataset_name). \
                    update({'current': False}, False)
                obj.save()
                object_ids.append(obj.id)

            return object_ids
        except Exception as e:
            self._save_gather_error('%r' % e.message, harvest_job)

    def fetch_stage(self, harvest_object):
        return True

    def import_stage(self, harvest_object):
        log.debug('In Sip4d ArcGIS Rest Harvester import_stage')

        context = {'model': model, 'session': model.Session,
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
            package_dict = h.json.loads(harvest_object.content)

            if package_dict.get('type') == 'harvest':
                log.warning('Remote dataset is a harvest source, ignoring...')
                return True

            # Local harvest source organization
            source_dataset = get_action('package_show')(context.copy(), {'id': harvest_object.source.id})
            local_org = source_dataset.get('owner_org')

            config_org = self.config.get('organization_name', None)

            if config_org is None:
                package_dict['owner_org'] = local_org
            else:
                # owner_org確認
                is_crate_organization = True
                if 'organization' in package_dict:
                    # organization確認
                    package_organization = package_dict['organization']
                    if 'title' in package_organization and package_organization['title'] == config_org:
                        # print 'is_crate_organization False'
                        is_crate_organization = False

                if is_crate_organization:
                    package_dict['owner_org'] = None
                    try:
                        data_dict = {}  # 'q': config_org
                        org_id = None
                        org_list = get_action('organization_list_for_user')(context.copy(), data_dict)
                        # print org_list
                        for org_item in org_list:
                            if org_item['title'] == config_org or org_item['id'] == config_org:
                                org_id = org_item['id']
                                break
                        if org_id:
                            package_dict['owner_org'] = org_id
                        else:
                            raise NotFound('not found remote org')

                    except NotFound as e:
                        try:
                            # create org
                            org = dict()
                            org['name'] = six.u(uuid.uuid4())
                            org['title'] = config_org
                            # org['image_url ']
                            for key in ['packages', 'created', 'users', 'groups', 'tags', 'extras', 'display_name',
                                        'type']:
                                org.pop(key, None)
                            create_organization = get_action('organization_create')(context.copy(), org)

                            log.info('Organization %s has been newly created', config_org)
                            # # サムネイル画像のダウンロード
                            # if org['image_display_url']:
                            #    log.info('Copy image file %s', org['image_display_url'])
                            #    image_url = org['image_display_url']
                            #    if isinstance(image_url, unicode):
                            #        image_url = image_url.encode('utf-8')
                            #    self._get_organization_thumb(image_url)
                            if create_organization:
                                package_dict['owner_org'] = create_organization['id']
                        except (RemoteResourceError, ValidationError):
                            log.error('Could not get remote org %s', config_org)
                            package_dict['owner_org'] = local_org
                if 'owner_org' not in package_dict or package_dict['owner_org'] is None:
                    package_dict['owner_org'] = local_org

            package_dict['state'] = 'active'
            result = self._create_or_update_package(
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
