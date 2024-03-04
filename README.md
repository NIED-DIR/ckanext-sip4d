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
### ckan.ini
CKANの画面表示の権限確認設定  
Trueを設定するとゲストユーザは画面表示を行えません。

        ckanext.sip4d.guests_ban = true

トップページに表示するサイト名設定

        ckanext.sip4d.site_title = SIP4D-CKAN

トップページに表示するロゴのパス設定

        ckanext.sip4d.logo_path = /images/logo_SIP4D-CKAN.svg

トップページに表示するロゴの幅(%)設定

        ckanext.sip4d.logo_width_percent　= 55

デフォルトのデータフォルダのID設定

        ckanext.sip4d_organization_id = sip4d

デフォルトのデータフォルダの名称設定

        ckanext.sip4d_organization_title = SIP4D

高度な検索フォームの表示設定

        ckanext.sip4d.show_search_div_flag = true

高度な検索の項目設定  
「検索対象の属性ID:画面に表示する属性名」を半角スペースで区切ります。

        ckanext.sip4d.search_item_list = title:タイトル notes:説明 author:著作者 notes:タグ

データセット一覧画面で表示するサムネイル画像の幅(px)設定

        ckanext.sip4d.thumbnail_width = 140px

データセット一覧画面で表示するサムネイル画像の高さ(px)設定

        ckanext.sip4d.thumbnail_height = 140px

データセット編集画面の地図画面の初期表示に利用する範囲設定  
四隅の緯度経度をカンマ区切りで設定します。

        ckanext.sip4d.dataset_map_extent = 123.135,23.24,157.76,51.51

### Solr
ckanext-sip4dは、extraで追加されたinformation_dateによるソートを行うために、Solrの設定を変更する必要があります。
    
    <field name="information_date" type="date" indexed="true" stored="true" />

        
## DataSet
SIP4D-CKANでは、extraで追加するメタデータを以下のように定義しています。

| メタデータ名 | 日本語ラベル名 | 説明 |
|:-----------|:------------|:------------|
| information_date | 情報更新日 | データセットの情報が更新された日付を入力します。 |
| testflg | フラグ | データセットの属性で、通常/訓練/試験のいずれかを入力します。ハーベストタイプ「SIP4D-CKAN Harvester」で参照されます。 |
| harvestflg | ハーベストフラグ | ハーベスト対象となるデータセットを指定します。ハーベストタイプ「SIP4D-CKAN Harvester」で参照されます。 |
| disaster_id | 災害ID | 災害情報のIDを入力します。|
| disaster_name | 災害名 | 災害情報の名称を入力します。|
| disaster_report |  報番号 | 災害情報の報番号を入力します。|
| credit |  クレジットタイトル | データセットのクレジット情報を入力します。|
| code |  情報種別コード | データセットの情報種別コードを入力します。|
| lgcode |  自治体コード | 地方公共団体コードの上5桁（6桁目は省略）を入力します。|

### サムネイル画像
データセットのサムネイル画像は、リソース名を「thumbnail.png」として、PNG画像のURLをリソースURLに設定することで表示されます。
## Harvest type
以下２種類のハーベストタイプが追加されます。

### SIP4D-CKAN Harvester
標準のハーベストに加えて、以下の機能が追加されています。
  1. 任意のデータセットをハーベスト対象とすることができます。  
      データセットのextraにharvestflgを追加し、値のキーワードを持つデータセットをハーベスト対象とします。  

  2. 手動で追加したメタデータがハーベストによって消えないようにするモードを設定できます。  
      標準のハーベスト処理は、ハーベスト元のデータセットをコピーします。そのため、コピーされたハーベスト先のデータセットを編集し、新たにメタデータを追加しても、次回のハーベストで上書きされて消えてしまいます。  
      このモードを有効にすると、手動で追加されたメタデータを保持しながら、ハーベストを実行します。

#### configuration
ハーベスト対象とするキーワードを列挙します。全てのデータセットをハーベスト対象とする場合は、空の配列を指定します。
    
    "harvestflags": ["keyword1", "keyword2", ...] or [],

