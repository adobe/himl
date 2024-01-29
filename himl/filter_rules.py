import re


class FilterRules(object):

    def __init__(self, rules, levels):
        self.rules = rules
        self.levels = levels

    def run(self, output):

        removable_keys = set(output.keys()) - set(self.levels)

        for filter in self.rules:
            selector = filter.get("selector", {})
            if type(selector) != dict:
                raise Exception("Filter selector must be a dictionary")

            if not self.match(output, selector):
                continue

            keys = filter.get("keys")
            if "values" in keys:
                removable_keys = removable_keys - set(keys["values"])
            if "regex" in keys:
                key_re = re.compile(keys["regex"])
                removable_keys = {k for k in removable_keys if not key_re.match(k)}

        for key in removable_keys:
            del output[key]

    def match(self, output, selector):
        for key, pattern in selector.items():
            value = "" if key not in output else output[key]
            if not re.match(pattern, value):
                return False
        return True
