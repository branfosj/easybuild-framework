# #
# Copyright 2009-2025 Ghent University
#
# This file is part of EasyBuild,
# originally created by the HPC team of Ghent University (http://ugent.be/hpc/en),
# with support of Ghent University (http://ugent.be/hpc),
# the Flemish Supercomputer Centre (VSC) (https://www.vscentrum.be),
# Flemish Research Foundation (FWO) (http://www.fwo.be/en)
# and the Department of Economy, Science and Innovation (EWI) (http://www.ewi-vlaanderen.be/en).
#
# https://github.com/easybuilders/easybuild
#
# EasyBuild is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation v2.
#
# EasyBuild is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with EasyBuild.  If not, see <http://www.gnu.org/licenses/>.
# #
"""
Documentation-related functionality

Authors:

* Stijn De Weirdt (Ghent University)
* Dries Verdegem (Ghent University)
* Kenneth Hoste (Ghent University)
* Pieter De Baets (Ghent University)
* Jens Timmerman (Ghent University)
* Toon Willems (Ghent University)
* Ward Poelmans (Ghent University)
* Caroline De Brouwer (Ghent University)
"""
import copy
import inspect
import json
import os
from collections import OrderedDict
from easybuild.tools import LooseVersion
from string import ascii_lowercase

from easybuild.base import fancylogger
from easybuild.framework.easyconfig.default import DEFAULT_CONFIG, HIDDEN, sorted_categories
from easybuild.framework.easyblock import EasyBlock
from easybuild.framework.easyconfig.constants import EASYCONFIG_CONSTANTS
from easybuild.framework.easyconfig.easyconfig import get_easyblock_class, process_easyconfig
from easybuild.framework.easyconfig.licenses import EASYCONFIG_LICENSES_DICT
from easybuild.framework.easyconfig.parser import ALTERNATIVE_EASYCONFIG_PARAMETERS, EasyConfigParser
from easybuild.framework.easyconfig.templates import TEMPLATE_CONSTANTS, TEMPLATE_NAMES_CONFIG, TEMPLATE_NAMES_DYNAMIC
from easybuild.framework.easyconfig.templates import TEMPLATE_NAMES_EASYBLOCK_RUN_STEP, TEMPLATE_NAMES_EASYCONFIG
from easybuild.framework.easyconfig.templates import TEMPLATE_NAMES_LOWER, TEMPLATE_NAMES_LOWER_TEMPLATE
from easybuild.framework.easyconfig.templates import TEMPLATE_SOFTWARE_VERSIONS, template_constant_dict
from easybuild.framework.easyconfig.tools import avail_easyblocks
from easybuild.framework.easyconfig.tweak import find_matching_easyconfigs
from easybuild.framework.extension import Extension
from easybuild.tools.build_log import EasyBuildError, print_msg
from easybuild.tools.config import build_option
from easybuild.tools.filetools import read_file
from easybuild.tools.modules import modules_tool
from easybuild.tools.toolchain.toolchain import SYSTEM_TOOLCHAIN_NAME, is_system_toolchain
from easybuild.tools.toolchain.utilities import search_toolchain
from easybuild.tools.utilities import INDENT_2SPACES, INDENT_4SPACES
from easybuild.tools.utilities import import_available_modules, mk_md_table, mk_rst_table, nub, quote_str


_log = fancylogger.getLogger('tools.docs')


DETAILED = 'detailed'
SIMPLE = 'simple'

FORMAT_JSON = 'json'
FORMAT_MD = 'md'
FORMAT_RST = 'rst'
FORMAT_TXT = 'txt'


def generate_doc(name, params):
    """Generate documentation by calling function with specified name, using supplied parameters."""
    func = globals()[name]
    return func(*params)


def md_title_and_table(title, table_titles, table_values, title_level=1):
    """Generate table in section with title in MarkDown (.md) format."""
    doc = []
    if title is not None:
        doc.extend([
            '#' * title_level + ' ' + title,
            '',
        ])
    doc.extend(mk_md_table(table_titles, table_values))
    return doc


def rst_title_and_table(title, table_titles, table_values):
    """Generate table in section with title in .rst format."""
    doc = []
    if title is not None:
        doc.extend([
            title,
            '-' * len(title),
            '',
        ])
    doc.extend(mk_rst_table(table_titles, table_values))
    return doc


def avail_cfgfile_constants(go_cfg_constants, output_format=FORMAT_TXT):
    """
    Return overview of constants supported in configuration files.
    """
    return generate_doc('avail_cfgfile_constants_%s' % output_format, [go_cfg_constants])


def avail_cfgfile_constants_json(go_cfg_constants):
    """Generate documentation on constants for configuration files in json format"""
    raise NotImplementedError("JSON output format not supported for avail_cfgfile_constants_json")


def avail_cfgfile_constants_txt(go_cfg_constants):
    """Generate documentation on constants for configuration files in txt format"""
    doc = [
        "Constants available (only) in configuration files:",
        "syntax: %(CONSTANT_NAME)s",
    ]
    for section in go_cfg_constants:
        doc.append('')
        if section != go_cfg_constants['DEFAULT']:
            section_title = "only in '%s' section:" % section
            doc.append(section_title)
        for cst_name, (cst_value, cst_help) in sorted(go_cfg_constants[section].items()):
            doc.append("* %s: %s [value: %s]" % (cst_name, cst_help, cst_value))
    return '\n'.join(doc)


def avail_cfgfile_constants_rst(go_cfg_constants):
    """Generate documentation on constants for configuration files in rst format"""
    title = "Constants available (only) in configuration files"
    doc = [title, '-' * len(title)]

    for section in go_cfg_constants:
        doc.append('')
        if section != go_cfg_constants['DEFAULT']:
            section_title = "Only in '%s' section:" % section
            doc.extend([section_title, '-' * len(section_title), ''])
        table_titles = ["Constant name", "Constant help", "Constant value"]
        sorted_names = sorted(go_cfg_constants[section].keys())
        table_values = [
            ['``' + x + '``' for x in sorted_names],
            [go_cfg_constants[section][x][1] for x in sorted_names],
            ['``' + go_cfg_constants[section][x][0] + '``' for x in sorted_names],
        ]
        doc.extend(mk_rst_table(table_titles, table_values))

    return '\n'.join(doc)


def avail_cfgfile_constants_md(go_cfg_constants):
    """Generate documentation on constants for configuration files in MarkDown format"""
    title = "Constants available (only) in configuration files"
    doc = [
        '# ' + title,
        '',
    ]

    for section in go_cfg_constants:
        if section != go_cfg_constants['DEFAULT']:
            doc.extend([
                "## Only in '%s' section:" % section,
                '',
            ])
        table_titles = ["Constant name", "Constant help", "Constant value"]
        sorted_names = sorted(go_cfg_constants[section].keys())
        table_values = [
            ['``' + x + '``' for x in sorted_names],
            [go_cfg_constants[section][x][1] for x in sorted_names],
            ['``' + go_cfg_constants[section][x][0] + '``' for x in sorted_names],
        ]
        doc.extend(mk_md_table(table_titles, table_values))

    return '\n'.join(doc)


