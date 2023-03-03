# -*- coding: utf-8 -*-

import logging

from flask import Blueprint, make_response

import ckanext.sip4d.utils as utils
import ckan.plugins.toolkit as tk

import inspect

log = logging.getLogger(__name__)

sip4d_interface = Blueprint("sip4d", __name__)


def show_updateview():
    return utils.datesetview()


def disaster_update():
    # obj = tk.request
    # for m in inspect.getmembers(obj):
    #     print(m)
    return utils.disasterupdate(make_response)


def sip4d_search_dataset():
    return utils.sip4d_search_dataset()


sip4d_interface.add_url_rule(u'/sip4d/sip4d_update_list_page', view_func=show_updateview)
sip4d_interface.add_url_rule(u'/sip4d/disaster_update', methods=[u'POST'], view_func=disaster_update)
sip4d_interface.add_url_rule(u'/sip4d_search_dataset', methods=[u'GET', u'POST'], view_func=sip4d_search_dataset)


def get_blueprints():
    return [sip4d_interface]
