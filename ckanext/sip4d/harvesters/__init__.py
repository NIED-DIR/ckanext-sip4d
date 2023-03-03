# this is a namespace package
try:
    import pkg_resources
    pkg_resources.declare_namespace(__name__)
except ImportError:
    import pkgutil
    __path__ = pkgutil.extend_path(__path__, __name__)

from ckanext.sip4d.harvesters.base import Sip4DHarvesterBase
from ckanext.sip4d.harvesters.sip4d import Sip4DHarvester
from ckanext.sip4d.harvesters.sip4darc import Sip4DArcGISHarvester

# __all__ = ['Sip4DHarvester', 'Sip4DArcGISHarvester', 'Sip4DHarvesterBase']