def avail_easyconfig_constants(output_format=FORMAT_TXT):
    """Generate the easyconfig constant documentation"""
    return generate_doc('avail_easyconfig_constants_%s' % output_format, [])


def avail_easyconfig_constants_json():
    """Generate easyconfig constant documentation in json format"""
    raise NotImplementedError("JSON output format not supported for avail_easyconfig_constants_json")


def avail_easyconfig_constants_txt():
    """Generate easyconfig constant documentation in txt format"""
    doc = ["Constants that can be used in easyconfigs"]
    for cst, (val, descr) in sorted(EASYCONFIG_CONSTANTS.items()):
        doc.append('%s%s: %s (%s)' % (INDENT_4SPACES, cst, val, descr))

    return '\n'.join(doc)


def avail_easyconfig_constants_rst():
    """Generate easyconfig constant documentation in rst format"""
    title = "Constants that can be used in easyconfigs"

    table_titles = [
        "Constant name",
        "Constant value",
        "Description",
    ]

    sorted_keys = sorted(EASYCONFIG_CONSTANTS)

    table_values = [
        ["``%s``" % key for key in sorted_keys],
        ["``%s``" % str(EASYCONFIG_CONSTANTS[key][0]) for key in sorted_keys],
        [EASYCONFIG_CONSTANTS[key][1] for key in sorted_keys],
    ]

    doc = rst_title_and_table(title, table_titles, table_values)
    return '\n'.join(doc)


def avail_easyconfig_constants_md():
    """Generate easyconfig constant documentation in MarkDown format"""
    title = "Constants that can be used in easyconfigs"

    table_titles = [
        "Constant name",
        "Constant value",
        "Description",
    ]

    sorted_keys = sorted(EASYCONFIG_CONSTANTS)

    table_values = [
        ["``%s``" % key for key in sorted_keys],
        ["``%s``" % str(EASYCONFIG_CONSTANTS[key][0]) for key in sorted_keys],
        [EASYCONFIG_CONSTANTS[key][1] for key in sorted_keys],
    ]

    doc = md_title_and_table(title, table_titles, table_values)
    return '\n'.join(doc)


def avail_easyconfig_licenses(output_format=FORMAT_TXT):
    """Generate the easyconfig licenses documentation"""
    return generate_doc('avail_easyconfig_licenses_%s' % output_format, [])


def avail_easyconfig_licenses_json():
    """Generate easyconfig license documentation in json format"""
    raise NotImplementedError("JSON output format not supported for avail_easyconfig_licenses_json")


def avail_easyconfig_licenses_txt():
    """Generate easyconfig license documentation in txt format"""
    doc = ["License constants that can be used in easyconfigs"]
    for lic_name, lic in sorted(EASYCONFIG_LICENSES_DICT.items()):
        lic_inst = lic()
        strver = ''
        if lic_inst.version:
            strver = " (version: %s)" % '.'.join([str(d) for d in lic_inst.version])
        doc.append("%s%s: %s%s" % (INDENT_4SPACES, lic_inst.name, lic_inst.description, strver))

    return '\n'.join(doc)


def avail_easyconfig_licenses_rst():
    """Generate easyconfig license documentation in rst format"""
    title = "License constants that can be used in easyconfigs"

    table_titles = [
        "License name",
        "License description",
        "Version",
    ]

    lics = sorted(EASYCONFIG_LICENSES_DICT.items())
    table_values = [
        ["``%s``" % lic().name for _, lic in lics],
        ["%s" % lic().description for _, lic in lics],
        ["``%s``" % lic().version for _, lic in lics],
    ]

    doc = rst_title_and_table(title, table_titles, table_values)
    return '\n'.join(doc)


def avail_easyconfig_licenses_md():
    """Generate easyconfig license documentation in MarkDown format"""
    title = "License constants that can be used in easyconfigs"

    table_titles = [
        "License name",
        "License description",
        "Version",
    ]

    lics = sorted(EASYCONFIG_LICENSES_DICT.items())
    table_values = [
        ["``%s``" % lic().name for _, lic in lics],
        [lic().description or '' for _, lic in lics],
        ["``%s``" % lic().version for _, lic in lics],
    ]

    doc = md_title_and_table(title, table_titles, table_values)
    return '\n'.join(doc)


def avail_easyconfig_params_md(title, grouped_params, alternative_params):
    """
    Compose overview of available easyconfig parameters, in MarkDown format.
    """
    # main title
    doc = [
        '# ' + title,
        '',
    ]

    for grpname in grouped_params:
        # group section title
        title = "%s%s parameters" % (grpname[0].upper(), grpname[1:])
        table_titles = ["**Parameter name**", "**Description**", "**Default value**", "**Alternative name**"]
        keys = sorted(grouped_params[grpname].keys())
        values = [grouped_params[grpname][key] for key in keys]
        table_values = [
            ['`%s`' % name for name in keys],  # parameter name
            [x[0].replace('<', '&lt;').replace('>', '&gt;') for x in values],  # description
            ['`' + str(quote_str(x[1])) + '`' for x in values],  # default value
            ['`%s`' % alternative_params[name] if name in alternative_params else '' for name in keys],
        ]

        doc.extend(md_title_and_table(title, table_titles, table_values, title_level=2))
        doc.append('')

    return '\n'.join(doc)


def avail_easyconfig_params_rst(title, grouped_params, alternative_params):
    """
    Compose overview of available easyconfig parameters, in RST format.
    """
    # main title
    doc = [
        title,
        '=' * len(title),
        '',
    ]

    for grpname in grouped_params:
        # group section title
        title = "%s parameters" % grpname
        table_titles = ["**Parameter name**", "**Description**", "**Default value**", "**Alternative name**"]
        keys = sorted(grouped_params[grpname].keys())
        values = [grouped_params[grpname][key] for key in keys]
        table_values = [
            ['``%s``' % name for name in keys],  # parameter name
            [x[0] for x in values],  # description
            [str(quote_str(x[1])) for x in values],  # default value
            ['``%s``' % alternative_params[name] if name in alternative_params else '' for name in keys],
        ]

        doc.extend(rst_title_and_table(title, table_titles, table_values))
        doc.append('')

    return '\n'.join(doc)


def avail_easyconfig_params_json(*args):
    """
    Compose overview of available easyconfig parameters, in json format.
    """
    raise NotImplementedError("JSON output format not supported for avail_easyconfig_params_json")


def avail_easyconfig_params_txt(title, grouped_params, alternative_params):
    """
    Compose overview of available easyconfig parameters, in plain text format.
    """
    # main title
    doc = [
        '%s:' % title,
        '',
    ]

    for grpname in grouped_params:
        # group section title
        doc.append(grpname.upper())
        doc.append('-' * len(doc[-1]))

        # determine width of 'name' column, to left-align descriptions
        nw = max(map(len, grouped_params[grpname].keys()))

        # line by parameter
        for name, (descr, dflt) in sorted(grouped_params[grpname].items()):
            line = ' '.join([
                '{0:<{nw}}  ',
                '{1:}',
                '[default: {2:}]',
            ]).format(name, descr, str(quote_str(dflt)), nw=nw)

            alternative = alternative_params.get(name)
            if alternative:
                line += ' {alternative: %s}' % alternative

            doc.append(line)
        doc.append('')

    return '\n'.join(doc)


