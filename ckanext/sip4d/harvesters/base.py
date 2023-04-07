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

    def _sip4d_create_or_update_package(self, package_dict, harvest_object,
                                        package_dict_form='rest'):

        assert package_dict_form in ('rest', 'package_show')
        try:
            # Change default schema
            schema = default_create_package_schema()
            schema['id'] = [ignore_missing, six.text_type]  # unicode
            schema['__junk'] = [ignore]

            # Check API version
            if self.config:
                try:
                    api_version = int(self.config.get('api_version', 2))
                except ValueError:
                    raise ValueError('api_version must be an integer')
            else:
                api_version = 2

            user_name = self._get_user_name()
            context = {
                'model': model,
                'session': Session,
                'user': user_name,
                'api_version': api_version,
                'schema': schema,
                'ignore_auth': True,
            }

            if self.config and self.config.get('clean_tags', False):
                tags = package_dict.get('tags', [])
                package_dict['tags'] = self._clean_tags(tags)

            # Check if package exists
            try:
                previous_object = model.Session.query(HarvestObject) \
                    .filter(HarvestObject.guid == harvest_object.guid) \
                    .filter(HarvestObject.current is True) \
                    .first()

                # mod previous_object
                if previous_object and not self.force_import:
                    previous_object.current = False
                    previous_object.save()

                # _find_existing_package can be overridden if necessary
                existing_package_dict = self._find_existing_package(package_dict)

                # In case name has been modified when first importing. See issue #101.
                package_dict['name'] = existing_package_dict['name']

                log.info('existing_package_dict state %s' % existing_package_dict['state'])

                # Check modified date
                if 'metadata_modified' not in package_dict or \
                        package_dict['metadata_modified'] > existing_package_dict.get('metadata_modified'):
                    log.info('Package with GUID %s exists and needs to be updated' % harvest_object.guid)
                    # Update package
                    context.update({'id': package_dict['id']})
                    package_dict.setdefault('name',
                                            existing_package_dict['name'])
                    # mod
                    package_dict['state'] = 'active'

                    new_package = p.toolkit.get_action(
                        'package_update' if package_dict_form == 'package_show'
                        else 'package_update_rest')(context, package_dict)
                # mod
                elif 'state' in existing_package_dict and existing_package_dict['state'] == 'deleted':
                    # Update package
                    context.update({'id': package_dict['id']})
                    package_dict.setdefault('name',
                                            existing_package_dict['name'])
                    package_dict['state'] = 'active'

                    new_package = p.toolkit.get_action(
                        'package_update' if package_dict_form == 'package_show'
                        else 'package_update_rest')(context, package_dict)
                else:
                    harvest_object.package_id = package_dict['id']
                    harvest_object.current = True
                    # harvest_object.content = ''
                    harvest_object.save()

                    log.info('SIP4d harvest: No changes to package with GUID %s, skipping...' % harvest_object.guid)
                    # NB harvest_object.current/package_id are not set
                    return 'unchanged'

                # Flag this as the current harvest object
                harvest_object.package_id = new_package['id']
                harvest_object.current = True
                # mod
                harvest_object.content = ''
                harvest_object.save()

            except p.toolkit.ObjectNotFound:
                # Package needs to be created

                # Get rid of auth audit on the context otherwise we'll get an
                # exception
                context.pop('__auth_audit', None)

                # Set name for new package to prevent name conflict, see issue #117
                if package_dict.get('name', None):
                    package_dict['name'] = self._gen_new_name(package_dict['name'])
                else:
                    package_dict['name'] = self._gen_new_name(package_dict['title'])

                log.info('Package with GUID %s does not exist, let\'s create it' % harvest_object.guid)
                harvest_object.current = True
                harvest_object.package_id = package_dict['id']
                # mod
                # harvest_object.content = ''
                # Defer constraints and flush so the dataset can be indexed with
                # the harvest object id (on the after_show hook from the harvester
                # plugin)
                harvest_object.add()

                model.Session.execute('SET CONSTRAINTS harvest_object_package_id_fkey DEFERRED')
                model.Session.flush()

                new_package = p.toolkit.get_action(
                    'package_create' if package_dict_form == 'package_show'
                    else 'package_create_rest')(context, package_dict)
            finally:
                Session.commit()

            return True

        except p.toolkit.ValidationError as e:
            log.exception(e)
            self._save_object_error('Invalid package with GUID %s: %r' % (harvest_object.guid, e.error_dict),
                                    harvest_object, 'Import')
        except Exception as e:
            log.exception(e)
            self._save_object_error('%r' % e, harvest_object, 'Import')

        return None


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
