ckanext-sip4dのインストール手順
====

## selinux無効化
```
setenforce 0
vi /etc/selinux/config
--- 編集
SELINUX=disabled
---
```

## パッケージ追加
```
yum install -y wget
yum install -y git
yum install -y git-core
yum install -y java-1.8.0-openjdk
yum install -y subversion
yum install -y gcc
yum install -y gcc-c++
yum install -y make
yum install -y redis
yum install -y unzip
#yum install -y mercurial
#yum install -y supervisor
```
##　firewallのポート開放
```
firewall-cmd --permanent --add-service=http
firewall-cmd --permanent --add-service=https
#firewall-cmd --permanent --add-port=8983/tcp #solrを外部から確認する用
firewall-cmd --reload
firewall-cmd --list-all
```
***

## PostgreSQLインストール
### CentOS7 PostgreSQL9.6インストール 
```
mkdir /home/src
cd /home/src
wget https://download.postgresql.org/pub/repos/yum/reporpms/EL-7-x86_64/pgdg-redhat-repo-latest.noarch.rpm
rpm -ivh pgdg-redhat-repo-latest.noarch.rpm

yum -y install postgresql96-server postgresql96-devel postgresql96-contrib postgresql96
#db初期化
/usr/pgsql-9.6/bin/postgresql96-setup initdb
#conf編集
cp /var/lib/pgsql/9.6/data/pg_hba.conf /var/lib/pgsql/9.6/data/pg_hba.conf.org
cp /var/lib/pgsql/9.6/data/postgresql.conf /var/lib/pgsql/9.6/data/postgresql.conf.org
vi /var/lib/pgsql/9.6/data/pg_hba.conf
#---　一時的にtrustを設定
local   all             all                                     trust
host    all             all             127.0.0.1/32            trust
#---
vi /var/lib/pgsql/9.6/data/postgresql.conf
#---
listen_addresses = 'localhost'
port = 5432
max_connections = 256
work_mem = 4MB
#---
systemctl start postgresql-9.6.service
systemctl enable postgresql-9.6.service

#PostGIS 2.4インストール
yum -y install geos.x86_64 geos-devel.x86_64
yum -y install proj.x86_64 proj-devel.x86_64 proj-epsg.x86_64 proj-nad.x86_64 proj-debuginfo.x86_64
yum -y install --enablerepo=epel gdal.x86_64 gdal-devel.x86_64 gdal-libs.x86_64 gdal-doc.noarch
yum -y install postgis24_96
yum -y install postgis24_96-*
psql -U postgres -d template1 -f /usr/pgsql-9.6/share/contrib/postgis-2.4/postgis.sql
psql -U postgres -d template1 -f /usr/pgsql-9.6/share/contrib/postgis-2.4/spatial_ref_sys.sql
psql -U postgres -d template1 -c "SELECT postgis_full_version()"

#postgresユーザパスワード
passwd postgres

su - postgres
psql
#---
alter role postgres with password '****';
#---

vi /var/lib/pgsql/9.6/data/pg_hba.conf
#--- md5を設定
local   all             all                                     md5
host    all             all             127.0.0.1/32            md5
#---
systemctl restart postgresql-9.6.service
```

###　Oracle Linux利用時のPostgreSQLインストール
```
sudo dnf install oracle-epel-release-el8.x86_64
sudo dnf install https://download.postgresql.org/pub/repos/yum/reporpms/EL-8-x86_64/pgdg-redhat-repo-latest.noarch.rpm

sudo dnf config-manager --set-enabled ol8_codeready_builder
sudo dnf -qy module disable postgresql

sudo dnf search postgresql13
sudo dnf install postgresql13 postgresql13-devel postgresql13-server

sudo dnf install postgis32_13.x86_64 
sudo dnf install postgis32_13-devel.x86_64

sudo /usr/pgsql-13/bin/postgresql-13-setup initdb

sudo systemctl start postgresql-13
sudo systemctl enable postgresql-13
sudo systemctl status postgresql-13

su - postgres
psql -U postgres -f /usr/pgsql-13/share/contrib/postgis-3.2/postgis.sql template1
psql -U postgres -f /usr/pgsql-13/share/contrib/postgis-3.2/spatial_ref_sys.sql template1

cp /var/lib/pgsql/13/data/pg_hba.conf /var/lib/pgsql/13/data/pg_hba.conf.org
cp /var/lib/pgsql/13/data/postgresql.conf /var/lib/pgsql/13/data/postgresql.org

vi /var/lib/pgsql/13/data/pg_hba.conf
#---
local   all             all                                     trust
#---

vi /var/lib/pgsql/13/data/postgresql.conf
#---
listen_addresses = 'localhost'
#---

#postgresユーザパスワード
passwd postgres

su - postgres
psql
#---
alter role postgres with password '****';
#---

vi /var/lib/pgsql/13/data/pg_hba.conf
#---
local   all             all                                     md5
#---
```