def avail_easyconfig_params(easyblock, output_format=FORMAT_TXT):
    """
    Compose overview of available easyconfig parameters, in specified format.
    """
    params = copy.deepcopy(DEFAULT_CONFIG)

    # include list of extra parameters (if any)
    extra_params = {}
    app = get_easyblock_class(easyblock, error_on_missing_easyblock=False)
    if app is not None:
        extra_params = app.extra_options()
    params.update(extra_params)

    # reverse mapping of alternative easyconfig parameter names
    alternative_params = {v: k for k, v in ALTERNATIVE_EASYCONFIG_PARAMETERS.items()}

    # compose title
    title = "Available easyconfig parameters"
    if extra_params:
        title += " (* indicates specific to the %s easyblock)" % app.__name__

    # group parameters by category
    grouped_params = OrderedDict()
    for category in sorted_categories():
        # exclude hidden parameters
        if category[1].upper() in [HIDDEN]:
            continue

        grpname = category[1]
        grouped_params[grpname] = {}
        for name, (dflt, descr, cat) in sorted(params.items()):
            if cat == category:
                if name in extra_params:
                    # mark easyblock-specific parameters
                    name = '%s*' % name
                grouped_params[grpname].update({name: (descr, dflt)})

        if not grouped_params[grpname]:
            del grouped_params[grpname]

    # compose output, according to specified format (txt, rst, ...)
    return generate_doc('avail_easyconfig_params_%s' % output_format, [title, grouped_params, alternative_params])


def avail_easyconfig_templates(output_format=FORMAT_TXT):
    """Generate the templating documentation"""
    return generate_doc('avail_easyconfig_templates_%s' % output_format, [])


def avail_easyconfig_templates_json():
    """ Returns template documentation in json text format """
    raise NotImplementedError("JSON output format not supported for avail_easyconfig_templates")


def avail_easyconfig_templates_txt():
    """ Returns template documentation in plain text format """
    # This has to reflect the methods/steps used in easyconfig _generate_template_values
    doc = []

    # step 1: add TEMPLATE_NAMES_EASYCONFIG
    doc.append('Template names/values derived from easyconfig instance')
    for name, curDoc in TEMPLATE_NAMES_EASYCONFIG.items():
        doc.append("%s%%(%s)s: %s" % (INDENT_4SPACES, name, curDoc))
    doc.append('')

    # step 2: add SOFTWARE_VERSIONS
    doc.append('Template names/values for (short) software versions')
    for name, prefix in TEMPLATE_SOFTWARE_VERSIONS.items():
        doc.append("%s%%(%smajver)s: major version for %s" % (INDENT_4SPACES, prefix, name))
        doc.append("%s%%(%sshortver)s: short version for %s (<major>.<minor>)" % (INDENT_4SPACES, prefix, name))
        doc.append("%s%%(%sver)s: full version for %s" % (INDENT_4SPACES, prefix, name))
    doc.append('')

    # step 3: add remaining config
    doc.append('Template names/values as set in easyconfig')
    for name in TEMPLATE_NAMES_CONFIG:
        doc.append("%s%%(%s)s" % (INDENT_4SPACES, name))
    doc.append('')

    # step 4:  make lower variants
    doc.append('Lowercase values of template values')
    for name in TEMPLATE_NAMES_LOWER:
        template_name = TEMPLATE_NAMES_LOWER_TEMPLATE % {'name': name}
        doc.append("%s%%(%s)s: lower case of value of %s" % (INDENT_4SPACES, template_name, name))
    doc.append('')

    # step 5: template_values can/should be updated from outside easyconfig
    # (eg the run_step code in EasyBlock)
    doc.append('Template values set outside EasyBlock runstep')
    for name, cur_doc in TEMPLATE_NAMES_EASYBLOCK_RUN_STEP.items():
        doc.append("%s%%(%s)s: %s" % (INDENT_4SPACES, name, cur_doc))
    doc.append('')

    # some template values are only defined dynamically,
    # see template_constant_dict function in easybuild.framework.easyconfigs.templates
    doc.append('Template values which are defined dynamically')
    for name, cur_doc in TEMPLATE_NAMES_DYNAMIC.items():
        doc.append("%s%%(%s)s: %s" % (INDENT_4SPACES, name, cur_doc))
    doc.append('')

    doc.append('Template constants that can be used in easyconfigs')
    for name, (value, cur_doc) in TEMPLATE_CONSTANTS.items():
        doc.append('%s%s: %s (%s)' % (INDENT_4SPACES, name, cur_doc, value))

    return '\n'.join(doc)


def avail_easyconfig_templates_rst():
    """ Returns template documentation in rst format """
    table_titles = ['Template name', 'Template value']

    title = 'Template names/values derived from easyconfig instance'
    table_values = [
        ['``%%(%s)s``' % name for name in TEMPLATE_NAMES_EASYCONFIG],
        list(TEMPLATE_NAMES_EASYCONFIG.values()),
    ]
    doc = rst_title_and_table(title, table_titles, table_values)
    doc.append('')

    title = 'Template names/values for (short) software versions'
    ver = []
    ver_desc = []
    for name, prefix in TEMPLATE_SOFTWARE_VERSIONS.items():
        ver.append('``%%(%smajver)s``' % prefix)
        ver.append('``%%(%sshortver)s``' % prefix)
        ver.append('``%%(%sver)s``' % prefix)
        ver_desc.append('major version for %s' % name)
        ver_desc.append('short version for %s (<major>.<minor>)' % name)
        ver_desc.append('full version for %s' % name)
    table_values = [ver, ver_desc]
    doc.extend(rst_title_and_table(title, table_titles, table_values))
    doc.append('')

    title = 'Template names/values as set in easyconfig'
    doc.extend([title, '-' * len(title), ''])
    for name in TEMPLATE_NAMES_CONFIG:
        doc.append('* ``%%(%s)s``' % name)
    doc.append('')

    title = 'Lowercase values of template values'
    table_values = [
        ['``%%(%s)s``' % (TEMPLATE_NAMES_LOWER_TEMPLATE % {'name': name}) for name in TEMPLATE_NAMES_LOWER],
        ['lower case of value of %s' % name for name in TEMPLATE_NAMES_LOWER],
    ]
    doc.extend(rst_title_and_table(title, table_titles, table_values))

    title = 'Template values set outside EasyBlock runstep'
    table_values = [
        ['``%%(%s)s``' % name for name in TEMPLATE_NAMES_EASYBLOCK_RUN_STEP],
        list(TEMPLATE_NAMES_EASYBLOCK_RUN_STEP.values()),
    ]
    doc.extend(rst_title_and_table(title, table_titles, table_values))

    title = 'Template values which are defined dynamically'
    table_values = [
        ['``%%(%s)s``' % name for name in TEMPLATE_NAMES_DYNAMIC],
        list(TEMPLATE_NAMES_DYNAMIC.values()),
    ]
    doc.extend(rst_title_and_table(title, table_titles, table_values))

    title = 'Template constants that can be used in easyconfigs'
    titles = ['Constant', 'Template description', 'Template value']
    table_values = [
        ['``%s``' % name for name in TEMPLATE_CONSTANTS],
        [doc for _, doc in TEMPLATE_CONSTANTS.values()],
        ['``%s``' % value for value, _ in TEMPLATE_CONSTANTS.values()],
    ]
    doc.extend(rst_title_and_table(title, titles, table_values))

    return '\n'.join(doc)


