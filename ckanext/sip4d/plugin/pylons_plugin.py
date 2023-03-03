# -*- coding: utf-8 -*-

import ckan.plugins as p


class Sip4DMixinPlugin(p.SingletonPlugin):
    p.implements(p.IRoutes, inherit=True)

    def after_map(self, map):
        controller = 'ckanext.sip4d.controller:Sip4DCustomViewController'
        map.connect('/sip4d/sip4d_update_list_page', controller=controller, action='datesetview')
        map.connect('/sip4d/disaster_update', controller=controller, action='disasterupdate')
        map.connect('/sip4d_search_dataset', controller=controller, action='sip4d_search')
        return map