### PostgreSQLインストール後の共通作業
```
#　PostgresqlにCKAN用のユーザ作成
su - postgres
createuser -S -D -R -P ckan_default
createuser -S -D -R -P -l datastore_default

#　CKAN用のDB作成
createdb -O ckan_default ckan_default -E utf-8
createdb -O datastore_default datastore_default -E utf-8

#　権限設定
psql -U postgres ckan_default
GRANT ALL ON DATABASE ckan_default TO ckan_default;
GRANT ALL ON geometry_columns TO ckan_default;
GRANT ALL ON spatial_ref_sys TO ckan_default;

psql -U postgres datastore_default
GRANT ALL ON DATABASE datastore_default TO ckan_default;
GRANT ALL ON geometry_columns TO ckan_default;
GRANT ALL ON spatial_ref_sys TO ckan_default;
GRANT ALL ON DATABASE datastore_default TO datastore_default;
GRANT ALL ON geometry_columns TO datastore_default;
GRANT ALL ON spatial_ref_sys TO datastore_default;
```
***

## python3 インストール
```
yum install -y https://repo.ius.io/ius-release-el7.rpm
yum install -y python36u python36u-libs python36u-devel python36u-pip
```
***
## CKANユーザ作成
```
useradd -m -s /sbin/nologin -d /usr/lib/ckan -c "CKAN User" ckan
```
## CKANインストールフォルダ作成
```
mkdir -p /usr/lib/ckan/default
chown -R ckan:ckan /usr/lib/ckan/default
mkdir -p /etc/ckan/default
chown ckan:ckan /etc/ckan/default
```
###  pipを最新に更新
```
pip3 install --upgrade pip
pip3 list
```

### venvでCKANの仮想環境を作成
```
python3 -m venv /usr/lib/ckan/default
chown -R ckan:ckan /usr/lib/ckan/default
#　activateできるか確認
. default/bin/activate
deactivate
. /usr/lib/ckan/default/bin/activate
deactivate
```