def avail_easyconfig_templates_md():
    """Returns template documentation in MarkDown format."""
    table_titles = ['Template name', 'Template value']

    title = 'Template names/values derived from easyconfig instance'
    table_values = [
        ['``%%(%s)s``' % name for name in TEMPLATE_NAMES_EASYCONFIG],
        list(TEMPLATE_NAMES_EASYCONFIG.values()),
    ]
    doc = md_title_and_table(title, table_titles, table_values, title_level=2)
    doc.append('')

    title = 'Template names/values for (short) software versions'
    ver = []
    ver_desc = []
    for name, prefix in TEMPLATE_SOFTWARE_VERSIONS.items():
        ver.append('``%%(%smajver)s``' % prefix)
        ver.append('``%%(%sshortver)s``' % prefix)
        ver.append('``%%(%sver)s``' % prefix)
        ver_desc.append('major version for %s' % name)
        ver_desc.append('short version for %s (``<major>.<minor>``)' % name)
        ver_desc.append('full version for %s' % name)
    table_values = [ver, ver_desc]
    doc.extend(md_title_and_table(title, table_titles, table_values, title_level=2))
    doc.append('')

    title = '## Template names/values as set in easyconfig'
    doc.extend([title, ''])
    for name in TEMPLATE_NAMES_CONFIG:
        doc.append('* ``%%(%s)s``' % name)
    doc.append('')

    title = 'Lowercase values of template values'
    table_values = [
        ['``%%(%s)s``' % (TEMPLATE_NAMES_LOWER_TEMPLATE % {'name': name}) for name in TEMPLATE_NAMES_LOWER],
        ['lower case of value of %s' % name for name in TEMPLATE_NAMES_LOWER],
    ]
    doc.extend(md_title_and_table(title, table_titles, table_values, title_level=2))
    doc.append('')

    title = 'Template values set outside EasyBlock runstep'
    table_values = [
        ['``%%(%s)s``' % name for name in TEMPLATE_NAMES_EASYBLOCK_RUN_STEP],
        list(TEMPLATE_NAMES_EASYBLOCK_RUN_STEP.values()),
    ]
    doc.extend(md_title_and_table(title, table_titles, table_values, title_level=2))
    doc.append('')

    title = 'Template values which are defined dynamically'
    table_values = [
        ['``%%(%s)s``' % name for name in TEMPLATE_NAMES_DYNAMIC],
        list(TEMPLATE_NAMES_DYNAMIC.values()),
    ]
    doc.extend(md_title_and_table(title, table_titles, table_values, title_level=2))
    doc.append('')

    title = 'Template constants that can be used in easyconfigs'
    titles = ['Constant', 'Template description', 'Template value']
    table_values = [
        ['``%s``' % name for name in TEMPLATE_CONSTANTS],
        [doc for _, doc in TEMPLATE_CONSTANTS.values()],
        ['``%s``' % value for value, _ in TEMPLATE_CONSTANTS.values()],
    ]

    doc.extend(md_title_and_table(title, titles, table_values, title_level=2))

    return '\n'.join(doc)


def avail_classes_tree(classes, class_names, locations, detailed, format_strings, depth=0):
    """Print list of classes as a tree."""
    txt = []

    for class_name in class_names:
        class_info = classes[class_name]
        if detailed:
            mod = class_info['module']
            loc = ''
            if mod in locations:
                loc = '@ %s' % locations[mod]['loc']
            txt.append(format_strings['zero_indent'] + format_strings['indent'] * depth +
                       format_strings['sep'] + "%s (%s %s)" % (class_name, mod, loc))
        else:
            txt.append(format_strings['zero_indent'] + format_strings['indent'] * depth +
                       format_strings['sep'] + class_name)
        if 'children' in class_info:
            if len(class_info['children']) > 0:
                if format_strings.get('newline') is not None:
                    txt.append(format_strings['newline'])
                txt.extend(avail_classes_tree(classes, class_info['children'], locations, detailed,
                                              format_strings, depth + 1))
                if format_strings.get('newline') is not None:
                    txt.append(format_strings['newline'])
    return txt


def list_easyblocks(list_easyblocks=SIMPLE, output_format=FORMAT_TXT):
    if output_format == FORMAT_JSON:
        raise NotImplementedError("JSON output format not supported for list_easyblocks")
    format_strings = {
        FORMAT_MD: {
            'det_root_templ': "- **%s** (%s%s)",
            'root_templ': "- **%s**",
            'zero_indent': INDENT_2SPACES,
            'indent': INDENT_2SPACES,
            'sep': '- ',
        },
        FORMAT_RST: {
            'det_root_templ': "* **%s** (%s%s)",
            'root_templ': "* **%s**",
            'zero_indent': INDENT_2SPACES,
            'indent': INDENT_2SPACES,
            'newline': '',
            'sep': '* ',
        },
        FORMAT_TXT: {
            'det_root_templ': "%s (%s%s)",
            'root_templ': "%s",
            'zero_indent': '',
            'indent': "|   ",
            'sep': "|-- ",
        },
    }
    return gen_list_easyblocks(list_easyblocks, format_strings[output_format])


def gen_list_easyblocks(list_easyblocks, format_strings):
    """Get a class tree for easyblocks."""
    detailed = list_easyblocks == DETAILED

    locations = avail_easyblocks()

    def add_class(classes, cls):
        """Add a new class, and all of its subclasses."""
        children = cls.__subclasses__()
        classes.update({cls.__name__: {
            'module': cls.__module__,
            'children': sorted([c.__name__ for c in children], key=lambda x: x.lower())
        }})
        for child in children:
            add_class(classes, child)

    roots = [EasyBlock, Extension]

    classes = {}
    for root in roots:
        add_class(classes, root)

    # Print the tree, start with the roots
    txt = []

    for root in roots:
        root = root.__name__
        if detailed:
            mod = classes[root]['module']
            loc = ''
            if mod in locations:
                loc = ' @ %s' % locations[mod]['loc']
            txt.append(format_strings['det_root_templ'] % (root, mod, loc))
        else:
            txt.append(format_strings['root_templ'] % root)

        if format_strings.get('newline') is not None:
            txt.append(format_strings['newline'])
        if 'children' in classes[root]:
            txt.extend(avail_classes_tree(classes, classes[root]['children'], locations, detailed, format_strings))
            if format_strings.get('newline') is not None:
                txt.append(format_strings['newline'])
    return '\n'.join(txt)


