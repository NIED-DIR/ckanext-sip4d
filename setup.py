from setuptools import setup, find_packages

version = '0.4'

setup(
    name='ckanext-sip4d',
    version=version,
    description='SIP4D extension for customising CKAN',
    long_description='',
    classifiers=[],  # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
    keywords='',
    author='National Research Institute for Earth Science and Disaster Resilience',
    author_email='',
    url='',
    license='',
    packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
    namespace_packages=['ckanext'],
    include_package_data=True,
    zip_safe=False,
    install_requires=[],
    entry_points="""
        [ckan.plugins]
            sip4ddata=ckanext.sip4d.plugin:Sip4DDataPlugin
            sip4dview=ckanext.sip4d.plugin:Sip4DDataViewPlugin
            
            sip4dharvest=ckanext.sip4d.harvesters:Sip4DHarvester
            sip4d_arcgis_harvest=ckanext.sip4d.harvesters:Sip4DArcGISHarvester
        
        [babel.extractors]
            ckan = ckan.lib.extract:extract_ckan
	""",
    message_extractors={
        'ckanext': [
            ('**.py', 'python', None),
            ('**.js', 'javascript', None),
            ('**/templates/**.html', 'ckan', None),
        ],
    },
)