## CKANパッケージインストール
```
# activateして作業
su -s /bin/bash - ckan
. default/bin/activate

# CKANインストール用にsetuptoolsをバージョン指定でインストール
pip install setuptools==44.1.0
pip install --upgrade pip

#ckan 2.9.5インストール
pip install -e 'git+https://github.com/ckan/ckan.git@ckan-2.9.5#egg=ckan[requirements]'
# No matching distribution found for psycopg2==2.8.2
vi default/src/ckan/requirements.txt
#--- インストール途中で失敗するので修正してpip installを実行
psycopg2-binary==2.8.2
#psycopg2==2.8.2           # via -r requirements.in
#---
cd default/src/ckan
pip install -r requirements.txt
pip install -r dev-requirements.txt
pip install flask_debugtoolbar --upgrade
pip install -e ./
```
## ckan.iniファイル編集
```
#　ckan.iniファイル生成
ckan generate config /etc/ckan/default/ckan.ini

# ckan.iniを複製して編集
cp /etc/ckan/default/ckan.ini /etc/ckan/default/ckan.ini.org
vi /etc/ckan/default/ckan.ini
#---
sqlalchemy.url = postgresql://ckan_default:パスワード@localhost/ckan_default?sslmode=disable

ckan.datastore.write_url = postgresql://ckan_default:パスワード@localhost/datastore_default
ckan.datastore.read_url = postgresql://datastore_default:パスワード@localhost/datastore_default

ckan.site_url =https://server.domain.com

ckan.auth.create_user_via_web = false

solr_url = http://127.0.0.1:8983/solr/ckan

#CORS
#ckan.cors.origin_allow_all = false
#ckan.cors.origin_whitelist = https://***.***.** https://****.***.**

## Front-End Settings
ckan.site_title = SIP4D-CKAN
ckan.site_logo = /base/images/ckan-logo.png
ckan.site_description =SIP4D-CKAN

ckan.storage_path = /var/lib/ckan

## Internationalisation Settings
ckan.locale_default = ja
ckan.locale_order = ja en
ckan.locales_offered = ja en
ckan.locales_filtered_out = en_GB

# --------------------------------------
# ckanエクステンションインストール後に編集
ckan.plugins = stats text_view image_view recline_view harvest ckan_harvester dcat dcat_rdf_harvester dcat_json_harvester dcat_json_interface structured_data spatial_metadata spatial_query sip4ddata sip4dview sip4dharvest sip4d_arcgis_harvest

# ckanエクステンション用の設定
ckan.harvest.mq.type = redis

ckan.spatial.srid = 4326
ckan.spatial.default_map_extent = 123.135,23.24,157.76,51.51
ckanext.spatial.search_backend = solr
ckanext.spatial.use_postgis_sorting = true
ckanext.spatial.common_map.type = custom
ckanext.spatial.common_map.custom.url = https://cyberjapandata.gsi.go.jp/xyz/std/{z}/{x}/{y}.png
ckanext.spatial.common_map.attribution = Map tiles by <a href="http://www.gsi.go.jp" target="_blank">GSI</a>

ckanext.guests_ban = true

ckanext.sip4d.pass_phrase = 9emQludST3S7Sia9VyE9oQ9xdGeyHAeJ

ckanext.sip4d_organization_id = sip4d
ckanext.sip4d_organization_title = SIP4D
ckanext.sip4d.logo_path = /images/logo_SIP4D-CKAN_M.svg
ckanext.sip4d.logo_width_percent = 55

ckan.search.default_package_sort = metadata_modified desc
#---
```

## CKANストレージ設定
```
# permission対策
mkdir /var/lib/ckan
mkdir /var/lib/ckan/storage
mkdir /var/lib/ckan/resources
sudo chown -R apache:apache /var/lib/ckan
sudo chmod -R u+rwx /var/lib/ckan
sudo chmod -R 777 /var/lib/ckan
#SGIDビットを立てる
chmod 2770 /var/lib/ckan/storage/
```