def list_software(output_format=FORMAT_TXT, detailed=False, only_installed=False):
    """
    Show list of supported software

    :param output_format: output format to use
    :param detailed: whether or not to return detailed information (incl. version, versionsuffix, toolchain info)
    :param only_installed: only retain software for which a corresponding module is available
    :return: multi-line string presenting requested info
    """
    silent = build_option('silent')

    ec_paths = find_matching_easyconfigs('*', '*', build_option('robot_path') or [])
    ecs = []
    cnt = len(ec_paths)
    for idx, ec_path in enumerate(ec_paths):
        # full EasyConfig instance is only required when module name is needed
        # this is significantly slower (5-10x) than a 'shallow' parse via EasyConfigParser
        if only_installed:
            ec = process_easyconfig(ec_path, validate=False, parse_only=True)[0]['ec']
        else:
            ec = EasyConfigParser(filename=ec_path).get_config_dict()

        ecs.append(ec)
        print_msg('\r', prefix=False, newline=False, silent=silent)
        print_msg("Processed %d/%d easyconfigs..." % (idx + 1, cnt), newline=False, silent=silent)
    print_msg('', prefix=False, silent=silent)

    software = {}
    for ec in ecs:
        software.setdefault(ec['name'], [])
        if is_system_toolchain(ec['toolchain']['name']):
            toolchain = SYSTEM_TOOLCHAIN_NAME
        else:
            toolchain = '%s/%s' % (ec['toolchain']['name'], ec['toolchain']['version'])

        keys = ['description', 'homepage', 'version', 'versionsuffix']

        info = {'toolchain': toolchain}
        for key in keys:
            info[key] = ec.get(key, '')

        # make sure values like homepage & versionsuffix get properly templated
        if isinstance(ec, dict):
            template_values = template_constant_dict(ec)
            for key in keys:
                if info[key] and '%(' in info[key]:
                    try:
                        info[key] = info[key] % template_values
                    except (KeyError, TypeError, ValueError) as err:
                        _log.debug("Ignoring failure to resolve templates: %s", err)

        software[ec['name']].append(info)

        if only_installed:
            software[ec['name']][-1].update({'mod_name': ec.full_mod_name})

    print_msg("Found %d different software packages" % len(software), silent=silent)

    if only_installed:
        avail_mod_names = modules_tool().available()

        # rebuild software, only retain entries with a corresponding available module
        software, all_software = {}, software
        for key, entries in all_software.items():
            for entry in entries:
                if entry['mod_name'] in avail_mod_names:
                    software.setdefault(key, []).append(entry)

        print_msg("Retained %d installed software packages" % len(software), silent=silent)

    return generate_doc('list_software_%s' % output_format, [software, detailed])


def list_software_md(software, detailed=True):
    """
    Return overview of supported software in MarkDown format

    :param software: software information (structured like list_software does)
    :param detailed: whether or not to return detailed information (incl. version, versionsuffix, toolchain info)
    :return: multi-line string presenting requested info
    """

    lines = [
        "# List of supported software",
        '',
        "EasyBuild supports %d different software packages (incl. toolchains, bundles):" % len(software),
        '',
    ]

    # links to per-letter tables
    key_letters = nub(sorted(k[0].lower() for k in software.keys()))
    letter_links = ' - '.join(['[' + x + '](#' + x + ')' for x in ascii_lowercase if x in key_letters])
    lines.extend([letter_links, ''])

    letter = None
    sorted_keys = sorted(software.keys(), key=lambda x: x.lower())
    for key in sorted_keys:

        # start a new subsection for each letter
        if key[0].lower() != letter:

            # subsection for new letter
            letter = key[0].lower()
            lines.extend([
                '',
                "## %s" % letter.upper(),
                '',
            ])

            if detailed:
                # quick links per software package
                lines.extend([
                    '',
                    ' - '.join('[%s](#%s)' % (k, k.lower()) for k in sorted_keys if k[0].lower() == letter),
                    '',
                ])

        # append software to list, including version(suffix) & toolchain info if detailed info is requested
        if detailed:
            table_titles = ['version', 'toolchain']
            table_values = [[], []]

            # first determine unique pairs of version/versionsuffix
            # we can't use LooseVersion yet here, since nub uses set and LooseVersion instances are not hashable
            pairs = nub((x['version'], x['versionsuffix']) for x in software[key])

            # check whether any non-empty versionsuffixes are in play
            with_vsuff = any(vs for (_, vs) in pairs)
            if with_vsuff:
                table_titles.insert(1, 'versionsuffix')
                table_values.insert(1, [])

            # sort pairs by version (and then by versionsuffix);
            # we sort by LooseVersion to obtain chronological version ordering,
            # but we also need to retain original string version for filtering-by-version done below
            sorted_pairs = sorted((LooseVersion(v), vs, v) for v, vs in pairs)

            for _, vsuff, ver in sorted_pairs:
                table_values[0].append('``%s``' % ver)
                if with_vsuff:
                    if vsuff:
                        table_values[1].append('``%s``' % vsuff)
                    else:
                        table_values[1].append('')
                tcs = [x['toolchain'] for x in software[key] if x['version'] == ver and x['versionsuffix'] == vsuff]
                table_values[-1].append(', '.join('``%s``' % tc for tc in sorted(nub(tcs))))

            lines.extend([
                '',
                '### %s' % key,
                '',
                ' '.join(software[key][-1]['description'].split('\n')).lstrip(' '),
                '',
                "*homepage*: <%s>" % software[key][-1]['homepage'],
                '',
            ] + md_title_and_table(None, table_titles, table_values))
        else:
            lines.append("* %s" % key)

    return '\n'.join(lines)