ハーベストモードを指定します。"overwrite"は標準のハーベストモードです。"append"は手動で追加したメタデータを保持しながらハーベストを実行します。

    "harvestmode": "overwrite" or "append" , 

ハーベスト対象とするフラグを指定します。"none"はtestflgがないデータセットを対象とします。"all"は全てのtestflgを対象とします。
    
    "testflgs": ["通常","訓練", ...] or "none" or "all",

#### 設定例
        {
                "api_version": 3,
                "organizations_filter_include": ["test-org"],
                "harvestflgs": ["SPF"],
                "harvestmode" :"append",
                "testflgs":["all"]
        }


### ArcGIS Online Harvester
ArcGIS Onlineのデータをハーベストします。以下はArcGIS OnlineのREST-APIから取得されるItemのプロパティ名とCKANのメタデータ名の対応表です。

| ArcGIS | CKAN | 備考 |
|:-----------|:------------|:------------|
| title | title | タイトル|
| id | name | uuid |
| description | notes | 説明 |
| tags | tags | タグ |
| licenseInfo | license_title | ライセンス情報 |
| accessInformation | owner_org | CKANのAPIで取得される組織一覧から、登録する組織のnameを取得して記述する。ハーベストコンフィグのorganization_nameを利用する。 |
| access | private | コンテンツのアクセスレベルがpublicの場合にパブリック、private/shared/orgの場合にプライベートとする。|
| url | url | コンテンツのURL |
| owner | author | コンテンツの所有者 |
| owner.email | author_email | コンテンツの所有者のメールアドレス |
| extent | spatial |範囲情報[[minX, minY],[maxX, maxY]]からPolygonを構築して挿入する。|
|folder.name | disaster_name | 災害名としてAOGLのフォルダー名、グループ名を利用する。ハーベストコンフィグのdisaster_nameが設定されている場合はこちらを利用する。|
| created | metadata_created | メタデータの作成日 |
| modified | metadata_modified | メタデータの更新日 |
| thumbnail | リソース | リソースにthumbnail.pngを追加する。|
| accessInformation | copyright | 著作者情報 |

#### configuration
| パラメータ名 | 説明 |
|:-----------|:------------|
| organization_name | ハーベスト先の組織名収集したArcGISのアイテムを登録する、ローカルのCKANの組織のタイトルを設定します。組織が存在しない場合は新規作成します。|
| author_user | 収集したアイテムに作成者の名称を追加します。アイテムのownerに値がある場合はアイテムの値を優先します。|
| author_email | 収集したアイテムに作成者のメールアドレスを追加します。アイテムのowner.emailに値がある場合はアイテムの値を優先します。|
| maintainer_user | 収集したアイテムにメンテナーの名称を追加します。|
| maintainer_email | 収集したアイテムにメンテナーのメールアドレスを追加します。|
| username | ArcGIS Onlineのユーザ名を設定します。|
| password | ArcGIS Onlineのユーザのパスワードを設定します。CKANの設定iniファイルに「ckanext.sip4d.pass_phrase」の英数32文字が設定されている場合、パスワードを暗号化して保存します。|
| groups | ArcGISOnlineのグループを対象にアイテムの取得を行います。foldersの設定も同時に行えます。|
| folders | ArcGISOnlineのフォルダーを対象にアイテムの取得を行います。groupsの設定も同時に行えます。“None”を値に設定した場合、フォルダーに登録されていないアイテムの取得を行います。|
| all | trueを設定すると、ArcGISOnlineの全てのアイテムを対象にアイテムの取得を行います。groups,foldersの設定は無視されます。|


#### 設定例
    

    {
        "organization_name":"登録組織名",
        "author_user":"作成者",
        “author_email":"author@sample.com",
        "maintainer_user":"メンテナー",
        "maintainer_email":"maintainer@sample.com",
        "username": "arcgis_user",
        "password": "<ArcGIS USER PASSWORD>",
        "groups": ["グループの名称1","グループの名称2"],
        "folders": ["フォルダーの名称1","フォルダーの名称2",”None”],
        “all”: false
    }