## Apache Solrインストール
```
# log4j2の脆弱性があるため、インストール後に脆弱性対策を行う
# wget http://ftp.jaist.ac.jp/pub/apache/lucene/solr/7.7.2/solr-7.7.2.tgz
# tar xzvf solr-7.7.2.tgz
# cd solr-7.7.2/bin/
# ./install_solr_service.sh /root/install_ckan/solr-7.7.2.tgz

wget https://www.apache.org/dyn/closer.lua/lucene/solr/8.11.2/solr-8.11.2.tgz
tar zxvf solr-8.11.2.tgz
cd solr-8.11.2/bin
./install_solr_service.sh /home/src/solr-8.11.2.tgz

# solrユーザでckan用の設定追加
su solr
cd /opt/solr/bin/
./solr create -c ckan
exit

systemctl enable solr
#　solrが停止しない場合
cd /opt/solr/bin/
./solr stop
systemctl start solr

#CKAN solr設定
cp /var/solr/data/ckan/conf/solrconfig.xml /var/solr/data/ckan/conf/solrconfig.xml.org
cd /var/solr/data/ckan/conf/
chown solr:solr solrconfig.xml
chmod 664 solrconfig.xml
vi /var/solr/data/ckan/conf/solrconfig.xml
#---
#　<conofig>タグ内に追加
<schemaFactory class="ClassicIndexSchemaFactory"/>

#　こちらは削除
<!-- updateProcessor class="solr./AddSchemaFieldsUpdateProcessorFactory" name="add-schema-fields">
 </updateProcessor -->
<!-- updateRequestProcessorChain name="add-unknown-fields-to-the-schema" default="${update.autoCreateFields:true}"
</updateRequestProcessorChain -->
#<requestHandler name="/select" class="solr.SearchHandler">

#  <lst name="defaults">タグに追加
#    <str name="echoParams">explicit</str>
#    <int name="rows">10</int>
    <str name="df">text</str>
    <str name="q.op">AND</str>
#  </lst>
#---

# managed-schemaは削除
rm /var/solr/data/ckan/conf/managed-schema
ln -s /usr/lib/ckan/default/src/ckan/ckan/config/solr/schema.xml /var/solr/data/ckan/conf/schema.xml
# solr8ではschema.xmlがシンボリックリンクでは認識できない
cp /usr/lib/ckan/default/src/ckan/ckan/config/solr/schema.xml /var/solr/data/ckan/conf/schema.xml

cd /usr/lib/ckan/default/src/ckan/ckan/config/solr/
cp -p schema.xml schema.xml.org
vi schema.xml
#---  追加
    <fieldType name="text_ja" class="solr.TextField" positionIncrementGap="100" autoGeneratePhraseQueries="false">
      <analyzer type="index">
        <tokenizer class="solr.JapaneseTokenizerFactory" mode="search"/>
        <!--<tokenizer class="solr.JapaneseTokenizerFactory" mode="search" userDictionary="lang/userdict_ja.txt"/>-->
        <!-- Reduces inflected verbs and adjectives to their base/dictionary forms (辞書型) -->
        <filter class="solr.JapaneseBaseFormFilterFactory"/>
        <!-- Removes tokens with certain part-of-speech tags -->
        <filter class="solr.JapanesePartOfSpeechStopFilterFactory" tags="lang/stoptags_ja.txt" />
        <!-- Normalizes full-width romaji to half-width and half-width kana to full-width (Unicode NFKC subset) -->
        <filter class="solr.CJKWidthFilterFactory"/>
        <!-- Removes common tokens typically not useful for search, but have a negative effect on ranking -->
        <filter class="solr.StopFilterFactory" ignoreCase="true" words="lang/stopwords_ja.txt" />
        <!-- Normalizes common katakana spelling variations by removing any last long sound character (U+30FC) -->
        <filter class="solr.JapaneseKatakanaStemFilterFactory" minimumLength="4"/>
        <!-- Lower-cases romaji characters -->
        <filter class="solr.LowerCaseFilterFactory"/>
      </analyzer>
      <analyzer type="query">
        <tokenizer class="solr.JapaneseTokenizerFactory" mode="search"/>
        <!--<tokenizer class="solr.JapaneseTokenizerFactory" mode="search" userDictionary="lang/userdict_ja.txt"/>-->
        <!-- Reduces inflected verbs and adjectives to their base/dictionary forms (辞書型) -->
        <filter class="solr.JapaneseBaseFormFilterFactory"/>
        <!-- Removes tokens with certain part-of-speech tags -->
        <filter class="solr.JapanesePartOfSpeechStopFilterFactory" tags="lang/stoptags_ja.txt" />
        <!-- Normalizes full-width romaji to half-width and half-width kana to full-width (Unicode NFKC subset) -->
        <filter class="solr.CJKWidthFilterFactory"/>
        <!-- Removes common tokens typically not useful for search, but have a negative effect on ranking -->
        <filter class="solr.StopFilterFactory" ignoreCase="true" words="lang/stopwords_ja.txt" />
        <!-- Normalizes common katakana spelling variations by removing any last long sound character (U+30FC) -->
        <filter class="solr.JapaneseKatakanaStemFilterFactory" minimumLength="4"/>
        <!-- Lower-cases romaji characters -->
        <filter class="solr.LowerCaseFilterFactory"/>
      </analyzer>
    </fieldType>
#---
#---　string,textgenをtext_jaに編集
    <field name="id" type="string" indexed="true" stored="true" required="true" />
    <field name="title" type="text_ja" indexed="true" stored="true" />
    <field name="notes" type="text_ja" indexed="true" stored="true"/>
    <field name="author" type="text_ja" indexed="true" stored="true" />
    <field name="maintainer" type="textgen" indexed="true" stored="true" />
    <field name="res_name" type="text_ja" indexed="true" stored="true" multiValued="true" />
    <field name="res_description" type="text_ja" indexed="true" stored="true" multiValued="true"/>
    <field name="text" type="text_ja" indexed="true" stored="false" multiValued="true"/>
    <field name="urls" type="text_ja" indexed="true" stored="false" multiValued="true”/>
    <field name="depends_on" type="text_ja" indexed="true" stored="false" multiValued="true"/>
    <field name="dependency_of" type="text_ja" indexed="true" stored="false" multiValued="true"/>
    <field name="derives_from" type="text_ja" indexed="true" stored="false" multiValued="true”/>
    <field name="links_to" type="text_ja" indexed="true" stored="false" multiValued="true"/>
    <field name="linked_from" type="text_ja" indexed="true" stored="false" multiValued="true"/>
    <field name="child_of" type="text_ja" indexed="true" stored="false" multiValued="true"/>
    <field name="parent_of" type="text_ja" indexed="true" stored="false" multiValued="true”/>
    <dynamicField name="extras_*" type="text_ja" indexed="true" stored="true" multiValued="false”/>
    <dynamicField name="res_extras_*" type="text_ja" indexed="true" stored="true" multiValued="true"/>
#---
#---　以下はコメントアウト
<!-- defaultSearchField>text</defaultSearchField -->
<!-- solrQueryParser defaultOperator="AND"/ -->
#---

#solr-8.11以前をインストールした場合、log4j2の脆弱性対策として起動オプションに以下を追加して再起動
# vi /opt/solr/bin/solr
# #---
# -Dlog4j2.formatMsgNoLookups=true
# #---

# solr再起動
systemctl restart solr

#　redis起動
systemctl enable redis
systemctl start redis

# solrからのレスポンスを確認する
curl -s http://localhost:8983/solr/admin/cores?action=STATUS
```
***