def list_software_rst(software, detailed=False):
    """
    Return overview of supported software in RST format

    :param software: software information (structured like list_software does)
    :param detailed: whether or not to return detailed information (incl. version, versionsuffix, toolchain info)
    :return: multi-line string presenting requested info
    """

    title = "List of supported software"
    lines = [
        title,
        '=' * len(title),
        '',
        "EasyBuild |version| supports %d different software packages (incl. toolchains, bundles):" % len(software),
        '',
    ]

    # links to per-letter tables
    letter_refs = ''
    key_letters = nub(sorted(k[0].lower() for k in software.keys()))
    for letter in ascii_lowercase:
        if letter in key_letters:
            if letter_refs:
                letter_refs += " - :ref:`list_software_letter_%s`" % letter
            else:
                letter_refs = ":ref:`list_software_letter_%s`" % letter
    lines.extend([letter_refs, ''])

    def key_to_ref(name):
        """Create a reference label for the specified software name."""
        return 'list_software_%s_%d' % (name, sum(ord(letter) for letter in name))

    letter = None
    sorted_keys = sorted(software.keys(), key=lambda x: x.lower())
    for key in sorted_keys:

        # start a new subsection for each letter
        if key[0].lower() != letter:

            # subsection for new letter
            letter = key[0].lower()
            lines.extend([
                '',
                '.. _list_software_letter_%s:' % letter,
                '',
                "*%s*" % letter.upper(),
                '-' * 3,
                '',
            ])

            if detailed:
                # quick links per software package
                lines.extend([
                    '',
                    ' - '.join(':ref:`%s`' % key_to_ref(k) for k in sorted_keys if k[0].lower() == letter),
                    '',
                ])

        # append software to list, including version(suffix) & toolchain info if detailed info is requested
        if detailed:
            table_titles = ['version', 'toolchain']
            table_values = [[], []]

            # first determine unique pairs of version/versionsuffix
            # we can't use LooseVersion yet here, since nub uses set and LooseVersion instances are not hashable
            pairs = nub((x['version'], x['versionsuffix']) for x in software[key])

            # check whether any non-empty versionsuffixes are in play
            with_vsuff = any(vs for (_, vs) in pairs)
            if with_vsuff:
                table_titles.insert(1, 'versionsuffix')
                table_values.insert(1, [])

            # sort pairs by version (and then by versionsuffix);
            # we sort by LooseVersion to obtain chronological version ordering,
            # but we also need to retain original string version for filtering-by-version done below
            sorted_pairs = sorted((LooseVersion(v), vs, v) for v, vs in pairs)

            for _, vsuff, ver in sorted_pairs:
                table_values[0].append('``%s``' % ver)
                if with_vsuff:
                    if vsuff:
                        table_values[1].append('``%s``' % vsuff)
                    else:
                        table_values[1].append('')
                tcs = [x['toolchain'] for x in software[key] if x['version'] == ver and x['versionsuffix'] == vsuff]
                table_values[-1].append(', '.join('``%s``' % tc for tc in sorted(nub(tcs))))

            lines.extend([
                '',
                '.. _%s:' % key_to_ref(key),
                '',
                '*%s*' % key,
                '+' * (len(key) + 2),
                '',
                ' '.join(software[key][-1]['description'].split('\n')).lstrip(' '),
                '',
                "*homepage*: %s" % software[key][-1]['homepage'],
                '',
            ] + rst_title_and_table(None, table_titles, table_values))
        else:
            lines.append("* %s" % key)

    return '\n'.join(lines)


def list_software_txt(software, detailed=False):
    """
    Return overview of supported software in plain text

    :param software: software information (structured like list_software does)
    :param detailed: whether or not to return detailed information (incl. version, versionsuffix, toolchain info)
    :return: multi-line string presenting requested info
    """

    lines = ['']
    for key in sorted(software, key=lambda x: x.lower()):
        lines.append('* %s' % key)
        if detailed:
            lines.extend([
                '',
                ' '.join(software[key][-1]['description'].split('\n')),
                '',
                "homepage: %s" % software[key][-1]['homepage'],
                '',
            ])

            # first determine unique pairs of version/versionsuffix
            # we can't use LooseVersion yet here, since nub uses set and LooseVersion instances are not hashable
            pairs = nub((x['version'], x['versionsuffix']) for x in software[key])

            # sort pairs by version (and then by versionsuffix);
            # we sort by LooseVersion to obtain chronological version ordering,
            # but we also need to retain original string version for filtering-by-version done below
            sorted_pairs = sorted((LooseVersion(v), vs, v) for v, vs in pairs)

            for _, vsuff, ver in sorted_pairs:
                tcs = [x['toolchain'] for x in software[key] if x['version'] == ver and x['versionsuffix'] == vsuff]

                line = "  * %s v%s" % (key, ver)
                if vsuff:
                    line += " (versionsuffix: '%s')" % vsuff
                line += ": %s" % ', '.join(sorted(nub(tcs)))
                lines.append(line)
            lines.append('')

    return '\n'.join(lines)


def list_software_json(software, detailed=False):
    """
    Return overview of supported software in json

    :param software: software information (strucuted like list_software does)
    :param detailed: whether or not to return detailed information (incl. version, versionsuffix, toolchain info)
    :return: multi-line string presenting requested info
    """
    lines = ['[']
    for key in sorted(software, key=lambda x: x.lower()):
        for entry in software[key]:
            if detailed:
                # deep copy here to avoid modifying the original dict
                entry = copy.deepcopy(entry)
                entry['description'] = ' '.join(entry['description'].split('\n')).strip()
            else:
                entry = {}
            entry['name'] = key

            lines.append(json.dumps(entry, indent=4, sort_keys=True, separators=(',', ': ')) + ",")
            if not detailed:
                break

    # remove trailing comma on last line
    if len(lines) > 1:
        lines[-1] = lines[-1].rstrip(',')

    lines.append(']')

    return '\n'.join(lines)


def list_toolchains(output_format=FORMAT_TXT):
    """Show list of known toolchains."""
    _, all_tcs = search_toolchain('')

    # start with dict that maps toolchain name to corresponding subclass of Toolchain
    # filter deprecated 'dummy' toolchain
    tcs = {tc.NAME: tc for tc in all_tcs}

    for tcname in sorted(tcs):
        tcc = tcs[tcname]
        tc = tcc(version='1.2.3')  # version doesn't matter here, but something needs to be there
        tcs[tcname] = tc.definition()

    return generate_doc('list_toolchains_%s' % output_format, [tcs])


def list_toolchains_md(tcs):
    """Returns overview of all toolchains in MarkDown format"""
    title = "List of known toolchains"

    # Specify the column names for the table
    table_titles = ['NAME', 'COMPILER', 'MPI', 'LINALG', 'FFT']

    # Set up column name : display name pairs
    col_names = {
        'NAME': 'Name',
        'COMPILER': 'Compiler(s)',
        'LINALG': "Linear algebra",
    }

    # Create sorted list of toolchain names
    sorted_tc_names = sorted(tcs.keys(), key=str.lower)

    # Create text placeholder to use for missing entries
    none_txt = '*(none)*'

    # Initialize an empty list of lists for the table data
    table_values = [[] for _ in range(len(table_titles))]

    for col_id, col_name in enumerate(table_titles):
        if col_name == 'NAME':
            # toolchain names column gets bold face entry
            table_values[col_id] = ['**%s**' % tcname for tcname in sorted_tc_names]
        else:
            for tc_name in sorted_tc_names:
                tc = tcs[tc_name]
                if 'cray' in tc_name.lower():
                    if col_name == 'COMPILER':
                        entry = ', '.join(tc[col_name.upper()])
                    elif col_name == 'MPI':
                        entry = 'cray-mpich'
                    elif col_name == 'LINALG':
                        entry = 'cray-libsci'
                    else:
                        entry = none_txt
                # Combine the linear algebra libraries into a single column
                elif col_name == 'LINALG':
                    linalg = []
                    for col in ['BLAS', 'LAPACK', 'SCALAPACK']:
                        linalg.extend(tc.get(col, []))
                    entry = ', '.join(nub(linalg)) or none_txt
                else:
                    # for other columns, we can grab the values via 'tc'
                    # key = col_name
                    entry = ', '.join(tc.get(col_name, [])) or none_txt
                table_values[col_id].append(entry)

    # Set the table titles to the pretty ones
    table_titles = [col_names.get(col, col) for col in table_titles]

    # Pass the data to the rst formatter, wich is returned as a list, each element
    # is an rst formatted text row.
    doc = md_title_and_table(title, table_titles, table_values)

    # Make a string with line endings suitable to write to document file
    return '\n'.join(doc)


