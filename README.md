# ckanext-sip4d
 SIP4D-CKAN用のCKAN拡張モジュールです。CKAN v2.9以上で使用してください。CKAN v2.10.0は未対応です。ckanext-harvest, chanext-spatialの後にckanext-sip4dをインストールしてください。

## Requirements
CKAN2.9.*
ckanext-harvest  
ckanext-spatial  
の環境で動作を確認しています。

## Installation
1.  パッケージの配置:  
ckanext-sip4dパッケージをckanをインストールした仮想環境下のパス（本手順書では/usr/lib/ckan/default/src/とする）に配置します。

        mv　ckanext-sip4d /usr/lib/ckan/default/src/

2.  仮想環境のactivate:

        . /usr/lib/ckan/default/bin/activate
      
3.  ckanext-sip4dインストール:

        cd /usr/lib/ckan/default/src/ckanext-sip4d
        pip install -e ./

4.  動作に必須のパッケージインストール

        pip install -r requirements.txt

5.  CKANのコンフィグファイル（本手順書では/etc/ckan/default/ckan.iniとする）のckan.pluginsに追加します。

        ckan.plugins = sip4ddata sip4dview sip4dharvest sip4d_arcgis_harvest

6.  CKANを再起動して設定を反映します。

## Configuration

CKANの画面表示の権限確認設定  
Trueを設定するとゲストユーザは画面表示を行えません。

        ckanext.sip4d.guests_ban = true

トップページに表示するサイト名設定

        ckanext.sip4d.site_title = SIP4D-CKAN

トップページに表示するロゴのパス設定

        ckanext.sip4d.logo_path = /images/logo_SIP4D-CKAN_01.svg

トップページに表示するロゴの幅(%)設定

        ckanext.sip4d.logo_width_percent　= 55

デフォルトのデータフォルダのID設定

        ckanext.sip4d_organization_id = sip4d

デフォルトのデータフォルダの名称設定

        ckanext.sip4d_organization_title = SIP4D

高度な検索フォームの表示設定

        ckanext.sip4d.show_search_div_flag = true

高度な検索の項目設定  
検索対象の属性ID:画面に表示する属性名を半角スペースで区切ります。

        ckanext.sip4d.search_item_list =　id1:name1 id2:name2

データセット一覧画面で表示するサムネイル画像の幅(px)設定

        ckanext.sip4d.thumbnail_width = 140

データセット一覧画面で表示するサムネイル画像の高さ(px)設定

        ckanext.sip4d.thumbnail_height = 140