## CKAN DB初期化
```
su -s /bin/bash - ckan
. default/bin/activate

# who.iniリンク
ln -s /usr/lib/ckan/default/src/ckan/who.ini /etc/ckan/default/who.ini

cd default/src/ckan/
ckan db init -c /etc/ckan/default/ckan.ini

deactivate
exit
```

## CKANインストール後の作業
```
su -s /bin/bash - ckan
. default/bin/activate

# CKANの組織をデータフォルダに書き換える設定
cd default/src/ckan
cp ckan/i18n/ja/LC_MESSAGES/ckan.po ckan/i18n/ja/LC_MESSAGES/ckan.po.org
sed -i -e "s/組織/データフォルダ/" ckan/i18n/ja/LC_MESSAGES/ckan.po
python setup.py compile_catalog -f --locale ja
python setup.py develop

# エラーで出た場合 2313行目付近の以下の行をコメントアウト
msgid_plural "Input is too short, must be at least %(num)d characters"
# CKANのsysadminユーザ登録
ckan -c /etc/ckan/default/ckan.ini sysadmin add admin email="***@***.**.**" 

# CKANの起動確認
# firewalldを停止するか、ポート5000を開けて確認する
# systemctl stop firewalld.service
ckan -c /etc/ckan/default/ckan.ini run

#　CKANの起動設定
# supervisorがインストールされていない場合、dnf install supervisor.noarch
# supervisorにCKANの起動設定を登録
vi /etc/supervisord.d/ckan-uwsgi.ini
#---
[program:ckan-uwsgi]

command=/usr/lib/ckan/default/bin/uwsgi -i /etc/ckan/default/ckan-uwsgi.ini

; Start just a single worker. Increase this number if you have many or
; particularly long running background jobs.
numprocs=1
process_name=%(program_name)s-%(process_num)02d

; Log files - change this to point to the existing CKAN log files
stdout_logfile=/var/log/nginx/uwsgi.OUT
stderr_logfile=/var/log/nginx/uwsgi.ERR

; Make sure that the worker is started on system start and automatically
; restarted if it crashes unexpectedly.
autostart=true
autorestart=true

; Number of seconds the process has to run before it is considered to have
; started successfully.
startsecs=10

; Need to wait for currently executing tasks to finish at shutdown.
; Increase this if you have very long running tasks.
stopwaitsecs = 600

; Required for uWSGI as it does not obey SIGTERM.
stopsignal=QUIT
#---
```
***