def list_toolchains_rst(tcs):
    """ Returns overview of all toolchains in rst format """
    title = "List of known toolchains"

    # Specify the column names for the table
    table_titles = ['NAME', 'COMPILER', 'MPI', 'LINALG', 'FFT']

    # Set up column name : display name pairs
    col_names = {
        'NAME': 'Name',
        'COMPILER': 'Compiler(s)',
        'LINALG': "Linear algebra",
    }

    # Create sorted list of toolchain names
    sorted_tc_names = sorted(tcs.keys(), key=str.lower)

    # Create text placeholder to use for missing entries
    none_txt = '*(none)*'

    # Initialize an empty list of lists for the table data
    table_values = [[] for _ in range(len(table_titles))]

    for col_id, col_name in enumerate(table_titles):
        if col_name == 'NAME':
            # toolchain names column gets bold face entry
            table_values[col_id] = ['**%s**' % tcname for tcname in sorted_tc_names]
        else:
            for tc_name in sorted_tc_names:
                tc = tcs[tc_name]
                if 'cray' in tc_name.lower():
                    if col_name == 'COMPILER':
                        entry = ', '.join(tc[col_name.upper()])
                    elif col_name == 'MPI':
                        entry = 'cray-mpich'
                    elif col_name == 'LINALG':
                        entry = 'cray-libsci'
                    else:
                        entry = none_txt
                # Combine the linear algebra libraries into a single column
                elif col_name == 'LINALG':
                    linalg = []
                    for col in ['BLAS', 'LAPACK', 'SCALAPACK']:
                        linalg.extend(tc.get(col, []))
                    entry = ', '.join(nub(linalg)) or none_txt
                else:
                    # for other columns, we can grab the values via 'tc'
                    # key = col_name
                    entry = ', '.join(tc.get(col_name, [])) or none_txt
                table_values[col_id].append(entry)

    # Set the table titles to the pretty ones
    table_titles = [col_names.get(col, col) for col in table_titles]

    # Pass the data to the rst formatter, wich is returned as a list, each element
    # is an rst formatted text row.
    doc = rst_title_and_table(title, table_titles, table_values)

    # Make a string with line endings suitable to write to document file
    return '\n'.join(doc)


def list_toolchains_txt(tcs):
    """ Returns overview of all toolchains in txt format """
    doc = ["List of known toolchains (toolchain name: module[, module, ...]):"]
    for name in sorted(tcs):
        tc_elems = nub(sorted([e for es in tcs[name].values() for e in es]))
        doc.append("\t%s: %s" % (name, ', '.join(tc_elems)))

    return '\n'.join(doc)


def list_toolchains_json(tcs):
    """ Returns overview of all toolchains in json format """
    raise NotImplementedError("JSON output not implemented yet for --list-toolchains")


def avail_toolchain_opts(name, output_format=FORMAT_TXT):
    """Show list of known options for given toolchain."""
    tc_class, _ = search_toolchain(name)
    if not tc_class:
        raise EasyBuildError("Couldn't find toolchain: '%s'. To see available toolchains, use --list-toolchains" % name)
    tc = tc_class(version='1.0')  # version doesn't matter here, but needs to be defined

    tc_dict = {}
    for cst in ['COMPILER_SHARED_OPTS', 'COMPILER_UNIQUE_OPTS', 'MPI_SHARED_OPTS', 'MPI_UNIQUE_OPTS']:
        opts = getattr(tc, cst, None)
        if opts is not None:
            tc_dict.update(opts)

    return generate_doc('avail_toolchain_opts_%s' % output_format, [name, tc_dict])


def avail_toolchain_opts_md(name, tc_dict):
    """ Returns overview of toolchain options in MarkDown format """
    title = "Available options for %s toolchain" % name

    table_titles = ['option', 'description', 'default']

    tc_items = sorted(tc_dict.items())
    table_values = [
        ['``%s``' % val[0] for val in tc_items],
        [val[1][1] for val in tc_items],
        ['``%s``' % val[1][0] for val in tc_items],
    ]

    doc = md_title_and_table(title, table_titles, table_values, title_level=2)

    return '\n'.join(doc)


def avail_toolchain_opts_rst(name, tc_dict):
    """ Returns overview of toolchain options in rst format """
    title = "Available options for %s toolchain" % name

    table_titles = ['option', 'description', 'default']

    tc_items = sorted(tc_dict.items())
    table_values = [
        ['``%s``' % val[0] for val in tc_items],
        [val[1][1] for val in tc_items],
        ['``%s``' % val[1][0] for val in tc_items],
    ]

    doc = rst_title_and_table(title, table_titles, table_values)

    return '\n'.join(doc)


def avail_toolchain_opts_json(name, tc_dict):
    """ Returns overview of toolchain options in jsonformat """
    raise NotImplementedError("JSON output not implemented yet for --avail-toolchain-opts")


def avail_toolchain_opts_txt(name, tc_dict):
    """ Returns overview of toolchain options in txt format """
    doc = ["Available options for %s toolchain:" % name]
    for opt_name in sorted(tc_dict.keys()):
        doc.append("%s%s: %s (default: %s)" % (INDENT_4SPACES, opt_name, tc_dict[opt_name][1], tc_dict[opt_name][0]))

    return '\n'.join(doc)


def get_easyblock_classes(package_name):
    """
    Get list of all easyblock classes in specified easyblocks.* package
    """
    easyblocks = set()
    modules = import_available_modules(package_name)

    for mod in modules:
        easyblock_found = False
        for name, _ in inspect.getmembers(mod, inspect.isclass):
            eb_class = getattr(mod, name)
            # skip imported classes that are not easyblocks
            if eb_class.__module__.startswith(package_name) and EasyBlock in inspect.getmro(eb_class):
                easyblocks.add(eb_class)
                easyblock_found = True
        if not easyblock_found:
            raise RuntimeError("No easyblocks found in module: %s", mod.__name__)

    return easyblocks


def gen_easyblocks_overview_json(package_name, path_to_examples, common_params=None, doc_functions=None):
    """
    Compose overview of all easyblocks in the given package in json format
    """
    raise NotImplementedError("JSON output not implemented yet for gen_easyblocks_overview")


