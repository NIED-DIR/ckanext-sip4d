# -*- coding: utf-8 -*-

import ckan.plugins as p

# import ckanext.sip4d.cli as cli
import ckanext.sip4d.views as views


class Sip4DMixinPlugin(p.SingletonPlugin):
    p.implements(p.IBlueprint)

    # IClick

    # def get_commands(self):
    #     return cli.get_commands()

    # IBlueprint

    def get_blueprint(self):
        return views.get_blueprints()
