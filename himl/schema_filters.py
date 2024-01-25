import re


class Schema(object):

    def __init__(self, filter_schema, levels):
        self.filter_schema = filter_schema
        self.levels = levels

    def filter(self, output):

        removable_keys = set(output.keys()) - set(self.levels)

        for filter in self.filter_schema:
            level = filter.get("level")
            if not level:
                raise Exception("Filter schema must contain a level : {}".format(filter))
            if level not in self.levels:
                raise Exception("Filter schema level must be one of the levels : {}".format(self.levels))

            if "value" in filter:
                predicate = lambda v: v == filter["value"]
            elif "regex" in filter:
                level_re = re.compile(filter["regex"])
                predicate = lambda v: level_re.match(v)
            else:
                predicate = lambda v: True
            if not predicate(output[level]):
                continue

            keys = filter.get("keys")
            if "values" in keys:
                removable_keys = removable_keys - set(keys["values"])
            if "regex" in keys:
                key_re = re.compile(keys["regex"])
                removable_keys = {k for k in removable_keys if not key_re.match(k)}

        for key in removable_keys:
            del output[key]