def gen_easyblocks_overview_md(package_name, path_to_examples, common_params=None, doc_functions=None):
    """
    Compose overview of all easyblocks in the given package in MarkDown format
    """
    if common_params is None:
        common_params = {}
    if doc_functions is None:
        doc_functions = []

    eb_classes = get_easyblock_classes(package_name)

    eb_links = []
    for eb_class in sorted(eb_classes, key=lambda c: c.__name__):
        eb_name = eb_class.__name__
        eb_links.append("[" + eb_name + "](#" + eb_name.lower() + ")")

    heading = [
        "# Overview of generic easyblocks",
        '',
        ' - '.join(eb_links),
        '',
    ]

    doc = []
    for eb_class in sorted(eb_classes, key=lambda c: c.__name__):
        doc.extend(gen_easyblock_doc_section_md(eb_class, path_to_examples, common_params, doc_functions, eb_classes))

    return heading + doc


def gen_easyblocks_overview_rst(package_name, path_to_examples, common_params=None, doc_functions=None):
    """
    Compose overview of all easyblocks in the given package in rst format
    """
    if common_params is None:
        common_params = {}
    if doc_functions is None:
        doc_functions = []

    eb_classes = get_easyblock_classes(package_name)

    doc = []
    for eb_class in sorted(eb_classes, key=lambda c: c.__name__):
        doc.extend(gen_easyblock_doc_section_rst(eb_class, path_to_examples, common_params, doc_functions, eb_classes))

    title = 'Overview of generic easyblocks'

    heading = [
        '*(this page was generated automatically using* ``easybuild.tools.docs.gen_easyblocks_overview_rst()`` *)*',
        '',
        '=' * len(title),
        title,
        '=' * len(title),
        '',
    ]

    contents = [":ref:`" + b.__name__ + "`" for b in sorted(eb_classes, key=lambda b: b.__name__)]
    toc = ' - '.join(contents)
    heading.append(toc)
    heading.append('')

    return heading + doc


def gen_easyblock_doc_section_md(eb_class, path_to_examples, common_params, doc_functions, all_eb_classes):
    """
    Compose overview of one easyblock given class object of the easyblock in MarkDown format
    """
    classname = eb_class.__name__

    doc = [
        '## ``' + classname + '``',
        '',
    ]

    bases = []
    for base in eb_class.__bases__:
        bname = base.__name__
        if base in all_eb_classes:
            bases.append("[``" + bname + "``](#" + bname.lower() + ")")
        else:
            bases.append('``' + bname + '``')

    derived = '(derives from ' + ', '.join(bases) + ')'
    doc.extend([derived, ''])

    # Description (docstring)
    eb_docstring = eb_class.__doc__
    if eb_docstring is not None:
        doc.extend(x.lstrip() for x in eb_docstring.splitlines())
        doc.append('')

    # Add extra options, if any
    if eb_class.extra_options():
        title = "Extra easyconfig parameters specific to ``%s`` easyblock" % classname
        ex_opt = eb_class.extra_options()
        keys = sorted(ex_opt.keys())
        values = [ex_opt[k] for k in keys]

        table_titles = ['easyconfig parameter', 'description', 'default value']
        table_values = [
            ['``' + key + '``' for key in keys],  # parameter name
            [val[1] for val in values],  # description
            ['``' + str(quote_str(val[0])) + '``' for val in values]  # default value
        ]

        doc.extend(md_title_and_table(title, table_titles, table_values, title_level=3))
        doc.append('')

    # Add commonly used parameters
    if classname in common_params:
        title = "Commonly used easyconfig parameters with ``%s`` easyblock" % classname

        table_titles = ['easyconfig parameter', 'description']
        table_values = [
            [opt for opt in common_params[classname]],
            [DEFAULT_CONFIG[opt][1] for opt in common_params[classname]],
        ]

        doc.extend(md_title_and_table(title, table_titles, table_values, title_level=3))
        doc.append('')

    # Add docstring for custom steps
    custom = []
    inh = ''
    f = None
    for func in doc_functions:
        if func in eb_class.__dict__:
            f = eb_class.__dict__[func]

        if f.__doc__:
            custom.append('* ``' + func + '`` - ' + f.__doc__.strip() + inh)
            custom.append('')

    if custom:
        doc.append("### Customised steps in ``" + classname + "`` easyblock")
        doc.append('')
        doc.extend(custom)
        doc.append('')

    # Add example if available
    example_ec = os.path.join(path_to_examples, '%s.eb' % classname)
    if os.path.exists(example_ec):
        doc.extend([
            "### Example easyconfig for ``" + classname + "`` easyblock",
            '',
            '```python',
            read_file(example_ec),
            '```',
            '',
        ])

    return doc


def gen_easyblock_doc_section_rst(eb_class, path_to_examples, common_params, doc_functions, all_blocks):
    """
    Compose overview of one easyblock given class object of the easyblock in rst format
    """
    classname = eb_class.__name__

    doc = [
        '.. _' + classname + ':',
        '',
        '``' + classname + '``',
        '=' * (len(classname) + 4),
        '',
    ]

    bases = []
    for b in eb_class.__bases__:
        base = ':ref:`' + b.__name__ + '`' if b in all_blocks else b.__name__
        bases.append(base)

    derived = '(derives from ' + ', '.join(bases) + ')'
    doc.extend([derived, ''])

    # Description (docstring)
    if eb_class.__doc__ is not None:
        doc.extend([eb_class.__doc__.strip(), ''])

    # Add extra options, if any
    if eb_class.extra_options():
        title = 'Extra easyconfig parameters specific to ``%s`` easyblock' % classname
        ex_opt = eb_class.extra_options()
        keys = sorted(ex_opt.keys())
        values = [ex_opt[k] for k in keys]

        table_titles = ['easyconfig parameter', 'description', 'default value']
        table_values = [
            ['``' + key + '``' for key in keys],  # parameter name
            [val[1] for val in values],  # description
            ['``' + str(quote_str(val[0])) + '``' for val in values]  # default value
        ]

        doc.extend(rst_title_and_table(title, table_titles, table_values))

    # Add commonly used parameters
    if classname in common_params:
        title = 'Commonly used easyconfig parameters with ``%s`` easyblock' % classname

        table_titles = ['easyconfig parameter', 'description']
        table_values = [
            [opt for opt in common_params[classname]],
            [DEFAULT_CONFIG[opt][1] for opt in common_params[classname]],
        ]

        doc.extend(rst_title_and_table(title, table_titles, table_values))
        doc.append('')

    # Add docstring for custom steps
    custom = []
    inh = ''
    f = None
    for func in doc_functions:
        if func in eb_class.__dict__:
            f = eb_class.__dict__[func]

        if f.__doc__:
            custom.append('* ``' + func + '`` - ' + f.__doc__.strip() + inh)

    if custom:
        title = 'Customised steps in ``' + classname + '`` easyblock'
        doc.extend([title, '-' * len(title)] + custom)
        doc.append('')

    # Add example if available
    if os.path.exists(os.path.join(path_to_examples, '%s.eb' % classname)):
        title = 'Example easyconfig for ``' + classname + '`` easyblock'
        doc.extend([title, '-' * len(title), '', '.. code::', ''])
        for line in read_file(os.path.join(path_to_examples, classname + '.eb')).split('\n'):
            doc.append(INDENT_4SPACES + line)
        doc.append('')  # empty line after literal block

    return doc
