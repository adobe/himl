import argparse
import os
from copy import deepcopy

from deepmerge import STRATEGY_END

"""
Example function to demonstrate how to provide a custom merging behavior to himl.
How to use it:
        config_processor = ConfigProcessor()
        config_processor.process(cwd, opts.path, filters, excluded_keys, opts.enclosing_key, opts.remove_enclosing_key,
                                 opts.output_format, opts.print_data, opts.output_file, opts.skip_interpolation_resolving,
                                 opts.skip_interpolation_validation, opts.skip_secrets, opts.multi_line_string,
                                 type_strategies= [(list, [strategy_merge_override,'append']), (dict, ["merge"])] )
"""
def strategy_merge_override(config, path, base, nxt):
    """merge list of dicts. if objects have same id, nxt replaces base."""
    """if remove flag is present in nxt item, remove base and not add nxt"""
    result = deepcopy(base)
    for nxto in nxt:
        for baseo in result:
            # if list is not a list of dicts, bail out and let the next strategy to execute
            if not isinstance(baseo,dict) or not isinstance(nxto,dict):
                return STRATEGY_END
            if 'id' in baseo and 'id' in nxto and baseo['id'] == nxto['id']:
                result.remove(baseo) #same id, remove previous item
        if 'remove' not in nxto:
            result.append(nxto)
    return result