## nginx
```
# nginxインストール
yum install -y nginx.x86_64

# uwsgiインストール
su -s /bin/bash - ckan
. default/bin/activate
pip install wheel
pip install uwsgi

# wsgi.pyの移動
cp /usr/lib/ckan/default/src/ckan/wsgi.py /etc/ckan/default/

# ckan-uwsgi.ini編集
cp /usr/lib/ckan/default/src/ckan/ckan-uwsgi.ini /etc/ckan/default/
vi /etc/ckan/default/ckan-uwsgi.ini
#---　uid,guidをckanに書き換え
[uwsgi]
http            =  127.0.0.1:8080
uid             =  ckan
guid            =  ckan
wsgi-file       =  /etc/ckan/default/wsgi.py
virtualenv      =  /usr/lib/ckan/default
module          =  wsgi:application
master          =  true
pidfile         =  /tmp/%n.pid
harakiri        =  50
max-requests    =  5000
vacuum          =  true
callable        =  application
logto           =  /var/log/nginx/ckan-uwsgi.log
workers         =  1
#---

cd default/src/ckan
ln -s /etc/ckan/default/ckan.ini ./
# ckan-uwsgi-ini移動
/usr/lib/ckan/default/bin/uwsgi -i /etc/ckan/default/ckan-uwsgi.ini

# 自己認証を利用する場合
yum install -y openssl
yum install -y openssl-devel
yum install -y mod_ssl

mkdir /etc/pki/CA
cd /etc/pki/CA
mkdir private
openssl req -new -x509 -newkey rsa:2048 -out cacert.pem -keyout private/cakey.pem -days 36500
chown root:root private/cakey.pem
chmod 600 private/cakey.pem
openssl x509 -in cacert.pem -text
openssl x509 -inform PEM -outform DER -in cacert.pem -out cacert_domain.der
openssl req -new -keyout ckan_key.pem -out ckan_csr.pem
touch index.txt
echo "01" > serial

#  自己認証の署名
mkdir newcerts
openssl ca -policy policy_anything -out ckan_cert.pem -infiles ckan_csr.pem
#ckan_ca
openssl x509 -in ckan_cert.pem -text
openssl rsa -in ckan_key.pem -out ckan_key.pem.nopass


# nginxのconf編集
#　ここではオレオレ認証を利用する
mkdir /var/cache/nginx

vi /etc/nginx/nginx.conf
#----serverに追加
http {
    server {
        server_tokens off;
    }
}
#----

# mkdir /etc/nginx/ssl
# openssl dhparam -out /etc/nginx/ssl/dhparam.pem 2048

vi /etc/nginx/conf.d/ckan-ssl.conf
#---
proxy_cache_path /tmp/nginx_ssl_cache levels=1:2 keys_zone=cache:30m max_size=250m;
proxy_temp_path /tmp/nginx_ssl_proxy 1 2;

server {
    listen 80;
    server_name  server.domain.com;
    return 301 https://$host$request_uri;
}
server {
    listen 443 ssl;
    listen [::]:443 ssl;

    server_name  server.domain.com;
    client_max_body_size 100M;

    ssl_certificate     /etc/pki/CA/ckan_cert.pem;
    ssl_certificate_key /etc/pki/CA/ckan_key.pem.nopass;
    ssl_session_timeout 1d;
    ssl_session_cache shared:MozSSL:10m;  # about 40000 sessions
    ssl_session_tickets off;

    # ssl_dhparam /etc/nginx/ssl/dhparam.pem;
    # intermediate configuration
    ssl_protocols TLSv1.1 TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;

    # HSTS (ngx_http_headers_module is required) (63072000 seconds)
    add_header Strict-Transport-Security "max-age=63072000" always;

    location / {
        proxy_pass http://127.0.0.1:8080/;
        proxy_set_header X-Forwarded-For $remote_addr;
        proxy_set_header Host $host;
        proxy_cache cache;
        proxy_cache_bypass $cookie_auth_tkt;
        proxy_no_cache $cookie_auth_tkt;
        proxy_cache_valid 30m;
        proxy_cache_key $host$scheme$proxy_host$request_uri;
        # In emergency comment out line to force caching
        # proxy_ignore_headers X-Accel-Expires Expires Cache-Control;
    }
}
#---
systemctl restart nginx
```
***
# CKAN エクステンションインストール
## ckanext-harvest インストール
```
su -s /bin/bash - ckan
. default/bin/activate

pip install -e git+https://github.com/ckan/ckanext-harvest.git#egg=ckanext-harvest

cd default/src/ckanext-harvest/
pip install -r pip-requirements.txt
pip install -r dev-requirements.txt
vi /etc/ckan/default/ckan.ini
#---
# 編集
ckan.plugins = harvest ckan_harvester
#　追記
ckan.harvest.mq.type = redis
#ckan.harvest.mq.hostname (localhost)
#ckan.harvest.mq.port (6379)
#ckan.harvest.mq.redis_db (0)
#ckan.harvest.mq.password (None)
#---

# indexの再作成
ckan -c /etc/ckan/default/ckan.ini -r search-index rebuild
ckan -c /etc/ckan/default/ckan.ini harvester reindex
```
## ckanext-harvestの設定
```
#ハーベストの自動設定
vi /etc/supervisord.d/ckan_harvesting.ini
#---
; ===============================
; ckan harvester
; ===============================
[program:ckan_gather_consumer]
command=/usr/lib/ckan/default/bin/ckan --config=/etc/ckan/default/ckan.ini harvester gather-consumer
user=ckan
numprocs=1
stdout_logfile=/var/log/nginx/gather_consumer.log
stderr_logfile=/var/log/nginx/gather_consumer_error.log
; environment=REQUESTS_CA_BUNDLE="/usr/lib/ckan//CA/ckan_bosai_cert.pem"
autostart=true
autorestart=true
startsecs=10
startretries=10
[program:ckan_fetch_consumer]
command=/usr/lib/ckan/default/bin/ckan --config=/etc/ckan/default/ckan.ini harvester fetch-consumer
user=ckan
numprocs=1
stdout_logfile=/var/log/nginx/fetch_consumer.log
stderr_logfile=/var/log/nginx/fetch_consumer_error.log
; environment=REQUESTS_CA_BUNDLE="/usr/lib/ckan//CA/ckan_bosai_cert.pem"
autostart=true
autorestart=true
startsecs=10
startretries=10
#---

# supervisord起動設定
systemctl start supervisord.service
systemctl status supervisord.service
systemctl enable supervisord.service
# supervisordの設定再読み込みを行う場合
sudo supervisorctl reread
sudo supervisorctl status

#　crontabで定期実行
sudo crontab -e
#---
01 * * * * /usr/lib/ckan/default/bin/paster --plugin=ckan tracking update -c /etc/ckan/default/development.ini
02 1 * * * /usr/lib/ckan/default/bin/paster --plugin=ckan search-index rebuild -r -c /etc/ckan/default/development.ini
#---
# harvest runを定期実行
su -s /bin/bash - ckan
. default/bin/activate
sudo crontab -e -u ckan
#----
# m  h  dom mon dow   command
# REQUESTS_CA_BUNDLE=/etc/pki/tls/certs/ca-bundle.crt
# SSL_CERT_PATH=/etc/pki/tls/certs/ca-bundle.crt
*/5 *  *   *   *     /usr/lib/ckan/default/bin/ckan -c /etc/ckan/default/ckan.ini harvester run
15 3  *   *   *     /usr/lib/ckan/default/bin/ckan -c /etc/ckan/default/ckan.ini harvester clearsource-history ソースID
#----
```

