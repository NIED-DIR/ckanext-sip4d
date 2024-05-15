import base64
import random
import six
from Crypto.Cipher import AES
from hashlib import sha256

from ckan import plugins as p
from ckan import model
from ckan.model import Session

from ckan.logic.schema import default_create_package_schema
from ckan.lib.navl.validators import ignore_missing, ignore

from ckanext.harvest.harvesters.base import HarvesterBase
from ckanext.harvest.model import HarvestObject
from ckanext.harvest.logic.schema import unicode_safe

import logging

log = logging.getLogger(__name__)


class Sip4DHarvesterBase(HarvesterBase):

  def _get_object_extra(self, harvest_object, key):
    '''
        Helper function for retrieving the value from a harvest object extra,
        given the key
        '''
    for extra in harvest_object.extras:
      if extra.key == key:
        return extra.value
    return None

  def _sip4d_create_or_update_package(self, status, package_dict, harvest_object):
    '''
        データセットの新規登録、更新を行う。
        :param status: create 新規登録、 update 更新
        :param package_dict:
        :param harvest_object:
        :return:
    '''
    try:
      # context
      user_name = self._get_user_name()
      schema = default_create_package_schema()
      schema['id'] = [ignore_missing, unicode_safe]
      context = {
        'model': model,
        'session': model.Session,
        'user': user_name,
        'api_version': 2,
        'schema': schema,
        'ignore_auth': True,
      }

      if self.config and self.config.get('clean_tags', False):
        tags = package_dict.get('tags', [])
        package_dict['tags'] = self._clean_tags(tags)

      context.update({
        # 'extras_as_string': True,
        'return_id_only': True})

      if status == 'create':
        log.info('Package with GUID %s does not exist, let\'s create it' % harvest_object.guid)
        harvest_object.current = True
        harvest_object.package_id = package_dict['id']
        harvest_object.add()

        model.Session.execute('SET CONSTRAINTS harvest_object_package_id_fkey DEFERRED')
        model.Session.flush()

        package_id = p.toolkit.get_action('package_create')(context, package_dict)
        log.info('Created new package %s with guid %s', package_id, harvest_object.guid)

        result = True

      elif status == 'update':
        log.info('Package with GUID %s exists and needs to be updated' % harvest_object.guid)
        # Update package
        context.update({'id': package_dict['id']})
        # nameが存在しない場合idを設定
        package_dict.setdefault('name', package_dict['id'])

        for field in p.toolkit.aslist(self.config.get('ckan.harvest.not_overwrite_fields')):
          if field in existing_package_dict:
            package_dict[field] = existing_package_dict[field]
        package_id = p.toolkit.get_action('package_update')(context, package_dict)

        log.info('Updated package %s with guid %s', package_id, harvest_object.guid)

        # Flag the other objects linking to this package as not current anymore
        from ckanext.harvest.model import harvest_object_table
        conn = model.Session.connection()
        u = update(harvest_object_table) \
          .where(harvest_object_table.c.package_id == bindparam('b_package_id')) \
          .values(current=False)
        conn.execute(u, b_package_id=package_id)

        # Flag this as the current harvest object

        harvest_object.package_id = package_id
        harvest_object.current = True
        harvest_object.save()

        result = True

      else:
        log.info('Create or Updated package nochange Status %s , package_id %s', status, package_dict['id'])
        result = None

      model.Session.commit()

    except p.toolkit.ValidationError as e:
      log.exception(e)
      self._save_object_error('Invalid package with GUID %s: %r' % (harvest_object.guid, e.error_dict),
                              harvest_object, 'Import')
      return False
    except Exception as e:
      log.exception(e)
      self._save_object_error('%r' % e, harvest_object, 'Import')
      return False

    return result


class AESCipher(object):
  def __init__(self, key, block_size=32):
    self.bs = block_size
    if len(key) >= len(str(block_size)):
      self.key = key[:block_size]
    else:
      self.key = self._pad(key)

  def generate_salt(self, digit_num):
    digits_and_alphabets = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    return "".join(random.sample(digits_and_alphabets, digit_num)).encode()

  def encrypt(self, raw):
    raw = self._pad(raw)
    salt = self.generate_salt(AES.block_size)
    salted = ''.encode()
    dx = ''.encode()
    while len(salted) < 48:
      key_hash = dx + self.key.encode() + salt
      dx = sha256(key_hash).digest()
      salted = salted + dx

    key = salted[0:32]
    iv = salted[32:48]

    cipher = AES.new(key, AES.MODE_CBC, iv)
    return base64.b64encode(salt + cipher.encrypt(raw.encode('utf-8')))

  def decrypt(self, enc):
    enc = base64.b64decode(enc)
    salt = enc[0:16]
    ct = enc[16:]
    rounds = 3

    data00 = self.key.encode() + salt
    dec_hash = {}
    dec_hash[0] = sha256(data00).digest()
    result = dec_hash[0]
    for i in range(1, rounds):
      dec_hash[i] = sha256(dec_hash[i - 1] + data00).digest()
      result += dec_hash[i]

    key = result[0:32]
    iv = result[32:48]
    cipher = AES.new(key, AES.MODE_CBC, iv)
    return self._unpad(cipher.decrypt(enc[16:]).decode())

  def _pad(self, s):
    return s + (self.bs - len(s) % self.bs) * chr(self.bs - len(s) % self.bs)

  def _unpad(self, s):
    return s[:-ord(s[len(s) - 1:])]