## ckanext-dcatインストール
```
su -s /bin/bash - ckan
. default/bin/activate
pip install -e git+https://github.com/ckan/ckanext-dcat.git#egg=ckanext-dcat
cd /usr/lib/ckan/default/src/ckanext-dcat/
pip install -r requirements-py2-py36.txt
# ckan.iniの編集
vi /etc/ckan/default/ckan.ini
#---
ckan.plugins = dcat dcat_rdf_harvester dcat_json_harvester dcat_json_interface structured_data
#---
```

# ckanext-spatialインストール
```
su -s /bin/bash - ckan
. default/bin/activate

pip install -e "git+https://github.com/ckan/ckanext-spatial.git#egg=ckanext-spatial"
cd /usr/lib/ckan/default/src/ckanext-spatial/
pip install -r /usr/lib/ckan/default/src/ckanext-spatial/pip-requirements.txt
# ckan.iniの編集
vi /etc/ckan/default/ckan.ini
#---
ckan.plugins = spatial_metadata spatial_query
ckan.spatial.srid = 4326
ckan.spatial.default_map_extent = 123.135,23.24,157.76,51.51
ckanext.spatial.search_backend = solr
ckanext.spatial.use_postgis_sorting = true

ckanext.spatial.common_map.type = custom
ckanext.spatial.common_map.custom.url = https://cyberjapandata.gsi.go.jp/xyz/std/{z}/{x}/{y}.png
ckanext.spatial.common_map.attribution = Map tiles by <a href="http://www.gsi.go.jp" target="_blank">GSI</a>
#---

#　ckanext-spatialのテンプレート編集
vi /usr/lib/ckan/default/src/ckanext-spatial/ckanext/spatial/templates/spatial/snippets/spatial_query.html
#--- 書き換え 
<i class="icon-medium icon-globe"></i>
# ↓
<i class="fa fa-filter"></i>
#---

#　Apache solrに位置情報の追加
#　solrにjts-core-1.15.jarををダウンロードして配置
https://github.com/locationtech/jts/releases
cp jts-core-1.15.0.jar /opt/solr/server/solr-webapp/webapp/WEB-INF/lib/

vi /usr/lib/ckan/default/src/ckan/ckan/config/solr/schema.xml
#---　追加
    <field name="bbox_area" type="float" indexed="true" stored="true"/>
    <field name="maxx" type="float" indexed="true" stored="true"/>
    <field name="maxy" type="float" indexed="true" stored="true"/>
    <field name="minx" type="float" indexed="true" stored="true"/>
    <field name="miny" type="float" indexed="true" stored="true"/>
    <field name="spatial_geom"  type="location_rpt" indexed="true" stored="true" multiValued="true" />
    #　<types>タグ内に追加
    <!-- ... -->
    <fieldType name="location_rpt" class="solr.SpatialRecursivePrefixTreeFieldType"
        autoIndex="true"
        distErrPct="0.025"
        maxDistErr="0.000009"
        distanceUnits="degrees"
        spatialContextFactory="JTS" />

    #　</types>
#---
systemctl restart solr
```

# ckanext-sip4dエクステンションインストール
```
su -s /bin/bash - ckan
. default/bin/activate
# ckanext-sip4dのファイルをコピー
cp -r /home/src/ckanext-sip4d /usr/lib/ckan/default/src/
#　パッケージをインストール
cd .default/src/ckanext-sip4d
pip install -e ./
pip install -r requirements.txt
# ckan.iniファイルを編集
vi /etc/ckan/default/ckan.ini
#---
ckan.plugins = sip4ddata sip4dview sip4dharvest sip4d_arcgis_harvest

ckanext.sip4d.pass_phrase=9emQludST3S7Sia9VyE9oQ9xdGeyHAeJ
ckanext.sip4d.site_title=SIP4D-CKAN

ckanext.guests_ban = true

ckan.sip4d.thumbnail_width = 140px
ckan.sip4d.thumbnail_height = 140px
ckanext.sip4d_organization = sip4d-t

ckan.search.default_package_sort =  metadata_modified desc
#---

# ckanエクステンションを反映する
# supervisorとnginxを再起動する
systemctl restart supervisord.service
systemctl restart nginx.service
```
